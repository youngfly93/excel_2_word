"""
模板渲染器

负责使用docxtpl渲染Docx模板。
"""

from pathlib import Path
from typing import Optional
from docx import Document
from reportgen.models.report_data import ReportData
from reportgen.utils.logger import get_logger
from reportgen.utils.validators import validate_docx_file


class TemplateRenderer:
    """
    模板渲染器
    
    使用docxtpl将报告数据填充到Docx模板。
    """
    
    def __init__(self, log_file: Optional[str] = None, log_level: str = "INFO"):
        """
        初始化模板渲染器
        
        Args:
            log_file: 日志文件路径
            log_level: 日志级别
        """
        self.logger = get_logger(log_file=log_file, level=log_level)
    
    def render(
        self, template_path: str, report_data: ReportData, output_path: str
    ) -> str:
        """
        渲染模板并保存
        
        Args:
            template_path: 模板文件路径
            report_data: 报告数据
            output_path: 输出文件路径
        
        Returns:
            输出文件路径
        
        Raises:
            FileNotFoundError: 模板文件不存在
            ValueError: 渲染失败
        """
        # 验证模板文件
        is_valid, error = validate_docx_file(template_path, must_exist=True)
        if not is_valid:
            self.logger.error("模板文件验证失败", template=template_path, error=error)
            raise FileNotFoundError(error)
        
        # 验证输出路径
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("开始渲染模板", template=template_path, output=output_path)
        
        try:
            try:
                from docxtpl import DocxTemplate
            except ModuleNotFoundError as e:
                raise ModuleNotFoundError(
                    "缺少依赖 'docxtpl'，无法渲染docx模板；请先安装 requirements.txt 中的依赖"
                ) from e

            # 加载模板
            doc = DocxTemplate(template_path)
            
            # 获取模板上下文
            context = report_data.get_template_context()
            
            self.logger.debug(
                "模板上下文",
                fields=len([k for k, v in context.items() if not isinstance(v, list)]),
                tables=len([k for k, v in context.items() if isinstance(v, list)]),
            )
            
            # 渲染
            doc.render(context)
            
            # 保存
            doc.save(output_path)

            # 渲染后清理：移除完全空白的表格行（避免循环控制行残留导致的空行）
            try:
                self._cleanup_empty_table_rows(output_path)
            except Exception as _:
                # 清理失败不影响主流程
                pass
            
            self.logger.info("模板渲染成功", output=output_path)
            
            return output_path
        
        except Exception as e:
            self.logger.error(
                "模板渲染失败", template=template_path, output=output_path, error=str(e)
            )
            raise ValueError(f"模板渲染失败: {e}")
    
    def validate_template(self, template_path: str) -> tuple[bool, Optional[str]]:
        """
        验证模板文件
        
        Args:
            template_path: 模板文件路径
        
        Returns:
            (是否有效, 错误消息)
        """
        # 基本文件验证
        is_valid, error = validate_docx_file(template_path, must_exist=True)
        if not is_valid:
            return False, error
        
        # 尝试加载模板
        try:
            try:
                from docxtpl import DocxTemplate
            except ModuleNotFoundError as e:
                return False, (
                    "缺少依赖 'docxtpl'，无法校验模板；请先安装 requirements.txt 中的依赖"
                )

            DocxTemplate(template_path)
            self.logger.debug("模板验证成功", template=template_path)
            return True, None
        except Exception as e:
            error_msg = f"模板文件无效: {e}"
            self.logger.error("模板验证失败", template=template_path, error=str(e))
            return False, error_msg
    
    def get_template_variables(self, template_path: str) -> list[str]:
        """
        获取模板中的变量列表

        Args:
            template_path: 模板文件路径

        Returns:
            变量名列表（包括单值变量和循环变量）
        """
        import re
        from zipfile import ZipFile

        try:
            variables = set()

            # 读取docx文件（本质是zip包）
            with ZipFile(template_path, 'r') as zf:
                # 读取document.xml（主要内容）
                xml_files = ['word/document.xml', 'word/header1.xml', 'word/header2.xml',
                             'word/footer1.xml', 'word/footer2.xml']

                for xml_file in xml_files:
                    try:
                        content = zf.read(xml_file).decode('utf-8')

                        # 提取 {{ variable }} 格式的变量
                        # 匹配单值变量: {{ var }} 或 {{ obj.attr }}
                        single_vars = re.findall(r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)\s*\}\}', content)
                        variables.update(single_vars)

                        # 提取 {% for item in list %} 中的list变量
                        for_vars = re.findall(r'\{%\s*for\s+\w+\s+in\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*%\}', content)
                        variables.update(for_vars)

                        # 提取 row.xxx 格式（循环内的字段引用）
                        row_vars = re.findall(r'row\.([a-zA-Z_][a-zA-Z0-9_]*)', content)
                        variables.update([f"row.{v}" for v in row_vars])

                        # 提取 row['xxx'] 格式
                        row_bracket_vars = re.findall(r"row\['([^']+)'\]", content)
                        variables.update([f"row['{v}']" for v in row_bracket_vars])

                    except KeyError:
                        # 文件不存在，跳过
                        continue

            result = sorted(list(variables))
            self.logger.debug("提取模板变量成功", template=template_path, count=len(result))
            return result

        except Exception as e:
            self.logger.error("提取模板变量失败", template=template_path, error=str(e))
            return []

    def validate_template_variables(
        self,
        template_path: str,
        available_variables: list[str],
        *,
        available_row_keys: Optional[set[str]] = None,
    ) -> tuple[bool, list[str], list[str]]:
        """
        校验模板变量是否都有对应的数据源

        Args:
            template_path: 模板文件路径
            available_variables: 可用的变量名列表（来自mapping配置）

        Returns:
            (是否全部匹配, 缺失变量列表, 未使用变量列表)
        """
        template_vars = self.get_template_variables(template_path)

        # 分离单值变量和循环变量
        single_vars = [v for v in template_vars if not v.startswith('row.') and not v.startswith("row[")]

        # 检查缺失的变量（模板中有，但mapping中没有）
        missing_vars = [v for v in single_vars if v not in available_variables]

        # 校验循环行字段（row.* / row['*']）是否在mapping的列定义/同义词中出现
        if available_row_keys is not None:
            row_vars = [v for v in template_vars if v.startswith("row.") or v.startswith("row[")]
            for v in row_vars:
                if v.startswith("row."):
                    key = v[len("row.") :]
                    if key and key not in available_row_keys:
                        missing_vars.append(v)
                elif v.startswith("row['") and v.endswith("']"):
                    key = v[len("row['") : -len("']")]
                    if key and key not in available_row_keys:
                        missing_vars.append(v)

        # 检查未使用的变量（mapping中有，但模板中没有）
        unused_vars = [v for v in available_variables if v not in single_vars]

        is_valid = len(missing_vars) == 0

        if missing_vars:
            self.logger.warning(
                "模板变量校验：发现未定义的变量",
                missing_count=len(missing_vars),
                missing_vars=missing_vars[:10],  # 只显示前10个
            )

        return is_valid, missing_vars, unused_vars

    # -------------------- internal helpers --------------------
    def _cleanup_empty_table_rows(self, file_path: str) -> None:
        """打开生成的docx，删除所有完全空白的表格行。

        空白行定义：该行所有单元格的 .text 去除空白后均为空字符串。
        """
        doc = Document(file_path)
        removed = 0
        for tbl in doc.tables:
            # 收集需要删除的 row 索引（从下往上删更安全）
            to_delete = []
            for idx, row in enumerate(tbl.rows):
                if all((cell.text or "").strip() == "" for cell in row.cells):
                    to_delete.append(idx)
            for idx in reversed(to_delete):
                tr = tbl.rows[idx]._tr
                tbl._tbl.remove(tr)
                removed += 1
        if removed:
            self.logger.debug("移除空白表格行", removed_rows=removed)
            doc.save(file_path)
