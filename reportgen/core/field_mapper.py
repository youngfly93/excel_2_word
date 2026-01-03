"""
字段映射器

负责将Excel字段映射到模板变量。
"""

from pathlib import Path
import re
from datetime import datetime
from typing import Any, Dict, Optional
import pandas as pd
from reportgen.models.excel_data import ExcelDataSource
from reportgen.models.mapping import FieldMapping, TableMapping
from reportgen.models.report_data import ReportData
from reportgen.config.loader import ConfigLoader
from reportgen.utils.logger import get_logger
from reportgen.utils.hgvs_utils import format_variant_site, infer_variant_type_cn


class FieldMapper:
    """
    字段映射器

    根据映射配置将Excel数据映射到模板变量。
    """

    def __init__(
        self,
        config_dir: str = "config",
        log_file: Optional[str] = None,
        log_level: str = "INFO",
    ):
        """
        初始化字段映射器

        Args:
            config_dir: 配置目录
            log_file: 日志文件路径
            log_level: 日志级别
        """
        self.config_loader = ConfigLoader(
            config_dir=config_dir, log_file=log_file, log_level=log_level
        )
        self.logger = get_logger(log_file=log_file, level=log_level)

        # 加载映射配置
        self.mapping_config = self.config_loader.load_mapping_config()

        # 🔥 NEW: 加载过滤配置
        self.filtering_config = self.config_loader.load_filtering_config()

        # 构建映射对象
        self.single_value_mappings = self._build_single_value_mappings()
        self.table_mappings = self._build_table_mappings()

        # 靶向药物提示数据库（可选）缓存：避免每次map都重复打开xlsx
        self._targeted_drug_db_loaded = False
        self._targeted_drug_db: Optional[pd.DataFrame] = None
        self._targeted_drug_db_cols: dict[str, str] = {}

        # 免疫相关基因列表（可选）缓存
        self._immune_gene_list_loaded = False
        self._immune_gene_sets: dict[str, set[str]] = {}

    def _build_single_value_mappings(self) -> Dict[str, FieldMapping]:
        """
        构建单值字段映射

        Returns:
            映射字典，key为变量名
        """
        mappings = {}
        single_values_config = self.mapping_config.get("single_values", {})

        for var_name, var_config in single_values_config.items():
            mapping = FieldMapping(
                variable_name=var_name,
                synonyms=var_config.get("synonyms", []),
                data_type=var_config.get("type", "string"),
                required=var_config.get("required", False),
                default_value=var_config.get("default_value"),
                format_template=var_config.get("format_template"),
                description=var_config.get("description", ""),
            )
            mappings[var_name] = mapping

        self.logger.debug("构建单值映射", count=len(mappings))
        return mappings

    def _build_table_mappings(self) -> Dict[str, TableMapping]:
        """
        构建表格映射

        Returns:
            映射字典，key为表格名
        """
        mappings = {}
        table_data_config = self.mapping_config.get("table_data", {})

        for table_name, table_config in table_data_config.items():
            # 构建列映射
            column_mappings = {}
            columns_config = table_config.get("columns", {})

            for col_var_name, col_config in columns_config.items():
                col_mapping = FieldMapping(
                    variable_name=col_var_name,
                    synonyms=col_config.get("synonyms", []),
                    data_type=col_config.get("type", "string"),
                    required=col_config.get("required", False),
                    default_value=col_config.get("default_value"),
                    format_template=col_config.get("format_template"),
                    description=col_config.get("description", ""),
                )
                column_mappings[col_var_name] = col_mapping

            # 构建表格映射
            table_mapping = TableMapping(
                table_name=table_name,
                sheet_name=table_config.get("sheet_name", ""),
                column_mappings=column_mappings,
                required=table_config.get("required", False),
                empty_behavior=table_config.get("empty_behavior", "show_placeholder"),
                filter=table_config.get("filter"),  # 🔥 NEW: 添加过滤配置支持
            )
            mappings[table_name] = table_mapping

        self.logger.debug("构建表格映射", count=len(mappings))
        return mappings

    def map(self, excel_data: ExcelDataSource) -> ReportData:
        """
        映射Excel数据到报告数据

        Args:
            excel_data: Excel数据源

        Returns:
            ReportData对象
        """
        self.logger.info("开始字段映射", source_file=excel_data.file_path)

        report_data = ReportData(
            metadata={"source_file": excel_data.file_path, **excel_data.metadata}
        )

        # ✅ 先尝试从metadata中获取样本编号
        sample_id_from_filename = excel_data.metadata.get("sample_id_from_filename")
        if sample_id_from_filename:
            report_data.set_field("sample_id", sample_id_from_filename)
            self.logger.info("从文件名提取样本编号", sample_id=sample_id_from_filename)

        # ✅ Week 3: 从配置文件加载患者信息
        patient_info = self.config_loader.load_patient_info(sample_id_from_filename)
        if patient_info:
            for key, value in patient_info.items():
                # 只在字段为空时才设置，避免覆盖已有数据
                if report_data.get_field(key) is None:
                    report_data.set_field(key, value)
                    self.logger.debug("从配置文件加载患者信息", field=key, value=value)

        # 映射单值字段
        self._map_single_values(excel_data, report_data)

        # 映射表格数据
        self._map_tables(excel_data, report_data)

        # 兼容性别名：为历史模板提供 TMB / MSI状态 字段
        try:
            tmb_val = report_data.get_field("tmb_value")
            tmb_unit = report_data.get_field("tmb_unit") or ""
            if tmb_val is not None and report_data.get_field("TMB") is None:
                # 合成如 "7.56 Muts/Mb" 的显示文本（若无单位则仅数值）
                tmb_text = f"{tmb_val} {tmb_unit}".strip()
                report_data.set_field("TMB", tmb_text)

            msi = report_data.get_field("msi_status")
            if msi is not None and report_data.get_field("MSI状态") is None:
                report_data.set_field("MSI状态", msi)

            # 终版：补齐MSI中文描述（供部分模板直接渲染）
            msi_cn = self._build_msi_status_cn(msi) or ""
            cur_msi_cn = (report_data.get_field("msi_status_cn") or "").strip()
            # 仅在缺失/默认值不匹配时覆盖，避免误覆盖外部显式输入
            if (not cur_msi_cn) or (
                cur_msi_cn == "微卫星稳定型，MSS"
                and str(msi or "").strip().upper() not in {"", "MSS"}
            ):
                if msi_cn:
                    report_data.set_field("msi_status_cn", msi_cn)

            # 终版：补齐TMB参考值/分级（批注：组织10；血液16）
            sample_type = str(report_data.get_field("sample_type") or "组织")
            threshold = 16 if ("血" in sample_type or "blood" in sample_type.lower()) else 10

            # tmb_reference：默认值为10，如检测到血液样本则修正为16
            try:
                cur_ref = report_data.get_field("tmb_reference")
                cur_ref_val = float(cur_ref) if cur_ref is not None else None
            except Exception:
                cur_ref_val = None
            if cur_ref_val is None or (cur_ref_val == 10 and threshold == 16):
                report_data.set_field("tmb_reference", threshold)

            # tmb_status / tmb_level_cn：优先依据数值计算，避免仅靠默认值
            if tmb_val is not None:
                try:
                    tmb = float(tmb_val)
                    tmb_status = "H" if tmb >= threshold else "L"
                    report_data.set_field("tmb_status", tmb_status)
                    report_data.set_field("tmb_level_cn", "高" if tmb_status == "H" else "低")
                except Exception:
                    # 非数值不阻断主流程
                    pass

            # 终版风格展示字段（供模板直接渲染）
            tips = self._build_immuno_tips(msi, tmb_val) or ""
            if (report_data.get_field("immuno_tips") or "").strip() == "":
                report_data.set_field("immuno_tips", tips)

            tmb_summary = self._build_tmb_summary(report_data) or ""
            if (report_data.get_field("tmb_summary") or "").strip() == "":
                report_data.set_field("tmb_summary", tmb_summary)

            msi_summary = self._build_msi_summary(msi) or ""
            if (report_data.get_field("msi_summary") or "").strip() == "":
                report_data.set_field("msi_summary", msi_summary)

            immuno_summary = self._build_immuno_gene_summary(excel_data)
            for field, key in [
                ("immuno_positive_genes", "pos"),
                ("immuno_negative_genes", "neg"),
                ("immuno_hyperprogression_genes", "hyper"),
            ]:
                cur = report_data.get_field(field)
                if cur is None or str(cur).strip() in {"", "未检出"}:
                    report_data.set_field(field, immuno_summary[key])
        except Exception:
            # 兼容别名失败不影响主流程
            pass

        self.logger.info(
            "字段映射完成",
            fields_mapped=len(
                [k for k, v in report_data.context.items() if not isinstance(v, list)]
            ),
            tables_mapped=len([k for k, v in report_data.context.items() if isinstance(v, list)]),
            validation_errors=len(report_data.validation_errors),
        )

        return report_data

    def _build_immuno_tips(self, msi_status: Optional[str], tmb_value) -> Optional[str]:
        """生成终版风格的“用药提示”（肠癌固定写法）。"""
        # 备注：该段落在终版报告中通常为固定科普/提示文本（与具体样本TMB高低不强绑定）
        return (
            "多项临床研究表明，TMB-H的肿瘤对免疫检查点抑制剂有更强的免疫应答效果\n"
            "常用免疫抑制剂有：#帕博利珠单抗、#纳武利尤单抗、#纳武利尤单抗+伊匹木单抗、阿替利珠单抗、"
            "度伐利尤单抗、特瑞普利单抗、信迪利单抗、卡瑞利珠单抗、#替雷利珠单抗、#恩沃利单抗、"
            "#多塔利单抗、#斯鲁利单抗、#普特利单抗、派安普利单抗、赛帕利单抗等"
        )

    def _map_single_values(self, excel_data: ExcelDataSource, report_data: ReportData) -> None:
        """
        映射单值字段

        Args:
            excel_data: Excel数据源
            report_data: 报告数据
        """
        for var_name, mapping in self.single_value_mappings.items():
            # 在Excel数据中查找匹配的字段
            excel_value = None
            matched_column = None

            for excel_column, value in excel_data.single_values.items():
                if mapping.matches_column_name(excel_column):
                    excel_value = value
                    matched_column = excel_column
                    break

            # 如果找到匹配
            if excel_value is not None:
                formatted_value = mapping.format_value(excel_value)
                report_data.set_field(var_name, formatted_value)
                self.logger.debug(
                    "映射字段",
                    variable=var_name,
                    excel_column=matched_column,
                    value=formatted_value,
                )
            else:
                # ✅ 检查字段是否已经有值（比如从文件名提取的sample_id）
                existing_value = report_data.get_field(var_name)
                if existing_value is not None:
                    # 已经有值，不要覆盖
                    self.logger.debug(
                        "字段已有值，跳过映射", variable=var_name, existing_value=existing_value
                    )
                    continue

                # 未找到匹配，使用默认值
                # 终版报告通常要求报告日期存在；若Excel缺失，则自动填充为当天（YYYYMMDD）
                # 避免终版模板出现空白/验证错误。
                if var_name == "report_date":
                    report_data.set_field(var_name, datetime.now().strftime("%Y%m%d"))
                    continue

                if mapping.required:
                    report_data.add_validation_error(
                        f"缺失必填字段: {var_name} ({mapping.synonyms})"
                    )
                    self.logger.warning(
                        "缺失必填字段", variable=var_name, synonyms=mapping.synonyms
                    )

                # 设置默认值
                report_data.set_field(var_name, mapping.default_value)

    def _map_tables(self, excel_data: ExcelDataSource, report_data: ReportData) -> None:
        """
        映射表格数据

        Args:
            excel_data: Excel数据源
            report_data: 报告数据
        """
        for table_name, table_mapping in self.table_mappings.items():
            # 2.1 专用九列表：由 Variations + CtDrug 聚合生成
            if table_name == "variants_2_1":
                rows = self._build_variants_2_1(excel_data, report_data)
                report_data.set_table(table_name, rows)
                self.logger.debug("映射表格(聚合)", table=table_name, rows=len(rows))
                continue
            # Special handling: build targeted_drug_tips by joining Variations with CtDrug
            if table_name == "targeted_drug_tips":
                rows = self._build_targeted_drug_tips(excel_data, report_data)
                report_data.set_table(table_name, rows)
                self.logger.debug("映射表格(聚合)", table=table_name, rows=len(rows))
                continue
            # 🔥 NEW: Special handling for drug detail tables (drug_顺铂, drug_卡铂, etc.)
            if table_name.startswith("drug_"):
                rows = self._build_drug_detail_table(table_name, table_mapping, excel_data)
                report_data.set_table(table_name, rows)
                self.logger.debug("映射药物表格", table=table_name, rows=len(rows))
                continue
            # 查找对应的Excel表格
            excel_table_data = None

            # 首先尝试按sheet_name查找
            if table_mapping.sheet_name:
                excel_table_data = excel_data.get_table_data(table_mapping.sheet_name)

            # 如果没找到，尝试按table_name查找
            if not excel_table_data:
                for sheet_name in excel_data.sheet_names:
                    if table_name.lower() in sheet_name.lower():
                        excel_table_data = excel_data.get_table_data(sheet_name)
                        break

            # 映射表格行
            if excel_table_data:
                mapped_rows = []
                skipped_rows = 0
                filter_stats = {
                    "class_filtered": 0,
                    "low_freq": 0,
                    "not_significant": 0,
                    "invalid": 0,
                }

                for row in excel_table_data:
                    # ✅ 过滤无效数据行（带统计）
                    is_valid, filter_reason = self._validate_table_row_with_reason(table_name, row)
                    if not is_valid:
                        skipped_rows += 1
                        if filter_reason in filter_stats:
                            filter_stats[filter_reason] += 1
                        continue

                    mapped_row = table_mapping.map_row(row)
                    if mapped_row:  # 只添加非空行
                        # CtDrug表兼容：模板历史字段别名（药物适应情况/检测结果/用药提示）
                        if table_name == "chemotherapy":
                            self._apply_ctdrug_template_aliases(mapped_row)
                        mapped_rows.append(mapped_row)

                report_data.set_table(table_name, mapped_rows)

                # INFO级别：输出过滤摘要（仅对variants表）
                if table_name == "variants" and skipped_rows > 0:
                    self.logger.info(
                        "变异数据过滤完成",
                        原始行数=len(excel_table_data),
                        保留行数=len(mapped_rows),
                        过滤总数=skipped_rows,
                        分级过滤=filter_stats.get("class_filtered", 0),
                        低频过滤=filter_stats.get("low_freq", 0),
                        非显著过滤=filter_stats.get("not_significant", 0),
                        无效数据=filter_stats.get("invalid", 0),
                    )

                self.logger.debug(
                    "映射表格",
                    table=table_name,
                    rows=len(mapped_rows),
                    skipped=skipped_rows,
                )
            else:
                # 表格不存在
                if table_mapping.required:
                    report_data.add_validation_error(
                        f"缺失必需表格: {table_name} (sheet: {table_mapping.sheet_name})"
                    )

                # 根据empty_behavior处理
                if table_mapping.empty_behavior == "show_placeholder":
                    report_data.set_table(table_name, [])
                elif table_mapping.empty_behavior == "error" and table_mapping.required:
                    report_data.add_validation_error(f"必需表格 {table_name} 为空")

    def _validate_table_row_with_reason(
        self, table_name: str, row: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        验证表格行是否有效，并返回过滤原因

        Args:
            table_name: 表格名称
            row: 行数据字典

        Returns:
            (是否有效, 过滤原因) - 原因: "class_filtered", "low_freq", "not_significant", "invalid", ""
        """
        # 针对variants表的特殊验证规则（包含智能过滤）
        if table_name == "variants":
            var_filter_config = self.filtering_config.get("variations", {})

            # 检查是否启用过滤
            if not var_filter_config.get("enabled", True):
                # 只做基本验证
                gene_symbol = row.get("Gene_Symbol") or row.get("基因") or row.get("Gene")
                variant = row.get("cHGVS") or row.get("变异")
                if pd.isna(gene_symbol) or gene_symbol is None:
                    return False, "invalid"
                if str(gene_symbol).strip() == "Gene":
                    return False, "invalid"
                if pd.isna(variant) or variant is None:
                    return False, "invalid"
                return True, ""

            # === 基本验证 ===
            basic_config = var_filter_config.get("basic_validation", {})

            if basic_config.get("require_gene", True):
                gene_cols = basic_config.get("gene_columns", ["Gene_Symbol", "基因", "Gene"])
                gene_symbol = None
                for col in gene_cols:
                    gene_symbol = row.get(col)
                    if gene_symbol is not None:
                        break
                if pd.isna(gene_symbol) or gene_symbol is None:
                    return False, "invalid"
                if str(gene_symbol).strip() == "Gene":
                    return False, "invalid"

            if basic_config.get("require_variant", True):
                variant_cols = basic_config.get("variant_columns", ["cHGVS", "变异"])
                variant = None
                for col in variant_cols:
                    variant = row.get(col)
                    if variant is not None:
                        break
                if pd.isna(variant) or variant is None:
                    return False, "invalid"

            # === 分级过滤（若存在Ⅰ/Ⅱ/Ⅲ类列则优先） ===
            class_filter_config = var_filter_config.get("class_filter", {})
            if class_filter_config.get("enabled", False):
                class_cols = class_filter_config.get("class_columns", ["ExistIn552"])
                allowed = {str(x).strip() for x in class_filter_config.get("allowed_classes", [])}
                cls_val = None
                for col in class_cols:
                    if col in row:
                        cls_val = row.get(col)
                        break
                if cls_val is not None and allowed:
                    cls_str = str(cls_val).strip()
                    if cls_str and cls_str not in allowed:
                        return False, "class_filtered"

            # === 智能过滤 ===
            is_high_freq = False
            freq_filter_config = var_filter_config.get("frequency_filter", {})
            if freq_filter_config.get("enabled", True):
                min_freq = freq_filter_config.get("min_frequency", 5.0)
                freq_cols = freq_filter_config.get("frequency_columns", ["Freq(%)", "AF"])
                freq = None
                for col in freq_cols:
                    freq = row.get(col)
                    if freq is not None:
                        break
                if freq is not None and not pd.isna(freq):
                    try:
                        freq_value = float(freq)
                        is_high_freq = freq_value >= min_freq
                    except (ValueError, TypeError):
                        pass

            is_clinically_significant = False
            clin_filter_config = var_filter_config.get("clinical_significance_filter", {})
            if clin_filter_config.get("enabled", True):
                keywords = clin_filter_config.get("significant_keywords", ["Missense", "Nonsense", "Frameshift", "Splice"])
                func_cols = clin_filter_config.get("function_columns", ["Function", "功能", "Type"])
                function = None
                for col in func_cols:
                    function = row.get(col)
                    if function is not None:
                        break
                if function is not None and not pd.isna(function):
                    function_str = str(function)
                    is_clinically_significant = any(kw in function_str for kw in keywords)

            # 保留高频或临床显著的变异
            if not is_high_freq and not is_clinically_significant:
                # 判断具体原因：如果有频率但低，是低频；否则是非显著
                if freq_filter_config.get("enabled", True) and freq is not None and not pd.isna(freq):
                    return False, "low_freq"
                return False, "not_significant"

            return True, ""

        # 其他表格使用原方法
        is_valid = self._is_valid_table_row(table_name, row)
        return is_valid, "" if is_valid else "invalid"

    def _is_valid_table_row(self, table_name: str, row: Dict[str, Any]) -> bool:
        """
        验证表格行是否有效

        Args:
            table_name: 表格名称
            row: 行数据字典

        Returns:
            是否为有效行
        """
        # 针对variants表的特殊验证规则（包含智能过滤）
        if table_name == "variants":
            # 🔥 使用配置中的过滤规则
            var_filter_config = self.filtering_config.get("variations", {})

            # 检查是否启用过滤
            if not var_filter_config.get("enabled", True):
                # 如果过滤未启用，只做基本验证
                gene_symbol = row.get("Gene_Symbol") or row.get("基因") or row.get("Gene")
                variant = row.get("cHGVS") or row.get("变异")

                if pd.isna(gene_symbol) or gene_symbol is None:
                    return False
                if str(gene_symbol).strip() == "Gene":
                    return False
                if pd.isna(variant) or variant is None:
                    return False

                return True

            # === 基本验证配置 ===
            basic_config = var_filter_config.get("basic_validation", {})

            # 基因验证
            if basic_config.get("require_gene", True):
                gene_cols = basic_config.get("gene_columns", ["Gene_Symbol", "基因", "Gene"])
                gene_symbol = None
                for col in gene_cols:
                    gene_symbol = row.get(col)
                    if gene_symbol is not None:
                        break

                if pd.isna(gene_symbol) or gene_symbol is None:
                    return False
                if str(gene_symbol).strip() == "Gene":
                    return False

            # 变异验证
            if basic_config.get("require_variant", True):
                variant_cols = basic_config.get("variant_columns", ["cHGVS", "变异"])
                variant = None
                for col in variant_cols:
                    variant = row.get(col)
                    if variant is not None:
                        break

                if pd.isna(variant) or variant is None:
                    return False

            # === 分级过滤（若存在Ⅰ/Ⅱ/Ⅲ类列则优先） ===
            class_filter_config = var_filter_config.get("class_filter", {})
            if class_filter_config.get("enabled", False):
                class_cols = class_filter_config.get("class_columns", ["ExistIn552"])
                allowed = {str(x).strip() for x in class_filter_config.get("allowed_classes", [])}
                cls_val = None
                for col in class_cols:
                    if col in row:
                        cls_val = row.get(col)
                        break
                if cls_val is not None and allowed:
                    cls_str = str(cls_val).strip()
                    if cls_str and cls_str not in allowed:
                        return False

            # === 智能过滤 ===
            # 策略1: 频率过滤
            is_high_freq = False
            freq_filter_config = var_filter_config.get("frequency_filter", {})

            if freq_filter_config.get("enabled", True):
                min_freq = freq_filter_config.get("min_frequency", 5.0)
                freq_cols = freq_filter_config.get("frequency_columns", ["Freq(%)", "AF"])

                freq = None
                for col in freq_cols:
                    freq = row.get(col)
                    if freq is not None:
                        break

                if freq is not None and not pd.isna(freq):
                    try:
                        freq_value = float(freq)
                        is_high_freq = freq_value >= min_freq
                    except (ValueError, TypeError):
                        pass

            # 策略2: 临床显著性过滤
            is_clinically_significant = False
            clin_filter_config = var_filter_config.get("clinical_significance_filter", {})

            if clin_filter_config.get("enabled", True):
                keywords = clin_filter_config.get("significant_keywords", ["Missense", "Nonsense", "Frameshift", "Splice"])
                func_cols = clin_filter_config.get("function_columns", ["Function", "功能", "Type"])

                function = None
                for col in func_cols:
                    function = row.get(col)
                    if function is not None:
                        break

                if function is not None and not pd.isna(function):
                    function_str = str(function)
                    is_clinically_significant = any(kw in function_str for kw in keywords)

            # 保留高频或临床显著的变异（OR逻辑）
            if not (is_high_freq or is_clinically_significant):
                return False

            return True

        # 针对化疗药物表的验证规则
        elif table_name == "chemotherapy":
            drug_name = row.get("药物") or row.get("Drug")
            gene = row.get("检测基因") or row.get("Gene")

            # 药物名称和检测基因不能都为空
            if (pd.isna(drug_name) or drug_name is None) and (pd.isna(gene) or gene is None):
                return False

            return True

        # 针对检测基因表的验证规则
        elif table_name == "genes":
            gene_name = row.get("Gene_Symbol") or row.get("基因") or row.get("Gene")

            # 基因名称不能为空
            if pd.isna(gene_name) or gene_name is None:
                return False

            # 不能是表头行
            if str(gene_name).strip() == "Gene":
                return False

            return True

        # 其他表格的默认验证：至少有一个字段非空
        non_null_count = sum(
            1 for value in row.values() if not pd.isna(value) and value is not None
        )
        return non_null_count > 0

    def get_mapping_for_variable(self, variable_name: str) -> Optional[FieldMapping]:
        """
        获取变量的映射配置

        Args:
            variable_name: 变量名

        Returns:
            FieldMapping或None
        """
        return self.single_value_mappings.get(variable_name)

    def get_table_mapping(self, table_name: str) -> Optional[TableMapping]:
        """
        获取表格的映射配置

        Args:
            table_name: 表格名

        Returns:
            TableMapping或None
        """
        return self.table_mappings.get(table_name)

    # -------------------- targeted drug knowledge base --------------------
    def _load_targeted_drug_db(self) -> None:
        if self._targeted_drug_db_loaded:
            return
        self._targeted_drug_db_loaded = True

        cfg = self.config_loader.get_setting("knowledge_bases.targeted_drug_db", {}) or {}
        if not isinstance(cfg, dict):
            return
        if not bool(cfg.get("enabled", False)):
            return

        path = cfg.get("path")
        if not path:
            return

        db_path = Path(str(path))
        if not db_path.exists():
            self.logger.warning("靶向药物数据库文件不存在", path=str(db_path))
            return

        try:
            xl = pd.ExcelFile(str(db_path), engine="openpyxl")
        except Exception as e:
            self.logger.warning("打开靶向药物数据库失败", path=str(db_path), error=str(e))
            return

        def find_col(cols: list[Any], *, exact: Optional[str] = None, contains: Optional[str] = None):
            for c in cols:
                s = str(c).strip()
                if exact is not None and s == exact:
                    return c
                if contains is not None and contains in s:
                    return c
            return None

        for sheet in xl.sheet_names:
            try:
                df = xl.parse(sheet)
            except Exception:
                continue

            cols = list(df.columns)
            gene_col = find_col(cols, exact="基因名称")
            level_col = find_col(cols, exact="变异等级")
            c_col = find_col(cols, exact="c_point")
            p_col = find_col(cols, exact="p_point")
            benefit_col = find_col(cols, contains="潜在获益靶向药物")
            caution_col = find_col(cols, contains="可能耐药") or find_col(cols, contains="慎重")

            if gene_col is None or benefit_col is None or caution_col is None:
                continue

            self._targeted_drug_db = df
            self._targeted_drug_db_cols = {
                "gene": str(gene_col),
                "level": str(level_col) if level_col is not None else "",
                "c": str(c_col) if c_col is not None else "",
                "p": str(p_col) if p_col is not None else "",
                "benefit": str(benefit_col),
                "caution": str(caution_col),
            }
            self.logger.info(
                "加载靶向药物数据库成功",
                path=str(db_path),
                sheet=sheet,
                rows=int(len(df)),
            )
            return

        self.logger.warning("未在靶向药物数据库中找到可用sheet", path=str(db_path))

    def _get_targeted_drug_overrides(self) -> dict[str, dict[str, str]]:
        cfg = (
            self.config_loader.get_setting("knowledge_bases.targeted_drug_db.overrides", {}) or {}
        )
        if not isinstance(cfg, dict):
            return {}
        out: dict[str, dict[str, str]] = {}
        for k, v in cfg.items():
            if not isinstance(v, dict):
                continue
            key = str(k).strip().upper()
            out[key] = {str(kk): str(vv) for kk, vv in v.items() if vv is not None}
        return out

    def _get_targeted_drug_db_filters(self) -> dict[str, Any]:
        cfg = self.config_loader.get_setting("knowledge_bases.targeted_drug_db.filters", {}) or {}
        return cfg if isinstance(cfg, dict) else {}

    @staticmethod
    def _cgi_evidence_rank(evidence: str) -> int:
        """Map CGI evidence level to a comparable rank (higher is stronger)."""
        mapping = {
            "fda guidelines": 5,
            "nccn guidelines": 5,
            "nccn/cap guidelines": 5,
            "cpic guidelines": 5,
            "european leukemianet guidelines": 5,
            "late trials": 4,
            "clinical trials": 3,
            "early trials": 2,
            "case report": 1,
            "pre-clinical": 0,
        }
        s = str(evidence or "").strip()
        if not s:
            return -1
        parts = [p.strip().lower() for p in re.split(r"[;,]", s) if p.strip()]
        ranks = [mapping.get(p, -1) for p in parts] or [-1]
        return max(ranks)

    @staticmethod
    def _civic_amp_rank(amp_category: str) -> int:
        """Map CIViC AMP/ASCO/CAP category to a comparable rank (higher is stronger)."""
        s = str(amp_category or "").strip().lower()
        if not s:
            return -1
        if "tier i" in s:
            if "level a" in s:
                return 5
            if "level b" in s:
                return 4
            return 4
        if "tier ii" in s:
            if "level c" in s:
                return 3
            if "level d" in s:
                return 2
            return 2
        if "tier iii" in s:
            return 1
        if "tier iv" in s:
            return 0
        return -1

    @staticmethod
    def _infer_crc(cancer_type: str, *, crc_keywords: list[str]) -> bool:
        s = str(cancer_type or "").strip().lower()
        if not s or s in {"-", "--"}:
            return False
        return any(str(k).strip().lower() in s for k in crc_keywords if str(k).strip())

    @staticmethod
    def _norm_text(v: Any) -> str:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return ""
        s = str(v).strip()
        if s in {"NaN", "nan", "*"}:
            return ""
        return s

    @classmethod
    def _p_point_matches(cls, db_p: str, patient_p: str) -> bool:
        """判断数据库 p_point 是否能匹配样本 pHGVS_S（支持 p.G12X 这类写法）。"""
        db = cls._norm_text(db_p)
        p = cls._norm_text(patient_p)
        if not db or not p:
            return False

        # 直接包含：覆盖精确列举（如 "... p.G12C ..."）
        if p in db:
            return True

        m = re.match(r"^p\.([A-Za-z])(\d+)([A-Za-z\*])$", p)
        if not m:
            return False
        aa, pos, var = m.group(1).upper(), m.group(2), m.group(3).upper()

        # 识别 X 通配：p.G12X / p.Q61X 等
        for xm in re.finditer(r"p\.([A-Za-z])(\d+)X", db):
            aa2, pos2 = xm.group(1).upper(), xm.group(2)
            if aa2 != aa or pos2 != pos:
                continue

            # 仅在该pattern附近解析“除C、D外”这类排除条件
            segment = db[xm.start() : xm.start() + 120]
            if ")" in segment:
                segment = segment.split(")", 1)[0]
            excl: set[str] = set()
            em = re.search(r"除([^外]{0,40})外", segment)
            if em:
                excl = {x.upper() for x in re.findall(r"[A-Za-z\*]", em.group(1))}
            if var in excl:
                continue

            return True

        return False

    def _lookup_targeted_drugs_for_variant(
        self,
        gene: str,
        *,
        c_point: str,
        p_point: str,
        variant_level: str = "",
        cancer_type: str = "",
    ) -> tuple[str, str, float]:
        """查询单个变异对应的药物提示（获益/慎重）并返回匹配分数。"""
        gene_norm = str(gene).strip().upper()
        overrides = self._get_targeted_drug_overrides()
        if gene_norm in overrides:
            ov = overrides[gene_norm]
            benefit = str(ov.get("benefit_drugs", "")).strip() or "--"
            caution = str(ov.get("caution_drugs", "")).strip() or "--"
            return benefit, caution, 100.0

        self._load_targeted_drug_db()
        if self._targeted_drug_db is None:
            return "--", "--", 0.0

        cols = self._targeted_drug_db_cols
        gene_col = cols.get("gene")
        benefit_col = cols.get("benefit")
        caution_col = cols.get("caution")
        c_col = cols.get("c") or None
        p_col = cols.get("p") or None
        level_col = cols.get("level") or None

        df = self._targeted_drug_db
        if not gene_col or gene_col not in df.columns:
            return "--", "--", 0.0

        sub = df[df[gene_col].astype(str).str.strip().str.upper() == gene_norm]
        if sub.empty:
            return "--", "--", 0.0

        best_score = 0.0
        best_benefit = "--"
        best_caution = "--"
        c_point = self._norm_text(c_point)
        p_point = self._norm_text(p_point)
        variant_level = self._norm_text(variant_level)

        filters_cfg = self._get_targeted_drug_db_filters()
        filters_enabled = bool(filters_cfg.get("enabled", False))
        apply_sources = {
            str(x).strip().upper()
            for x in (filters_cfg.get("apply_to_sources") or ["CGI", "CIVIC"])
            if str(x).strip()
        }
        require_position_match = bool(filters_cfg.get("require_position_match", False))

        cancer_cfg = filters_cfg.get("cancer_type", {}) or {}
        cancer_filter_enabled = bool(cancer_cfg.get("enabled", False)) and filters_enabled
        crc_keywords = (
            cancer_cfg.get(
                "crc_keywords",
                [
                    "结直肠",
                    "结肠",
                    "直肠",
                    "乙状结肠",
                    "sigmoid",
                    "colon",
                    "rectal",
                    "colorectal",
                ],
            )
            if isinstance(cancer_cfg, dict)
            else []
        )
        is_crc = self._infer_crc(cancer_type, crc_keywords=crc_keywords if isinstance(crc_keywords, list) else [])
        cgi_allowed_tumor_types = set(
            str(x).strip().upper()
            for x in (
                (cancer_cfg.get("cgi_allowed_primary_tumor_types", ["COREAD"]) if isinstance(cancer_cfg, dict) else ["COREAD"])
                or ["COREAD"]
            )
            if str(x).strip()
        )
        civic_disease_keywords = [
            str(x).strip().lower()
            for x in (
                (cancer_cfg.get("civic_disease_keywords", ["colorectal", "colon", "rectal"]) if isinstance(cancer_cfg, dict) else [])
                or []
            )
            if str(x).strip()
        ]
        missing_patient_cancer_action = str(
            (cancer_cfg.get("if_missing_patient_cancer", "allow") if isinstance(cancer_cfg, dict) else "allow")
        ).strip().lower()

        evidence_cfg = filters_cfg.get("evidence", {}) or {}
        evidence_filter_enabled = bool(evidence_cfg.get("enabled", False)) and filters_enabled
        try:
            cgi_min_rank = int(evidence_cfg.get("cgi_min_rank", 0)) if isinstance(evidence_cfg, dict) else 0
        except Exception:
            cgi_min_rank = 0
        try:
            civic_min_rank = int(evidence_cfg.get("civic_min_rank", 0)) if isinstance(evidence_cfg, dict) else 0
        except Exception:
            civic_min_rank = 0
        missing_evidence_action = str(
            (evidence_cfg.get("if_missing_evidence", "allow") if isinstance(evidence_cfg, dict) else "allow")
        ).strip().lower()

        for _, row in sub.iterrows():
            db_c = self._norm_text(row.get(c_col)) if c_col else ""
            db_p = self._norm_text(row.get(p_col)) if p_col else ""
            db_level = self._norm_text(row.get(level_col)) if level_col else ""

            if db_c:
                if not c_point or db_c != c_point:
                    continue
            if db_p:
                if not p_point or not self._p_point_matches(db_p, p_point):
                    continue

            source_db = self._norm_text(row.get("source_db")).strip().upper()
            should_filter = filters_enabled and (source_db in apply_sources)

            # 生产筛选：必须位点匹配（防止公共库“仅基因级别”条目误入输出）
            if should_filter and require_position_match and not (db_c or db_p):
                continue

            # 生产筛选：按癌种过滤（当前仅对“结直肠癌/CRC”启用分组逻辑；其他癌种默认不做过滤）
            if should_filter and cancer_filter_enabled:
                if not cancer_type or str(cancer_type).strip() in {"-", "--"}:
                    if missing_patient_cancer_action == "reject":
                        continue
                elif is_crc:
                    if source_db == "CGI":
                        tt = self._norm_text(row.get("cgi_primary_tumor_type"))
                        if tt:
                            row_types = {x.strip().upper() for x in tt.split(";") if x.strip()}
                            if row_types and not (row_types & cgi_allowed_tumor_types):
                                continue
                        elif missing_patient_cancer_action == "reject":
                            continue
                    elif source_db == "CIVIC":
                        disease = self._norm_text(row.get("civic_disease")).lower()
                        if disease:
                            if civic_disease_keywords and not any(k in disease for k in civic_disease_keywords):
                                continue
                        elif missing_patient_cancer_action == "reject":
                            continue

            # 生产筛选：按证据等级过滤
            if should_filter and evidence_filter_enabled:
                if source_db == "CGI":
                    e = self._norm_text(row.get("cgi_evidence_level"))
                    rank = self._cgi_evidence_rank(e)
                    if rank < 0:
                        if missing_evidence_action == "reject":
                            continue
                    elif rank < cgi_min_rank:
                        continue
                elif source_db == "CIVIC":
                    amp = self._norm_text(row.get("civic_amp_category"))
                    rank = self._civic_amp_rank(amp)
                    if rank < 0:
                        if missing_evidence_action == "reject":
                            continue
                    elif rank < civic_min_rank:
                        continue

            benefit = self._norm_text(row.get(benefit_col)) if benefit_col else ""
            caution = self._norm_text(row.get(caution_col)) if caution_col else ""

            # 评分：优先匹配更具体的位点；同分优先匹配等级；再优先有内容的行
            score = 1.0
            if db_c:
                score += 2.0
            if db_p:
                score += 2.0
            if variant_level and db_level and variant_level == db_level:
                score += 0.2
            if benefit or caution:
                score += 0.1

            if score > best_score:
                best_score = score
                best_benefit = benefit.strip() or "--"
                best_caution = caution.strip() or "--"

        return best_benefit, best_caution, best_score

    def _load_variants_2_1_baseline(self) -> list[dict[str, str]]:
        """加载九列表“未见突变”基线行（模板契约）。"""
        try:
            cfg_path = Path(self.config_loader.config_dir) / "variant_table_baseline.yaml"
        except Exception:
            return []
        if not cfg_path.exists():
            return []
        try:
            cfg = self.config_loader.load_yaml(str(cfg_path))
        except Exception as e:
            self.logger.warning("读取variants_2_1基线配置失败", path=str(cfg_path), error=str(e))
            return []

        rows = (cfg.get("variants_2_1", {}) or {}).get("unmutated_rows", [])
        if not isinstance(rows, list):
            return []
        out = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            gene = str(r.get("gene") or "").strip()
            transcript = str(r.get("transcript") or "").strip()
            chr_ = str(r.get("chr") or "").strip()
            if not gene:
                continue
            out.append({"gene": gene, "transcript": transcript, "chr": chr_})
        return out

    def _load_immune_gene_sets(self) -> dict[str, set[str]]:
        """加载免疫相关基因列表（正相关/负相关/超进展相关）。

        期望的xlsx结构示例见 `2025.12.12/1-免疫治疗相关基因.xlsx`：
        - 前3列：免疫治疗正相关基因（可能跨多列排版）
        - 中间3列：免疫治疗负相关基因
        - 后2列：免疫超进展相关基因（可能带备注列）
        """
        if self._immune_gene_list_loaded:
            return self._immune_gene_sets
        self._immune_gene_list_loaded = True

        cfg = self.config_loader.get_setting("knowledge_bases.immune_gene_list", {}) or {}
        if not isinstance(cfg, dict) or not bool(cfg.get("enabled", False)):
            self._immune_gene_sets = {}
            return self._immune_gene_sets

        path = cfg.get("path")
        if not path:
            self._immune_gene_sets = {}
            return self._immune_gene_sets

        xlsx_path = Path(str(path))
        if not xlsx_path.exists():
            self.logger.warning("免疫相关基因列表文件不存在", path=str(xlsx_path))
            self._immune_gene_sets = {}
            return self._immune_gene_sets

        try:
            df = pd.read_excel(str(xlsx_path), sheet_name=0, engine="openpyxl")
        except Exception as e:
            self.logger.warning("读取免疫相关基因列表失败", path=str(xlsx_path), error=str(e))
            self._immune_gene_sets = {}
            return self._immune_gene_sets

        def collect(cols: list[str]) -> set[str]:
            genes: set[str] = set()
            for col in cols:
                if col not in df.columns:
                    continue
                for v in df[col].tolist():
                    s = self._norm_text(v)
                    if not s or s == "基因":
                        continue
                    # 去掉可能的备注（如 "EGFR 只要扩增"）
                    s = s.split()[0].strip()
                    if s:
                        genes.add(s.upper())
            return genes

        pos_cols = ["免疫治疗正相关基因", "Unnamed: 1", "Unnamed: 2"]
        neg_cols = ["免疫治疗负相关基因", "Unnamed: 4", "Unnamed: 5"]
        hyper_cols = ["免疫超进展相关基因", "Unnamed: 7"]

        pos = collect(pos_cols)
        neg = collect(neg_cols)
        hyper = collect(hyper_cols)

        extra_pos = cfg.get("extra_positive_genes", []) or []
        if isinstance(extra_pos, list):
            pos |= {str(x).strip().upper() for x in extra_pos if str(x).strip()}

        self._immune_gene_sets = {"pos": pos, "neg": neg, "hyper": hyper}
        self.logger.info(
            "加载免疫相关基因列表成功",
            path=str(xlsx_path),
            pos=len(pos),
            neg=len(neg),
            hyper=len(hyper),
        )
        return self._immune_gene_sets

    def _build_tmb_summary(self, report_data: ReportData) -> Optional[str]:
        """生成终版风格的TMB展示字符串（含TMB-L/H与参考值提示）。"""
        tmb_val = report_data.get_field("tmb_value")
        if tmb_val is None:
            return None
        try:
            tmb = float(tmb_val)
        except Exception:
            return str(tmb_val)

        sample_type = str(report_data.get_field("sample_type") or "组织")
        threshold = 16 if ("血" in sample_type or "blood" in sample_type.lower()) else 10
        level = "TMB-H" if tmb >= threshold else "TMB-L"
        direction = "高于" if tmb >= threshold else "低于"
        unit = str(report_data.get_field("tmb_unit") or "mutations/Mb")

        # 终版常见写法：数值+单位不加空格
        return f"{tmb:.1f}{unit}，{level}\n(本次检测结果{direction}参考值\n{threshold} mutations/Mb)"

    @staticmethod
    def _build_msi_summary(msi_status: Optional[str]) -> Optional[str]:
        if not msi_status:
            return None
        msi = str(msi_status).strip()
        up = msi.upper()
        if up == "MSS":
            return "微卫星稳定型，MSS"
        if up.startswith("MSI"):
            return f"微卫星不稳定型，{msi}"
        return msi

    @staticmethod
    def _build_msi_status_cn(msi_status: Optional[str]) -> Optional[str]:
        """生成MSI中文描述（与终版一致）。"""
        if not msi_status:
            return None
        msi = str(msi_status).strip()
        up = msi.upper()
        if up == "MSS":
            return "微卫星稳定型，MSS"
        if up == "MSI-H":
            return "微卫星高度不稳定，MSI-H"
        if up == "MSI-L":
            return "微卫星低度不稳定，MSI-L"
        return msi

    def _build_immuno_gene_summary(self, excel_data: ExcelDataSource) -> dict[str, str]:
        """生成免疫相关基因检出摘要（用于模板表格）。"""
        gene_sets = self._load_immune_gene_sets()
        if not gene_sets:
            return {
                "pos": "未检出",
                "neg": "未检出",
                "hyper": "未检出",
            }

        variations = excel_data.get_table_data("Variations") or []

        def build(group: str) -> str:
            wanted = gene_sets.get(group, set())
            lines: list[str] = []
            seen: set[str] = set()
            for r in variations:
                level = self._norm_text(r.get("ExistIn552"))
                # 终版：仅使用Ⅰ/Ⅱ类突变进入免疫相关基因汇总
                if level not in {"Ⅰ类", "Ⅱ类"}:
                    continue
                gene = self._norm_text(r.get("Gene_Symbol") or r.get("基因") or r.get("Gene")).upper()
                if not gene or gene not in wanted or gene in seen:
                    continue
                c = self._norm_text(r.get("cHGVS"))
                p = self._norm_text(r.get("pHGVS_S") or r.get("pHGVS_A"))
                if not c:
                    continue
                line = f"{gene}：{c}，{p}" if p else f"{gene}：{c}"
                lines.append(line)
                seen.add(gene)

            if not lines:
                return "未检出"
            return f"检出（{len(lines)}个）\n" + "\n".join(lines)

        return {"pos": build("pos"), "neg": build("neg"), "hyper": build("hyper")}

    def _build_targeted_drug_tips(self, excel_data: ExcelDataSource, report_data: ReportData) -> list[dict]:
        """
        靶向药物提示（四列表）。

        - 优先使用 settings.yaml:knowledge_bases.targeted_drug_db（自建数据库）进行匹配；
        - 若未配置/加载失败，则回退为旧逻辑（Variations x CtDrug）。

        输出列：gene, variant_site, benefit_drugs, caution_drugs
        """
        def get_gene_from_row(row: dict) -> Optional[str]:
            for k in ("Gene_Symbol", "基因", "Gene", "检测基因"):
                v = row.get(k)
                if v not in (None, "", "NaN"):
                    return str(v).strip()
            return None

        variations = excel_data.get_table_data("Variations") or []
        report_cancer_type = self._norm_text(report_data.get_field("cancer_type"))
        gene_to_sites: dict[str, list[dict[str, str]]] = {}
        for r in variations:
            level = self._norm_text(r.get("ExistIn552"))
            # 终版报告：靶向药物提示表仅展示Ⅰ/Ⅱ类
            if level not in {"Ⅰ类", "Ⅱ类"}:
                continue
            gene = get_gene_from_row(r)
            c = self._norm_text(r.get("cHGVS"))
            p = self._norm_text(r.get("pHGVS_S") or r.get("pHGVS_A"))
            if not gene or not c:
                continue
            site = format_variant_site(c, p) or c
            gene_to_sites.setdefault(gene, []).append(
                {"c": c, "p": p, "level": level, "site": site}
            )

        if not gene_to_sites:
            return []

        overrides = self._get_targeted_drug_overrides()
        self._load_targeted_drug_db()
        use_kb = bool(overrides) or self._targeted_drug_db is not None

        # 2) 数据库模式：按基因聚合位点，并按位点选择最佳药物提示
        if use_kb:
            results: list[dict] = []
            for gene, sites in gene_to_sites.items():
                variant_site = "\n".join([s["site"] for s in sites]) or "未见变异"
                best_b, best_c, best_score = "--", "--", 0.0
                for s in sites:
                    b, c, score = self._lookup_targeted_drugs_for_variant(
                        gene,
                        c_point=s["c"],
                        p_point=s["p"],
                        variant_level=s["level"],
                        cancer_type=report_cancer_type,
                    )
                    if score > best_score:
                        best_b, best_c, best_score = b, c, score
                results.append(
                    {
                        "gene": gene,
                        "variant_site": variant_site,
                        "benefit_drugs": best_b or "--",
                        "caution_drugs": best_c or "--",
                    }
                )

            # 保持与Variations中出现顺序一致（避免按字母排序导致“终版顺序”变化）
            order: list[str] = []
            seen: set[str] = set()
            for r in variations:
                g = get_gene_from_row(r)
                if g and g in gene_to_sites and g not in seen:
                    order.append(g)
                    seen.add(g)
            results.sort(key=lambda x: order.index(x["gene"]) if x["gene"] in order else 9999)
            return results

        # 3) 回退逻辑：Variations x CtDrug（旧实现）
        ct = excel_data.get_table_data("CtDrug") or []
        gene_to_variants: dict[str, set[str]] = {
            g: {s["site"] for s in sites if s.get("site")} for g, sites in gene_to_sites.items()
        }
        mutated_genes = set(gene_to_variants.keys())

        def get_ct_gene(row: dict) -> Optional[str]:
            for k in ("检测基因", "Gene", "基因"):
                v = row.get(k)
                if v not in (None, "", "NaN"):
                    return str(v).strip()
            return None

        def get_ct_drug(row: dict) -> Optional[str]:
            for k in ("药物", "Drug", "药物名称"):
                v = row.get(k)
                if v not in (None, "", "NaN"):
                    return str(v).strip()
            return None

        def get_ct_level(row: dict) -> Optional[str]:
            for k in ("等级", "证据等级"):
                v = row.get(k)
                if v not in (None, "", "NaN"):
                    return str(v).strip()
            return None

        results: list[dict] = []
        # 取出提示/描述字段，按关键词将药物分成获益/慎重两类
        def get_ct_tip(row: dict) -> str:
            for k in ("用药提示（仅供参考）", "用药详细描述"):
                v = row.get(k)
                if v not in (None, "", "NaN"):
                    return str(v)
            return ""

        for gene in sorted(mutated_genes):
            var_site = ", ".join(sorted(gene_to_variants.get(gene, []))) or "未见变异"
            benefit_list: list[str] = []
            caution_list: list[str] = []
            seen_b, seen_c = set(), set()

            for row in ct:
                g = get_ct_gene(row)
                if g != gene:
                    continue
                name = get_ct_drug(row)
                if not name:
                    continue
                level = get_ct_level(row)
                tip = get_ct_tip(row)
                item = f"{name}{'（'+level+'）' if level else ''}"

                tip_l = (tip or "").lower()
                # 负向关键词：中文/英文混合，较全面覆盖
                neg_cn = [
                    "耐药", "慎重", "不敏感", "无效", "禁用", "风险", "较差", "较低", "不推荐", "避免", "禁忌", "谨慎",
                    "疗效差", "疗效较差", "无获益", "获益较低", "毒性", "毒副", "副作用", "不良反应增加",
                ]
                neg_en = ["toxic", "toxicity", "resist", "resistance", "decrease", "decreased", "worse", "contraindicated", "avoid"]
                is_caution = any(k in (tip or "") for k in neg_cn) or any(k in tip_l for k in neg_en)

                if is_caution:
                    if item not in seen_c:
                        seen_c.add(item)
                        caution_list.append(item)
                else:
                    if item not in seen_b:
                        seen_b.add(item)
                        benefit_list.append(item)

            results.append(
                {
                    "gene": gene,
                    "variant_site": var_site,
                    "benefit_drugs": "\n".join(benefit_list) if benefit_list else "--",
                    "caution_drugs": "\n".join(caution_list) if caution_list else "--",
                }
            )

        return results

    def _build_variants_2_1(self, excel_data: ExcelDataSource, report_data: ReportData) -> list[dict]:
        """
        生成“2.1 基因变异检测结果及相关靶向药物信息”九列表数据。

        列：gene, transcript, chr, exon, locus, var_type_cn, af_pct, benefit_drugs, caution_drugs
        规则：
        - 取 Variations 的核心字段。
        - 仅展示分级为 Ⅰ/Ⅱ/Ⅲ 类的变异（ExistIn552），对齐终版报告“只展示Ⅰ/Ⅱ/Ⅲ类”。
        - exon 从 ExIn_ID 中提取数字（EX7/Exon7/EX16E -> 7/16）。
        - locus = cHGVS + ',\\n' + pHGVS_S（若p为*则仅cHGVS）。
        - var_type_cn 将 Function 翻译为中文标签。
        - 靶向药物提示：Ⅰ/Ⅱ类优先用自建数据库匹配（缺失则可用overrides），Ⅲ类固定为--。
        - 末尾补齐“未见突变”基线行（config/variant_table_baseline.yaml），用于对齐终版报告展示。
        """
        def exon_num(exid: Any) -> str:
            s = self._norm_text(exid)
            if not s:
                return ""
            m = re.search(r"(?i)(?:EX|EXON)(\d+)", s)
            return m.group(1) if m else s

        def chr_num(v: Any) -> str:
            s = self._norm_text(v)
            if not s:
                return ""
            return re.sub(r"(?i)^chr", "", s).strip()

        variations = excel_data.get_table_data("Variations") or []
        report_cancer_type = self._norm_text(report_data.get_field("cancer_type"))
        out: list[dict] = []
        mutated_genes: set[str] = set()

        for r in variations:
            level = self._norm_text(r.get("ExistIn552"))
            if level not in {"Ⅰ类", "Ⅱ类", "Ⅲ类"}:
                continue

            gene = self._norm_text(r.get("Gene_Symbol") or r.get("基因") or r.get("Gene"))
            if not gene:
                continue

            c = self._norm_text(r.get("cHGVS"))
            p = self._norm_text(r.get("pHGVS_S") or r.get("pHGVS_A"))
            locus = format_variant_site(c, p) or ""

            # Ⅲ类：终版报告不展示药物提示
            if level in {"Ⅰ类", "Ⅱ类"}:
                benefit, caution, _ = self._lookup_targeted_drugs_for_variant(
                    gene,
                    c_point=c,
                    p_point=p,
                    variant_level=level,
                    cancer_type=report_cancer_type,
                )
            else:
                benefit, caution = "--", "--"

            row = {
                "gene": gene,
                "transcript": self._norm_text(r.get("Transcript")),
                "chr": chr_num(r.get("Chr")),
                "exon": exon_num(r.get("ExIn_ID")),
                "locus": locus or "",
                # 批注：变异类型依据 c.HGVS 关键字 del/dup/ins/delins
                "var_type_cn": infer_variant_type_cn(c) or "点突变",
                "af_pct": self._norm_text(r.get("Freq(%)") or r.get("AF")),
                "benefit_drugs": benefit or "--",
                "caution_drugs": caution or "--",
            }
            out.append(row)
            mutated_genes.add(gene)

        # 补齐“未见突变”基线行（若配置存在）
        for base in self._load_variants_2_1_baseline():
            gene = self._norm_text(base.get("gene"))
            if not gene or gene in mutated_genes:
                continue
            out.append(
                {
                    "gene": gene,
                    "transcript": self._norm_text(base.get("transcript")),
                    "chr": self._norm_text(base.get("chr")),
                    "exon": "",
                    "locus": "未见突变",
                    "var_type_cn": "--",
                    "af_pct": "--",
                    "benefit_drugs": "--",
                    "caution_drugs": "--",
                }
            )

        return out

    def _apply_ctdrug_template_aliases(self, row: Dict[str, Any]) -> None:
        """为CtDrug来源的行补齐模板历史别名字段。

        aligned_template_with_cnv_fusion_hla_FIXED.docx 中存在历史字段引用：
        - 化疗表：row.药物适应情况 / row.检测结果
        - 药物明细表：row.用药提示 / row.检测结果

        但真实CtDrug列更常见的是：用药提示（仅供参考）/ 用药详细描述。
        这里统一做一次别名补齐，避免模板渲染为空。
        """
        # 1) 提取“提示”文本（优先用短提示，其次用长描述）
        tip = self._norm_text(row.get("用药提示（仅供参考）"))
        if not tip:
            tip = self._norm_text(row.get("用药提示"))
        if not tip:
            tip = self._norm_text(row.get("Recommendation"))
        if not tip:
            tip = self._norm_text(row.get("用药详细描述"))

        if not tip:
            return

        # 2) 标准化字段（映射配置里的recommendation/result）缺失时补齐
        if self._norm_text(row.get("recommendation")) == "":
            row["recommendation"] = tip
        if self._norm_text(row.get("result")) == "":
            row["result"] = tip

        # 3) 模板历史别名字段：仅在不存在时补齐，避免覆盖外部显式输入
        row.setdefault("药物适应情况", tip)
        row.setdefault("检测结果", tip)
        row.setdefault("用药提示", tip)

    def _build_drug_detail_table(
        self, table_name: str, table_mapping: TableMapping, excel_data: ExcelDataSource
    ) -> list[dict]:
        """
        生成单个药物详细解析表数据

        Args:
            table_name: 表格名称 (e.g., "drug_顺铂")
            table_mapping: 表格映射配置
            excel_data: Excel数据源

        Returns:
            过滤后的药物数据行列表
        """
        # 获取CtDrug数据
        ctdrug_data = excel_data.get_table_data("CtDrug") or []

        # 获取过滤配置
        filter_config = getattr(table_mapping, 'filter', None)
        if not filter_config:
            self.logger.warning(f"药物表格 {table_name} 缺少filter配置")
            return []

        filter_column = filter_config.get('column', '药物')
        filter_values = filter_config.get('values', [])

        if not filter_values:
            self.logger.warning(f"药物表格 {table_name} 的filter.values为空")
            return []

        # 过滤数据：只保留匹配指定药物的行
        filtered_rows = []
        for row in ctdrug_data:
            drug_name = row.get(filter_column) or row.get('药物') or row.get('Drug')
            if drug_name and str(drug_name).strip() in filter_values:
                # 映射行数据（保留原始列名）
                mapped_row = table_mapping.map_row(row)
                if mapped_row:
                    self._apply_ctdrug_template_aliases(mapped_row)
                    filtered_rows.append(mapped_row)

        self.logger.debug(
            f"药物表格过滤完成",
            table=table_name,
            filter_values=filter_values,
            total_ctdrug=len(ctdrug_data),
            filtered=len(filtered_rows)
        )

        return filtered_rows
