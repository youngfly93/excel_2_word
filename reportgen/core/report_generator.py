"""
报告生成器

核心业务逻辑编排，协调所有组件生成报告。
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from reportgen.config.loader import ConfigLoader
from reportgen.core.excel_reader import ExcelReader
from reportgen.core.field_mapper import FieldMapper
from reportgen.core.data_cleaner import DataCleaner
from reportgen.core.template_renderer import TemplateRenderer
from reportgen.models.excel_data import ExcelDataSource
from reportgen.models.report_data import ReportData
from reportgen.utils.logger import get_logger
from reportgen.utils.file_utils import (
    ensure_directory_exists,
    get_unique_filename,
    safe_filename,
)
from reportgen.core.template_bridge_358 import enhance_report_data
from reportgen.knowledge import GeneKnowledgeProvider, CancerTypeGeneProvider


class ReportGenerator:
    """
    报告生成器
    
    协调Excel读取、字段映射、数据清洗和模板渲染，生成最终报告。
    """
    
    def __init__(
        self,
        config_dir: str = "config",
        template_dir: str = "templates",
        log_file: Optional[str] = None,
        log_level: str = "INFO",
    ):
        """
        初始化报告生成器
        
        Args:
            config_dir: 配置目录
            template_dir: 模板目录
            log_file: 日志文件路径
        """
        self.config_dir = config_dir
        self.template_dir = template_dir
        self.log_level = log_level
        self.logger = get_logger(log_file=log_file, level=log_level)
        self.config_loader = ConfigLoader(
            config_dir=config_dir, log_file=log_file, log_level=log_level
        )
        
        # 初始化各个组件
        self.excel_reader = ExcelReader(
            config_dir=config_dir, log_file=log_file, log_level=log_level
        )
        self.field_mapper = FieldMapper(
            config_dir=config_dir, log_file=log_file, log_level=log_level
        )
        self.data_cleaner = DataCleaner(log_file=log_file, log_level=log_level)
        self.template_renderer = TemplateRenderer(log_file=log_file, log_level=log_level)

        # 可选：基因知识库（用于参考文献/基因解析等终版模块）
        # 仅在settings.yaml中启用时生效，且按实例复用缓存，避免重复加载。
        self.gene_knowledge_provider: Optional[GeneKnowledgeProvider] = None
        self.cancer_type_gene_provider: Optional[CancerTypeGeneProvider] = None
        try:
            settings = self.config_loader.load_settings_config()
            knowledge_bases = (
                settings.get("knowledge_bases", {}) if isinstance(settings, dict) else {}
            )
            gene_kb_cfg = (
                knowledge_bases.get("gene_knowledge_db", {})
                if isinstance(knowledge_bases, dict)
                else {}
            )
            if isinstance(gene_kb_cfg, dict) and bool(gene_kb_cfg.get("enabled", False)):
                cfg = {"enabled": True, **knowledge_bases}
                self.gene_knowledge_provider = GeneKnowledgeProvider(config=cfg)

            # 癌种重要基因列表Provider (批注#33)
            cancer_genes_cfg = (
                knowledge_bases.get("cancer_type_genes", {})
                if isinstance(knowledge_bases, dict)
                else {}
            )
            if isinstance(cancer_genes_cfg, dict) and bool(cancer_genes_cfg.get("enabled", False)):
                self.cancer_type_gene_provider = CancerTypeGeneProvider(config=cancer_genes_cfg)
        except Exception:
            self.gene_knowledge_provider = None
            self.cancer_type_gene_provider = None
    
    # 关键字段定义（严格模式下必须存在）
    CRITICAL_FIELDS = ["patient_name", "sample_id"]

    # 重要字段定义（严格模式下缺失会警告，但不阻断）
    IMPORTANT_FIELDS = ["age", "gender", "cancer_type", "hospital"]

    def generate(
        self,
        excel_file: str,
        template_file: str,
        output_dir: str,
        output_filename: Optional[str] = None,
        strict_mode: bool = False,
        excel_data: Optional[ExcelDataSource] = None,
    ) -> dict:
        """
        生成单个报告

        Args:
            excel_file: Excel文件路径
            template_file: 模板文件路径
            output_dir: 输出目录
            output_filename: 输出文件名（可选，默认自动生成）
            strict_mode: 严格模式（缺失关键字段时阻断生成）

        Returns:
            生成结果字典，包含:
                - success: 是否成功
                - output_file: 输出文件路径
                - duration: 耗时（秒）
                - errors: 错误列表
        """
        start_time = time.time()
        
        self.logger.info(
            "开始生成报告",
            excel_file=excel_file,
            template=template_file,
            output_dir=output_dir,
        )
        
        try:
            # 1. 读取Excel（支持复用外部已读取的数据，避免重复IO）
            if excel_data is None:
                self.logger.log_event("excel_reading_started", file=excel_file)
                excel_data = self.excel_reader.read(excel_file)
                self.logger.log_event(
                    "excel_reading_completed",
                    file=excel_file,
                    single_values=len(excel_data.single_values),
                    tables=len(excel_data.table_data),
                )
            else:
                if excel_file and str(excel_file) != str(excel_data.file_path):
                    self.logger.warning(
                        "传入的excel_data与excel_file路径不一致，优先使用excel_data.file_path",
                        excel_file=excel_file,
                        excel_data_path=excel_data.file_path,
                    )
                self.logger.log_event(
                    "excel_reading_skipped",
                    file=excel_data.file_path,
                    single_values=len(excel_data.single_values),
                    tables=len(excel_data.table_data),
                )
            
            # 2. 字段映射
            self.logger.log_event("field_mapping_started")
            report_data = self.field_mapper.map(excel_data)
            self.logger.log_event(
                "field_mapping_completed", validation_errors=len(report_data.validation_errors)
            )
            
            # 3. 数据清洗
            self.logger.log_event("data_cleaning_started")
            report_data = self.data_cleaner.validate_and_clean(report_data)
            self.logger.log_event(
                "data_cleaning_completed", validation_errors=len(report_data.validation_errors)
            )

            # 3.5 358基因模板增强：添加模板特定的表格和字段
            self.logger.log_event("template_enhancement_started")
            report_data = enhance_report_data(
                report_data,
                excel_data,
                field_mapper=self.field_mapper,
                gene_knowledge_provider=self.gene_knowledge_provider,
                cancer_type_gene_provider=self.cancer_type_gene_provider,
                base_path=str(Path(self.config_dir).parent),
            )
            self.logger.log_event(
                "template_enhancement_completed",
                variants=len(report_data.get_table("variants") or []),
                summary_variants=len(report_data.get_table("summary_variants") or []),
                undetected_genes=len(report_data.get_table("undetected_genes") or []),
            )

            # 检查验证错误
            if not report_data.is_valid():
                self.logger.warning(
                    "报告数据验证失败", errors=report_data.validation_errors
                )
                # 继续生成，但记录警告

            # 4. 严格模式：检查关键字段
            if strict_mode:
                missing_critical = self._check_critical_fields(report_data)
                if missing_critical:
                    duration = time.time() - start_time
                    error_msg = f"严格模式：缺失关键字段 {missing_critical}，阻断生成"
                    self.logger.error(error_msg)
                    return {
                        "success": False,
                        "output_file": None,
                        "duration": duration,
                        "errors": [error_msg],
                        "warnings": report_data.validation_errors,
                    }

                # 检查重要字段（警告但不阻断）
                missing_important = self._check_important_fields(report_data)
                if missing_important:
                    self.logger.warning(
                        "严格模式：缺失重要字段（不阻断）",
                        missing_fields=missing_important
                    )

            # 5. 生成输出文件名
            if not output_filename:
                output_filename = self._generate_output_filename(excel_data, report_data)
            
            # 确保文件名安全
            max_len = self.config_loader.get_setting("naming.max_filename_length", 200)
            illegal_replace = self.config_loader.get_setting("naming.illegal_chars_replace", "_")
            output_filename = safe_filename(
                output_filename, max_length=int(max_len), replacement=str(illegal_replace)
            )
            
            # 确保输出目录存在
            ensure_directory_exists(output_dir)
            
            # 是否允许覆盖已存在文件（默认：不覆盖，自动生成唯一文件名）
            overwrite_existing = bool(
                self.config_loader.get_setting("generation.output.overwrite_existing", False)
            )
            if not overwrite_existing:
                output_filename = get_unique_filename(output_dir, output_filename)

            output_path = str(Path(output_dir) / output_filename)
            
            # 5. 渲染模板
            self.logger.log_event("template_rendering_started", output=output_path)
            final_output = self.template_renderer.render(template_file, report_data, output_path)
            self.logger.log_event("template_rendering_completed", output=final_output)
            
            # 计算耗时
            duration = time.time() - start_time
            
            self.logger.info(
                "报告生成成功", output=final_output, duration_seconds=f"{duration:.2f}"
            )
            
            return {
                "success": True,
                "output_file": final_output,
                "duration": duration,
                "errors": [],
                "warnings": report_data.validation_errors,
            }
        
        except Exception as e:
            duration = time.time() - start_time
            
            self.logger.error(
                "报告生成失败",
                excel_file=excel_file,
                error=str(e),
                duration_seconds=f"{duration:.2f}",
            )
            
            return {
                "success": False,
                "output_file": None,
                "duration": duration,
                "errors": [str(e)],
                "warnings": [],
            }
    
    def _generate_output_filename(
        self, excel_data, report_data: ReportData
    ) -> str:
        """
        生成输出文件名
        
        Args:
            excel_data: Excel数据源
            report_data: 报告数据
        
        Returns:
            输出文件名
        """
        pattern = self.config_loader.get_setting("naming.output_pattern", None)
        timestamp_format = self.config_loader.get_setting(
            "naming.timestamp_format", "%Y%m%d_%H%M%S"
        )
        date_format = self.config_loader.get_setting("naming.date_format", "%Y-%m-%d")

        now = datetime.now()
        filename_context = {
            "patient_name": report_data.get_field("patient_name") or "",
            "sample_id": report_data.get_field("sample_id")
            or excel_data.metadata.get("sample_id_from_filename")
            or "",
            "project_name": report_data.get_field("project_name") or "",
            "report_date": report_data.get_field("report_date") or now.strftime(date_format),
            "timestamp": now.strftime(timestamp_format),
        }

        filename = None
        if pattern:
            try:
                filename = str(pattern).format(**filename_context)
            except KeyError as e:
                self.logger.warning(
                    "文件名模板包含未知变量，回退默认命名",
                    pattern=pattern,
                    missing_key=str(e),
                )

        # 回退默认命名规则：患者名-样本号-报告.docx
        if not filename:
            parts = []
            if filename_context["patient_name"]:
                parts.append(str(filename_context["patient_name"]))
            if filename_context["sample_id"]:
                parts.append(str(filename_context["sample_id"]))
            if not parts:
                parts.append(Path(excel_data.file_path).stem)
            parts.append("报告")
            filename = "-".join(parts)

        if not filename.lower().endswith(".docx"):
            filename += ".docx"

        self.logger.debug("生成输出文件名", filename=filename)
        return filename
    
    def validate_inputs(
        self, excel_file: str, template_file: str, output_dir: str
    ) -> tuple[bool, list[str]]:
        """
        验证输入参数
        
        Args:
            excel_file: Excel文件路径
            template_file: 模板文件路径
            output_dir: 输出目录
        
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        
        # 验证Excel文件
        from reportgen.utils.validators import validate_excel_file
        
        is_valid, error = validate_excel_file(excel_file)
        if not is_valid:
            errors.append(f"Excel文件无效: {error}")
        
        # 验证模板文件
        is_valid, error = self.template_renderer.validate_template(template_file)
        if not is_valid:
            errors.append(f"模板文件无效: {error}")
        
        # 验证输出目录（可以不存在，会自动创建）
        from reportgen.utils.validators import validate_directory_writable
        
        if Path(output_dir).exists():
            is_valid, error = validate_directory_writable(output_dir)
            if not is_valid:
                errors.append(f"输出目录无效: {error}")
        
        return len(errors) == 0, errors

    def _check_critical_fields(self, report_data: ReportData) -> list[str]:
        """
        检查关键字段是否存在

        Args:
            report_data: 报告数据

        Returns:
            缺失的关键字段列表
        """
        missing = []
        for field in self.CRITICAL_FIELDS:
            value = report_data.get_field(field)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                missing.append(field)
        return missing

    def _check_important_fields(self, report_data: ReportData) -> list[str]:
        """
        检查重要字段是否存在

        Args:
            report_data: 报告数据

        Returns:
            缺失的重要字段列表
        """
        missing = []
        for field in self.IMPORTANT_FIELDS:
            value = report_data.get_field(field)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                missing.append(field)
        return missing

    def get_statistics(self) -> dict:
        """
        获取生成器统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "config_dir": self.config_dir,
            "template_dir": self.template_dir,
            "single_value_mappings": len(self.field_mapper.single_value_mappings),
            "table_mappings": len(self.field_mapper.table_mappings),
        }
