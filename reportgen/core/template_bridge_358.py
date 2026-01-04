#!/usr/bin/env python3
"""
Template Bridge for 358-Gene Colorectal Cancer Reports.

This module bridges the gap between the existing reportgen data layer
and the Jinja2 template requirements for the 358-gene panel.

Key responsibilities:
1. Fix ExistIn552 filtering (numeric 1/0 vs Chinese labels)
2. Generate 'variants' table with template-expected columns
3. Generate 'summary_variants' table
4. Generate 'undetected_genes' table
5. Add MSI/TMB summary fields

Python 3.9 compatible.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from reportgen.models.excel_data import ExcelDataSource
from reportgen.models.report_data import ReportData
from reportgen.utils.hgvs_utils import infer_variant_type_cn
from reportgen.knowledge import GeneKnowledgeProvider, CancerTypeGeneProvider
from reportgen.services import PubMedService, ClinicalTrialsService

logger = logging.getLogger(__name__)


# Panel gene definitions for 358-gene colorectal cancer panel
# Class I genes: Primary drug targets and MSI genes
CLASS_I_GENES = {
    "KRAS", "NRAS", "BRAF", "PIK3CA", "ERBB2", "HER2",
    "MLH1", "MSH2", "MSH6", "PMS2", "EPCAM"
}

# Class II genes: Secondary targets and tumor suppressors
CLASS_II_GENES = {
    "APC", "TP53", "SMAD4", "PTEN", "STK11", "FBXW7"
}

# 结直肠癌重要基因列表（批注#3：主表只显示这些基因中的Ⅰ类、Ⅱ类）
# 来源：2025.12.12/2-各癌种重要基因整理.xlsx
# 2025-12-29更新：新增SETD2（参考文档显示为关键突变基因）
CRC_IMPORTANT_GENES = {
    "KRAS", "NRAS", "BRAF", "MLH1", "MSH2", "MSH6", "PMS2", "HER2",
    "NTRK1", "NTRK2", "NTRK3", "TP53", "APC", "PIK3CA", "SMAD4",
    "FBXW7", "RNF43", "CTNNB1", "KMT2D", "ACVR2A", "TCF7L2", "ATM",
    "FAT4", "KMT2C", "ARID1A", "LRP1B", "PTEN", "FAT1", "ZFHX3",
    "AMER1", "GNAS", "ERBB3", "PTPRT", "NF1", "MUTYH", "ERBB2",
    "SETD2"  # 新增：参考文档显示SETD2为重要基因（22.15%突变率）
}

# 免疫治疗相关基因（批注#12：只显示Ⅰ类、Ⅱ类）
# 来源：2025.12.12/1-免疫治疗相关基因.xlsx
# 2025-12-29更新：新增TP53（参考文档显示为免疫正相关基因）
IMMUNE_POSITIVE_GENES = {
    "MLH1", "MSH2", "MSH6", "PMS2", "POLE", "POLD1", "CD274", "PDCD1LG2",
    "TET1", "PMS1", "ERCC2", "ERCC3", "ERCC4", "ERCC5", "BRCA1", "MRE11A",
    "NBN", "RAD50", "RAD51", "RAD51B", "RAD51D", "RAD52", "RAD54L", "BRCA2",
    "BRIP1", "FANCA", "FANCC", "PALB2", "RAD51C", "BLM", "ATM", "ATR",
    "CHEK1", "CHEK2", "MDC1", "MUTYH", "PARP1", "RECQL4", "ARID1A", "ATRX",
    "FANCM", "PRKDC", "CDK12", "MLH3", "MSH3", "FANCI", "ARID1B", "ARID2",
    "KRAS", "SERPINB3", "SERPINB4", "PBRM1",
    "TP53"  # 新增：参考文档显示TP53为免疫正相关基因
}

IMMUNE_NEGATIVE_GENES = {
    "PTEN", "JAK1", "JAK2", "B2M", "CTNNB1", "KEAP1", "EGFR", "ALK",
    "MET", "STK11", "IFNGR1", "IFNGR2"
}

IMMUNE_HYPERPROGRESSION_GENES = {
    "MDM2", "MDM4", "DNMT3A", "EGFR", "CCND1", "FGF3", "FGF4", "FGF19"
}

# 所有免疫相关基因
ALL_IMMUNE_GENES = IMMUNE_POSITIVE_GENES | IMMUNE_NEGATIVE_GENES | IMMUNE_HYPERPROGRESSION_GENES

# 模板中显示的免疫基因 -> Jinja2变量名映射（32个基因）
# 按模板中出现顺序排列
TEMPLATE_IMMUNE_GENE_VARS = {
    # === 正相关基因（13个）===
    "MLH1": "immune_MLH1_result",
    "MSH2": "immune_MSH2_result",
    "MSH6": "immune_MSH6_result",
    "PMS2": "immune_PMS2_result",
    "POLE": "immune_POLE_result",
    "POLD1": "immune_POLD1_result",
    "CD274": "immune_CD274_result",
    "PDCD1LG2": "immune_PDCD1LG2_result",
    "PBRM1": "immune_PBRM1_result",
    "TET1": "immune_TET1_result",
    "SERPINB3": "immune_SERPINB3_result",
    "SERPINB4": "immune_SERPINB4_result",
    "KRAS": "immune_KRAS_result",  # 正相关表格中的KRAS
    # === 负相关基因（10个，不含EGFR/KRAS_STK11/IFNGR特殊变量）===
    "PTEN": "immune_PTEN_result",
    "JAK1": "immune_JAK1_result",
    "JAK2": "immune_JAK2_result",
    "B2M": "immune_B2M_result",
    "CTNNB1": "immune_CTNNB1_result",
    "ALK": "immune_ALK_result",
    "MET": "immune_MET_result",
    "STK11": "immune_STK11_result",
    "KEAP1": "immune_KEAP1_result",
    # === 超进展相关基因（6个，不含EGFR特殊变量）===
    "MDM2": "immune_MDM2_result",
    "MDM4": "immune_MDM4_result",
    "DNMT3A": "immune_DNMT3A_result",
    "CCND1": "immune_CCND1_result",
    "FGF3": "immune_FGF3_result",
    "FGF4": "immune_FGF4_result",
    "FGF19": "immune_FGF19_result",
}

# All panel genes (subset for undetected genes display)
PANEL_DISPLAY_GENES = [
    {"name": "BRAF", "transcript": "NM_004333.4", "chromosome": "7"},
    {"name": "ERBB2", "transcript": "NM_004448.3", "chromosome": "17"},
    {"name": "FBXW7", "transcript": "NM_001349798.2", "chromosome": "4"},
    {"name": "MLH1", "transcript": "NM_000249.4", "chromosome": "3"},
    {"name": "MSH2", "transcript": "NM_000251.3", "chromosome": "2"},
    {"name": "MSH6", "transcript": "NM_000179.3", "chromosome": "2"},
    {"name": "NF1", "transcript": "NM_000267.3", "chromosome": "17"},
    {"name": "NRAS", "transcript": "NM_002524.4", "chromosome": "1"},
    {"name": "NTRK1", "transcript": "NM_001007792.1", "chromosome": "1"},
    {"name": "NTRK2", "transcript": "NM_006180.4", "chromosome": "9"},
    {"name": "NTRK3", "transcript": "NM_001012338.2", "chromosome": "15"},
    {"name": "PIK3CA", "transcript": "NM_006218.4", "chromosome": "3"},
    {"name": "PMS2", "transcript": "NM_000535.7", "chromosome": "7"},
    {"name": "SMAD4", "transcript": "NM_005359.6", "chromosome": "18"},
    {"name": "SMARCA4", "transcript": "NM_001128849.3", "chromosome": "19"},
    {"name": "TCF7L2", "transcript": "NM_001146274.2", "chromosome": "10"},
    {"name": "TSC1", "transcript": "NM_000368.5", "chromosome": "9"},
]

# Mutation type translation
MUTATION_TYPE_MAP = {
    "Missense": "错义突变",
    "Nonsense": "无义突变",
    "CDS-indel": "移码突变",
    "Frameshift": "移码突变",
    "Splice-5": "剪接突变",
    "Splice-3": "剪接突变",
    "Splice": "剪接突变",
    "Inframe": "框内突变",
    "Stop_gain": "无义突变",
    "Stop_loss": "终止密码子丢失",
}


def _norm_text(value: Any) -> str:
    """Normalize text value."""
    if value is None:
        return ""
    s = str(value).strip()
    if s.lower() in ("nan", "none", "*", "-", ""):
        return ""
    return s


def _format_date_yyyymmdd(value: Any) -> str:
    """Format common date inputs to compact YYYYMMDD (used by终版模板抬头字段)."""
    s = _norm_text(value)
    if not s:
        return ""

    # Keep only digits (supports 2025-12-04 / 2025.12.04 / datetime string etc.)
    digits = re.sub(r"[^0-9]", "", s)
    if len(digits) >= 8:
        return digits[:8]
    return s


def _get_gene_class(gene: str, exist_in_552: Any) -> str:
    """
    Determine gene class based on gene name and ExistIn552 value.

    Args:
        gene: Gene symbol
        exist_in_552: ExistIn552 column value (1, 0, or Chinese labels)

    Returns:
        Gene class string: "Ⅰ类", "Ⅱ类", or "Ⅲ类"
    """
    # Prefer explicit class label from Excel if available (终版口径)
    val = _norm_text(exist_in_552)
    if val in ("Ⅰ类", "Ⅱ类", "Ⅲ类"):
        return val

    # Fallback to gene-name based buckets (legacy)
    gene_upper = gene.upper()
    if gene_upper in CLASS_I_GENES:
        return "Ⅰ类"
    if gene_upper in CLASS_II_GENES:
        return "Ⅱ类"

    # Numeric mapping (if exists)
    # For now, default to Ⅲ类 for unknown genes
    return "Ⅲ类"


def _get_mutation_type(function: Any) -> str:
    """Translate mutation function to Chinese (legacy fallback)."""
    func = _norm_text(function)
    return MUTATION_TYPE_MAP.get(func, func or "")


def get_panel_size(excel_data: ExcelDataSource) -> int:
    """根据项目名称获取检测基因数（358或301）。

    优先从项目名称中识别，支持：
    - "结直肠癌358基因+MSI" -> 358
    - "结直肠癌301基因+MSI" -> 301
    - 包含"358"或"301"的任意项目名

    Args:
        excel_data: Excel数据源

    Returns:
        检测基因数（默认358）
    """
    project_name = str(excel_data.single_values.get("project_name", ""))
    if "358" in project_name:
        return 358
    elif "301" in project_name:
        return 301
    return 358  # 默认值


def _extract_exon(exin_id: Any) -> str:
    """Extract exon number from ExIn_ID (e.g., 'EX16' -> '16')."""
    s = _norm_text(exin_id)
    if not s:
        return ""
    match = re.search(r"(?i)(?:EX|EXON|IN)(\d+)", s)
    return match.group(1) if match else s


def _extract_chromosome(chr_val: Any) -> str:
    """Extract chromosome number (remove 'chr' prefix)."""
    s = _norm_text(chr_val)
    if not s:
        return ""
    return re.sub(r"(?i)^chr", "", s).strip()


def _format_frequency(freq: Any) -> str:
    """Format frequency value."""
    val = _norm_text(freq)
    if not val:
        return "--"
    try:
        return f"{float(val):.2f}"
    except (ValueError, TypeError):
        return val


def _normalize_drug_tips_text(gene: str, drug_text: Any) -> str:
    """
    Normalize targeted-drug tip text to align with legacy '终版' output.

    Notes:
    - Keep as a best-effort cleanup at the template-bridge layer (display only).
    - Avoid changing knowledge base files which may be regenerated.
    """
    raw = "" if drug_text is None else str(drug_text)
    raw = raw.replace("\u200b", "").replace("\xa0", " ").strip()
    if not raw or raw in {"*", "-", "--"}:
        return "--"

    gene_upper = (gene or "").strip().upper()

    # Split into logical lines; docxtpl renders '\n' as line breaks in the same cell.
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if not lines:
        return "--"

    # Fix known KB formatting artifacts / legacy display requirements.
    if gene_upper == "ATM":
        cleaned = []
        for ln in lines:
            ln2 = ln.replace("Tuvusertib+Peposertib（C）", "").strip()
            if ln2:
                cleaned.append(ln2)
        lines = cleaned

    if gene_upper == "KRAS":
        cleaned = []
        for ln in lines:
            s = ln.strip()
            if s == "GH35（C）":
                continue
            if s == "Avutometinib+Defactinib（C）":
                s = "Defactinib+Avutometinib（C）"
            cleaned.append(s)
        lines = cleaned

        combo = "Defactinib+Avutometinib（C）"
        anchor_prefix = "福巴替尼+贝美替尼（C）"
        if combo in lines and any(ln.startswith(anchor_prefix) for ln in lines):
            # Remove standalone combo line and append it to the anchor line
            filtered = [ln for ln in lines if ln != combo]
            joined = []
            inserted = False
            for ln in filtered:
                if (not inserted) and ln.startswith(anchor_prefix):
                    joined.append(f"{ln} {combo}")
                    inserted = True
                else:
                    joined.append(ln)
            lines = joined

    # Generic cleanup: drop empty lines after normalization.
    lines = [ln.strip() for ln in lines if ln and ln.strip()]
    return "\n".join(lines) if lines else "--"


def _build_variants_from_variation_rows(
    variation_rows: List[Dict[str, Any]],
    *,
    filter_column: str = "ExistInsmall358",
    filter_class_i_ii_only: bool = True,
    important_genes_only: bool = True,
    drug_lookup: Optional[Callable[[str, str, str, str], Tuple[str, str]]] = None,
) -> List[Dict[str, str]]:
    """
    Build variants table matching the Jinja2 template format from raw Variations rows.

    Columns: gene, transcript, chromosome, exon, cHGVS, pHGVS,
             mutation_type, frequency, gene_class, clinical_significance,
             benefit_drugs, caution_drugs

    Args:
        variation_rows: Raw row dicts from Variations sheet
        filter_column: Column to filter by (default: ExistInsmall358)
        filter_class_i_ii_only: If True, only include Ⅰ类 and Ⅱ类 (批注#3)
        important_genes_only: If True, only include genes in CRC_IMPORTANT_GENES
        drug_lookup: Optional callable to lookup (benefit_drugs, caution_drugs) by
            (gene, c_hgvs, p_hgvs, gene_class).

    Returns:
        List of variant dictionaries
    """
    variants = []

    for row in variation_rows:
        # Filter: only include variants with ExistInsmall358 == 1
        filter_val = row.get(filter_column)
        if filter_val not in (1, "1", True):
            continue

        gene = _norm_text(row.get("Gene_Symbol") or row.get("Gene"))
        if not gene:
            continue

        # 验证cHGVS格式：必须以"c."开头才是真正的变异
        c_hgvs = _norm_text(row.get("cHGVS"))
        if not c_hgvs or not c_hgvs.startswith("c."):
            continue  # 跳过非变异行（如注释、参考数据等）

        # 批注#3: 只显示重要基因列表中的基因
        if important_genes_only and gene.upper() not in CRC_IMPORTANT_GENES:
            continue

        # Get gene class
        gene_class = _get_gene_class(gene, row.get("ExistIn552"))

        # 批注#3: 只显示Ⅰ类和Ⅱ类基因
        if filter_class_i_ii_only and gene_class == "Ⅲ类":
            continue

        # Get pHGVS notation (cHGVS already extracted above)
        p_hgvs = _norm_text(row.get("pHGVS_S") or row.get("pHGVS_A"))
        if not p_hgvs or p_hgvs == "*":
            p_hgvs = "--"

        # Get clinical significance
        clnsig = _norm_text(row.get("CLNSIG"))
        if clnsig and clnsig not in ("*", "-"):
            clinical_significance = clnsig
        else:
            clinical_significance = "致病"  # Default for detected variants

        # Get drug associations (批注#5：来自自建数据库/既往报告口径)
        benefit_drugs = "--"
        caution_drugs = "--"
        if drug_lookup is not None and gene_class in {"Ⅰ类", "Ⅱ类"}:
            try:
                p_for_lookup = "" if p_hgvs in {"--", "*"} else p_hgvs
                benefit_drugs, caution_drugs = drug_lookup(gene, c_hgvs, p_for_lookup, gene_class)
            except Exception:
                benefit_drugs, caution_drugs = "--", "--"
        else:
            drug = _norm_text(row.get("Drug"))
            benefit_drugs = drug if drug and drug not in ("*", "-") else "--"
            caution_drugs = "--"

        # Legacy display normalization for drug tips (终版对齐)
        benefit_drugs = _normalize_drug_tips_text(gene, benefit_drugs)
        caution_drugs = _normalize_drug_tips_text(gene, caution_drugs)

        variant = {
            "gene": gene,
            "transcript": _norm_text(row.get("Transcript")),
            "chromosome": _extract_chromosome(row.get("Chr")),
            "exon": _extract_exon(row.get("ExIn_ID")),
            "cHGVS": c_hgvs,
            "pHGVS": p_hgvs,
            # 批注#16：突变类型依据 c.HGVS 的 del/dup/ins/delins 判定
            "mutation_type": infer_variant_type_cn(c_hgvs) or _get_mutation_type(row.get("Function")) or "点突变",
            "frequency": _format_frequency(row.get("Freq(%)")),
            "gene_class": gene_class,
            "clinical_significance": clinical_significance,
            "benefit_drugs": benefit_drugs,
            "caution_drugs": caution_drugs,
        }
        variants.append(variant)

    return variants


def build_variants_for_template(
    excel_data: ExcelDataSource,
    filter_column: str = "ExistInsmall358",
    filter_class_i_ii_only: bool = True,
    important_genes_only: bool = True,
    drug_lookup: Optional[Callable[[str, str, str, str], Tuple[str, str]]] = None,
) -> List[Dict[str, str]]:
    """
    Build variants table matching the Jinja2 template format.

    Columns: gene, transcript, chromosome, exon, cHGVS, pHGVS,
             mutation_type, frequency, gene_class, clinical_significance,
             benefit_drugs, caution_drugs
    """
    variations = excel_data.get_table_data("Variations") or []
    return _build_variants_from_variation_rows(
        variations,
        filter_column=filter_column,
        filter_class_i_ii_only=filter_class_i_ii_only,
        important_genes_only=important_genes_only,
        drug_lookup=drug_lookup,
    )


def build_filtered_variants_for_template(
    excel_data: ExcelDataSource,
    *,
    field_mapper: Optional[Any] = None,
    filter_column: str = "ExistInsmall358",
    filter_class_i_ii_only: bool = False,
    important_genes_only: bool = False,
    drug_lookup: Optional[Callable[[str, str, str, str], Tuple[str, str]]] = None,
) -> List[Dict[str, str]]:
    """
    Build variants list using the same filtering rule as FieldMapper variants table.

    This aligns with the “终版”口径 where only clinically relevant somatic variants
    are counted/displayed.
    """
    variations = excel_data.get_table_data("Variations") or []

    validate_fn = None
    if field_mapper is not None:
        try:
            validate_fn = getattr(field_mapper, "_validate_table_row_with_reason", None)
        except Exception:
            validate_fn = None

    filtered_rows: List[Dict[str, Any]] = []
    for row in variations:
        if callable(validate_fn):
            try:
                ok, _ = validate_fn("variants", row)
            except Exception:
                ok = True
            if not ok:
                continue

        # Extra guard: must look like a real c.HGVS mutation
        c_hgvs = _norm_text(row.get("cHGVS"))
        if not c_hgvs or not c_hgvs.startswith("c."):
            continue

        filtered_rows.append(row)

    return _build_variants_from_variation_rows(
        filtered_rows,
        filter_column=filter_column,
        filter_class_i_ii_only=filter_class_i_ii_only,
        important_genes_only=important_genes_only,
        drug_lookup=drug_lookup,
    )


def build_all_variants_for_template(
    excel_data: ExcelDataSource,
    filter_column: str = "ExistInsmall358",
    drug_lookup: Optional[Callable[[str, str, str, str], Tuple[str, str]]] = None,
) -> List[Dict[str, str]]:
    """
    Build ALL variants table (including Ⅲ类) for summary section.

    This is used for the full variants list and summary tables that need
    to show Ⅲ类 genes with "(意义未明突变)" annotation.

    Args:
        excel_data: Parsed Excel data
        filter_column: Column to filter by (default: ExistInsmall358)

    Returns:
        List of variant dictionaries (all classes)
    """
    return build_variants_for_template(
        excel_data,
        filter_column=filter_column,
        filter_class_i_ii_only=False,
        important_genes_only=False,
        drug_lookup=drug_lookup,
    )


def build_summary_variants(
    variants: List[Dict[str, str]],
    add_class_iii_annotation: bool = True
) -> List[Dict[str, str]]:
    """
    Build summary variants table (simplified format for summary section).

    Columns: gene, transcript, chromosome, exon, cHGVS, pHGVS,
             mutation_type, frequency, clinical_significance,
             benefit_drugs, caution_drugs

    Args:
        variants: Full variants list
        add_class_iii_annotation: If True, add "(意义未明突变)" for Ⅲ类 (批注#19)

    Returns:
        List of summary variant dictionaries
    """
    summary_variants = []
    for v in variants:
        # 批注#19: Ⅲ类需要加上"（意义未明突变）"
        clinical_significance = v.get("clinical_significance", "致病")
        gene_class = v.get("gene_class", "")
        if add_class_iii_annotation and gene_class == "Ⅲ类":
            if "意义未明" not in clinical_significance:
                clinical_significance = f"{clinical_significance}（意义未明突变）"

        c_hgvs_raw = v.get("cHGVS", "")
        p_hgvs_raw = v.get("pHGVS", "")

        # 终版模板：位点列为“c... , p...”；若无pHGVS则仅显示cHGVS
        p_hgvs_display = "" if p_hgvs_raw in {"", "--", "*"} else p_hgvs_raw
        c_hgvs_display = f"{c_hgvs_raw}," if p_hgvs_display else c_hgvs_raw

        exon_display = v.get("exon", "")
        # 终版模板：剪接/内含子位点显示“内含子X”
        if exon_display and re.search(r"c\.[0-9]+[+-][0-9]+", str(c_hgvs_raw)):
            if not str(exon_display).startswith("内含子"):
                exon_display = f"内含子{exon_display}"

        summary = {
            "gene": v["gene"],
            "transcript": v["transcript"],
            "chromosome": v["chromosome"],
            "exon": exon_display,
            "cHGVS": c_hgvs_display,
            "pHGVS": p_hgvs_display,
            # 批注#16：突变类型依据 c.HGVS 的 del/dup/ins/delins 判定
            "mutation_type": infer_variant_type_cn(c_hgvs_raw) or "点突变",
            "frequency": v["frequency"],
            "gene_class": gene_class,
            "clinical_significance": clinical_significance,
            "benefit_drugs": v["benefit_drugs"],
            "caution_drugs": v["caution_drugs"],
        }
        summary_variants.append(summary)
    return summary_variants


def build_immune_variants(
    excel_data: ExcelDataSource,
    filter_class_i_ii_only: bool = True,
    drug_lookup: Optional[Callable[[str, str, str, str], Tuple[str, str]]] = None,
) -> Dict[str, List[Dict[str, str]]]:
    """
    Build immune-related variants tables (批注#12).

    Separates variants into:
    - positive: 正相关基因 (IMMUNE_POSITIVE_GENES)
    - negative: 负相关基因 (IMMUNE_NEGATIVE_GENES)
    - hyperprogression: 超进展相关基因 (IMMUNE_HYPERPROGRESSION_GENES)

    Args:
        excel_data: Parsed Excel data
        filter_class_i_ii_only: If True, only include Ⅰ类 and Ⅱ类 genes

    Returns:
        Dict with 'positive', 'negative', 'hyperprogression' variant lists
    """
    # Get all 358 panel variants first (without class/important gene filtering)
    all_variants = build_variants_for_template(
        excel_data,
        filter_class_i_ii_only=False,
        important_genes_only=False,
        drug_lookup=drug_lookup,
    )

    positive_variants = []
    negative_variants = []
    hyperprogression_variants = []

    for v in all_variants:
        gene = v["gene"].upper()
        gene_class = v.get("gene_class", "")

        # 批注#12: 只显示Ⅰ类和Ⅱ类
        if filter_class_i_ii_only and gene_class == "Ⅲ类":
            continue

        # Add "(意义未明突变)" annotation for Ⅲ类 if not filtered out
        clinical_sig = v.get("clinical_significance", "致病")
        if gene_class == "Ⅲ类" and "意义未明" not in clinical_sig:
            v = v.copy()
            v["clinical_significance"] = f"{clinical_sig}（意义未明突变）"

        if gene in IMMUNE_POSITIVE_GENES:
            positive_variants.append(v)
        if gene in IMMUNE_NEGATIVE_GENES:
            negative_variants.append(v)
        if gene in IMMUNE_HYPERPROGRESSION_GENES:
            hyperprogression_variants.append(v)

    return {
        "positive": positive_variants,
        "negative": negative_variants,
        "hyperprogression": hyperprogression_variants,
    }


def build_per_gene_immune_results(
    all_variants: List[Dict[str, str]],
) -> Dict[str, str]:
    """
    为模板中的每个免疫基因生成检测结果变量（32个基因）。

    Args:
        all_variants: 所有检测到的变异列表

    Returns:
        Dict: 变量名 -> 检测结果文本
        例如: {"immune_MLH1_result": "检出：c.100C>T，p.Ala34Val"}
    """
    results = {}

    # 按基因分组所有变异
    variants_by_gene: Dict[str, List[Dict]] = {}
    for v in all_variants:
        gene = v.get("gene", "").upper()
        if gene:
            variants_by_gene.setdefault(gene, []).append(v)

    def format_variant(v: Dict) -> str:
        c_hgvs = v.get("cHGVS", "")
        p_hgvs = v.get("pHGVS", "")
        if p_hgvs and p_hgvs not in ("--", "*", ""):
            return f"{c_hgvs}，{p_hgvs}"
        return c_hgvs

    # 处理普通基因映射
    for gene, var_name in TEMPLATE_IMMUNE_GENE_VARS.items():
        gene_upper = gene.upper()
        if gene_upper in variants_by_gene:
            formatted = [format_variant(v) for v in variants_by_gene[gene_upper]]
            results[var_name] = "检出：" + "；".join(formatted)
        else:
            results[var_name] = "未检出有害变异"

    # 处理特殊变量
    # 1. EGFR 负相关和超进展（两个表格都用同样的EGFR检测结果）
    if "EGFR" in variants_by_gene:
        formatted = [format_variant(v) for v in variants_by_gene["EGFR"]]
        egfr_result = "检出：" + "；".join(formatted)
        results["immune_neg_EGFR_result"] = egfr_result
        results["immune_hyper_EGFR_result"] = egfr_result
    else:
        results["immune_neg_EGFR_result"] = "未检出有害变异"
        results["immune_hyper_EGFR_result"] = "未检出有害变异"

    # 2. KRAS/STK11共突变
    kras_detected = "KRAS" in variants_by_gene
    stk11_detected = "STK11" in variants_by_gene
    if kras_detected and stk11_detected:
        results["immune_KRAS_STK11_result"] = "检出共突变"
    elif kras_detected or stk11_detected:
        results["immune_KRAS_STK11_result"] = "未检出共突变"
    else:
        results["immune_KRAS_STK11_result"] = "未检出有害变异"

    # 3. IFNGR1/2（合并显示）
    ifngr1 = variants_by_gene.get("IFNGR1", [])
    ifngr2 = variants_by_gene.get("IFNGR2", [])
    if ifngr1 or ifngr2:
        all_ifngr = ifngr1 + ifngr2
        formatted = [format_variant(v) for v in all_ifngr]
        results["immune_IFNGR_result"] = "检出：" + "；".join(formatted)
    else:
        results["immune_IFNGR_result"] = "未检出有害变异"

    # 4. KRAS/TP53 共突变
    kras_variants = variants_by_gene.get("KRAS", [])
    tp53_variants = variants_by_gene.get("TP53", [])
    if kras_variants and tp53_variants:
        # 两个都检出 - 显示共突变详情
        kras_fmt = "；".join([format_variant(v) for v in kras_variants])
        tp53_fmt = "；".join([format_variant(v) for v in tp53_variants])
        results["immune_KRAS_TP53_result"] = f"TP53：{tp53_fmt}；KRAS：{kras_fmt}"
    elif kras_variants or tp53_variants:
        # 只检出一个
        results["immune_KRAS_TP53_result"] = "未检出共突变"
    else:
        results["immune_KRAS_TP53_result"] = "未检出有害变异"

    # 5. DDR基因（DNA损伤修复相关基因：ATM, BRCA1, BRCA2, CHEK2, PALB2, RAD51等）
    ddr_genes = ["ATM", "BRCA1", "BRCA2", "CHEK2", "PALB2", "RAD51", "RAD51C", "RAD51D", "BARD1", "BRIP1"]
    ddr_detected = []
    for ddr_gene in ddr_genes:
        if ddr_gene in variants_by_gene:
            for v in variants_by_gene[ddr_gene]:
                ddr_detected.append(f"{ddr_gene}：{format_variant(v)}")
    if ddr_detected:
        results["immune_DDR_result"] = "；".join(ddr_detected)
    else:
        results["immune_DDR_result"] = "未检出有害变异"

    return results


def build_undetected_genes(
    detected_genes: Set[str],
    panel_genes: Optional[List[Dict]] = None,
    cancer_type_genes: Optional[List[str]] = None,
    gene_transcript_provider: Optional[GeneKnowledgeProvider] = None,
) -> List[Dict[str, str]]:
    """
    Build undetected genes table.

    Columns: name, transcript, chromosome

    Args:
        detected_genes: Set of gene symbols that have detected variants
        panel_genes: Optional list of panel gene definitions (fallback)
        cancer_type_genes: Optional list of gene names from CancerTypeGeneProvider
        gene_transcript_provider: Optional provider for gene transcript info

    Returns:
        List of undetected gene dictionaries
    """
    # If cancer_type_genes is provided, use it; otherwise fallback to panel_genes
    if cancer_type_genes:
        undetected = []
        detected_upper = {g.upper() for g in detected_genes}
        for gene_name in cancer_type_genes:
            if gene_name.upper() not in detected_upper:
                # Try to get transcript info from provider
                gene_info = {"name": gene_name, "transcript": "", "chromosome": ""}
                if gene_transcript_provider:
                    transcript_info = gene_transcript_provider.get_gene_transcript_info(gene_name)
                    if transcript_info:
                        gene_info["transcript"] = transcript_info.get("transcript", "")
                        gene_info["chromosome"] = transcript_info.get("chromosome", "")
                # Fallback to PANEL_DISPLAY_GENES if available
                if not gene_info["transcript"]:
                    for pg in PANEL_DISPLAY_GENES:
                        if pg["name"].upper() == gene_name.upper():
                            gene_info["transcript"] = pg["transcript"]
                            gene_info["chromosome"] = pg["chromosome"]
                            break
                undetected.append(gene_info)
        return undetected

    # Fallback to panel_genes (original logic)
    if panel_genes is None:
        panel_genes = PANEL_DISPLAY_GENES

    undetected = []
    for gene_info in panel_genes:
        if gene_info["name"] not in detected_genes:
            undetected.append({
                "name": gene_info["name"],
                "transcript": gene_info["transcript"],
                "chromosome": gene_info["chromosome"],
            })
    return undetected


def build_msi_summary(excel_data: ExcelDataSource) -> Dict[str, str]:
    """
    Build MSI summary fields.

    Returns dict with: msi_status, msi_status_cn, msi_summary, msi_result_text
    """
    # 优先使用ExcelReader已抽取的单值（Msisensor解析）
    raw_status = excel_data.single_values.get("MSI状态")
    msi_status = str(raw_status).strip() if raw_status is not None else ""
    if not msi_status:
        msi_status = "MSS"

    up = msi_status.upper()
    if up == "MSS":
        msi_status = "MSS"
        msi_status_cn = "微卫星稳定型，MSS"
        msi_summary = "微卫星稳定型，MSS"
        msi_result_text = "微卫星稳定（MSS）型"
    elif up == "MSI-H":
        msi_status = "MSI-H"
        msi_status_cn = "微卫星高度不稳定，MSI-H"
        msi_summary = "微卫星不稳定型，MSI-H"
        msi_result_text = "微卫星高度不稳定（MSI-H）型"
    elif up == "MSI-L":
        msi_status = "MSI-L"
        msi_status_cn = "微卫星低度不稳定，MSI-L"
        msi_summary = "微卫星不稳定型，MSI-L"
        msi_result_text = "微卫星低度不稳定（MSI-L）型"
    elif up.startswith("MSI"):
        # 兜底：保持原始值
        msi_status_cn = msi_status
        msi_summary = f"微卫星不稳定型，{msi_status}"
        msi_result_text = f"微卫星不稳定（{msi_status}）型"
    else:
        msi_status_cn = msi_status
        msi_summary = msi_status
        msi_result_text = msi_status

    return {
        "msi_status": msi_status,
        "msi_status_cn": msi_status_cn,
        "msi_summary": msi_summary,
        "msi_result_text": msi_result_text,
    }


def build_tmb_summary(excel_data: ExcelDataSource) -> Dict[str, str]:
    """
    Build TMB summary fields.

    Returns dict with: tmb_value, tmb_status, tmb_level_cn, tmb_reference, tmb_summary,
                       tmb_clinical_significance (TMB-H时的临床意义解读)
    """
    # TMB-H 临床意义解读文本（批注要求：TMB-H需添加医学意义解释）
    TMB_H_CLINICAL_SIGNIFICANCE = (
        "肿瘤突变负荷（TMB）是指肿瘤基因组中每兆碱基（Mb）的体细胞突变数量。"
        "研究表明，TMB-H与免疫检查点抑制剂（如PD-1/PD-L1抑制剂）疗效呈正相关。"
        "2020年6月，FDA批准帕博利珠单抗用于TMB-H（≥10 mutations/Mb）的不可切除或转移性实体瘤。"
    )

    # Get TMB from single values
    tmb_val = excel_data.single_values.get("TMB")

    if tmb_val is None:
        return {
            "tmb_value": "--",
            "tmb_status": "L",
            "tmb_level_cn": "低",
            "tmb_reference": 10,
            "tmb_summary": "",
            "tmb_clinical_significance": "",
        }

    try:
        tmb = float(tmb_val)
        # 样本类型决定参考值：组织10；血液16
        sample_type = str(excel_data.single_values.get("样本类型") or "组织")
        threshold = 16 if ("血" in sample_type or "blood" in sample_type.lower()) else 10

        tmb_status = "H" if tmb >= threshold else "L"
        tmb_level_cn = "高" if tmb_status == "H" else "低"
        level = "TMB-H" if tmb_status == "H" else "TMB-L"
        direction = "高于" if tmb_status == "H" else "低于"
        unit = "mutations/Mb"

        # TMB-H时添加临床意义解读
        clinical_significance = TMB_H_CLINICAL_SIGNIFICANCE if tmb_status == "H" else ""

        return {
            "tmb_value": f"{tmb:.1f}",
            "tmb_status": tmb_status,
            "tmb_level_cn": tmb_level_cn,
            "tmb_reference": threshold,
            "tmb_summary": (
                f"{tmb:.1f}{unit}，{level}\n"
                f"(本次检测结果{direction}参考值\n{threshold} mutations/Mb)"
            ),
            "tmb_clinical_significance": clinical_significance,
        }
    except (ValueError, TypeError):
        return {
            "tmb_value": str(tmb_val),
            "tmb_status": "L",
            "tmb_level_cn": "低",
            "tmb_reference": 10,
            "tmb_summary": str(tmb_val),
            "tmb_clinical_significance": "",
        }


def format_immune_positive_result(
    variants: List[Dict[str, str]],
) -> str:
    """
    Format immune positive variants as display text.

    Format: "检出（N个）
    GENE1：cHGVS，pHGVS
    GENE2：cHGVS，pHGVS
    ..."

    If no variants, returns "未检出".
    """
    if not variants:
        return "未检出"

    count = len(variants)
    lines = [f"检出（{count}个）"]

    for v in variants:
        gene = v.get("gene", "")
        c_hgvs = v.get("cHGVS", "")
        p_hgvs = v.get("pHGVS", "")

        if p_hgvs and p_hgvs not in ("--", "*", ""):
            line = f"{gene}：{c_hgvs}，{p_hgvs}"
        else:
            line = f"{gene}：{c_hgvs}"
        lines.append(line)

    return "\n".join(lines)


def format_immune_result(
    variants: List[Dict[str, str]],
    result_type: str = "negative",
) -> str:
    """
    Format immune variants as display text.

    For negative/hyperprogression: returns "未检出" if empty,
    or formatted list of detected variants.

    Args:
        variants: List of variant dictionaries
        result_type: "negative" or "hyperprogression"

    Returns:
        Formatted string
    """
    if not variants:
        return "未检出"

    # Format as list of gene:mutation pairs
    lines = []
    for v in variants:
        gene = v.get("gene", "")
        c_hgvs = v.get("cHGVS", "")
        p_hgvs = v.get("pHGVS", "")

        if p_hgvs and p_hgvs not in ("--", "*", ""):
            line = f"{gene}：{c_hgvs}，{p_hgvs}"
        else:
            line = f"{gene}：{c_hgvs}"
        lines.append(line)

    return "检出：" + "；".join(lines)


def count_drug_related_variants(
    variants: List[Dict[str, str]],
) -> int:
    """
    Count variants that have drug associations.

    A variant is drug-related if benefit_drugs or caution_drugs is not empty/--
    """
    count = 0
    for v in variants:
        benefit = v.get("benefit_drugs", "--")
        caution = v.get("caution_drugs", "--")
        if (benefit and benefit != "--") or (caution and caution != "--"):
            count += 1
    return count


# NCCN table gene definitions for colorectal cancer (2.3 section)
# These are genes with specific NCCN guideline recommendations
# Maps to 31 variables in template v11
NCCN_TABLE_GENES = {
    # EGFR with exon-specific detection (exons 18-21)
    "EGFR": {
        "type": "exon_specific",
        "display": "EGFR",
        "exons": ["18", "19", "20", "21"],
    },
    # KRAS with exon-specific detection (exons 2, 3, 4)
    "KRAS": {
        "type": "exon_specific",
        "display": "KRAS",
        "exons": ["2", "3", "4"],
    },
    # ALK fusion
    "ALK": {"type": "fusion", "display": "ALK"},
    # ROS1 fusion
    "ROS1": {"type": "fusion", "display": "ROS1"},
    # RET fusion
    "RET": {"type": "fusion", "display": "RET"},
    # HER2/ERBB2 mutation and amplification
    "HER2": {
        "type": "mutation_amplification",
        "display": "ERBB2（HER2）",
        "aliases": ["ERBB2"],
    },
    # PIK3CA exon-specific (exons 10, 21)
    "PIK3CA": {
        "type": "exon_specific",
        "display": "PIK3CA",
        "exons": ["10", "21"],
    },
    # MET exon 14 and amplification
    "MET": {
        "type": "exon_amplification",
        "display": "MET",
        "exons": ["14"],
    },
    # NRAS with exon-specific detection (exons 2, 3, 4)
    "NRAS": {
        "type": "exon_specific",
        "display": "NRAS",
        "exons": ["2", "3", "4"],
    },
    # BRAF V600 mutation
    "BRAF": {
        "type": "codon_specific",
        "display": "BRAF",
        "codons": ["V600"],
    },
    # FGFR mutation and fusion
    "FGFR": {
        "type": "mutation_fusion",
        "display": "FGFR1/2/3",
        "genes": ["FGFR1", "FGFR2", "FGFR3"],
    },
    # NTRK fusion detection
    "NTRK": {
        "type": "fusion",
        "display": "NTRK1/2/3",
        "genes": ["NTRK1", "NTRK2", "NTRK3"],
    },
    # KIT with exon-specific detection
    "KIT": {
        "type": "exon_specific",
        "display": "KIT",
        "exons": ["9", "11", "13", "17"],
    },
    # PDGFRA with exon-specific detection
    "PDGFRA": {
        "type": "exon_specific",
        "display": "PDGFRA",
        "exons": ["12", "14", "18"],
    },
    # BRCA1/2 mutation
    "BRCA": {
        "type": "mutation",
        "display": "BRCA1/2",
        "genes": ["BRCA1", "BRCA2"],
    },
    # IDH1/2 mutation
    "IDH": {
        "type": "mutation",
        "display": "IDH1/2",
        "genes": ["IDH1", "IDH2"],
    },
}


def _format_nccn_result(
    variants: List[Dict[str, str]],
    gene_class_annotation: bool = True,
) -> str:
    """
    Format variants for NCCN table display.

    Args:
        variants: List of variant dictionaries for a specific gene
        gene_class_annotation: If True, add "(意义未明突变)" for Ⅲ类

    Returns:
        Formatted result string: variant info or "未检出"
    """
    if not variants:
        return "未检出"

    results = []
    for v in variants:
        c_hgvs = v.get("cHGVS", "")
        p_hgvs = v.get("pHGVS", "")
        gene_class = v.get("gene_class", "")

        # Build variant description
        if p_hgvs and p_hgvs not in ("--", "*", ""):
            variant_desc = f"{c_hgvs}，{p_hgvs}"
        else:
            variant_desc = c_hgvs

        # Add annotation for Ⅲ类 (批注: Ⅲ类需要填进去同时加上"意义未明突变")
        if gene_class_annotation and gene_class == "Ⅲ类":
            variant_desc = f"{variant_desc}（意义未明突变）"

        results.append(variant_desc)

    return "；".join(results) if results else "未检出"


def build_nccn_table_variables(
    all_variants: List[Dict[str, str]],
) -> Dict[str, str]:
    """
    Build NCCN table variables for template (section 2.3).

    Generates 31 variables like:
    - nccn_EGFR_exon18_result, nccn_EGFR_exon19_result, etc.
    - nccn_KRAS_exon2_result, nccn_KRAS_exon3_result, etc.
    - nccn_ALK_result, nccn_ROS1_result, nccn_RET_result
    - nccn_HER2_mutation_result, nccn_HER2_amplification_result
    - nccn_BRAF_V600_result
    - nccn_NTRK_result
    - etc.

    Logic per user annotation:
    - Ⅰ类、Ⅱ类: show result directly
    - Ⅲ类: show result + "(意义未明突变)"
    - Not detected: show "未检出"

    Args:
        all_variants: List of all detected variants

    Returns:
        Dict of NCCN table variables
    """
    nccn_vars: Dict[str, str] = {}

    # Build gene -> variants index
    gene_variants: Dict[str, List[Dict[str, str]]] = {}
    for v in all_variants:
        gene = v.get("gene", "").upper()
        if gene not in gene_variants:
            gene_variants[gene] = []
        gene_variants[gene].append(v)

    for gene_key, config in NCCN_TABLE_GENES.items():
        gene_type = config["type"]
        gene_names = config.get("genes", [gene_key]) + config.get("aliases", [])

        if gene_type == "exon_specific":
            # Exon-specific gene: separate variable per exon
            gene_upper = gene_key.upper()
            gene_var_list = gene_variants.get(gene_upper, [])

            for exon in config["exons"]:
                exon_variants = [
                    v for v in gene_var_list
                    if v.get("exon", "") == exon
                ]
                var_name = f"nccn_{gene_key}_exon{exon}_result"
                nccn_vars[var_name] = _format_nccn_result(exon_variants)

            # Also provide an overall result
            var_name = f"nccn_{gene_key}_result"
            nccn_vars[var_name] = _format_nccn_result(gene_var_list)

        elif gene_type == "fusion":
            # Fusion detection: check multiple genes
            matched_variants = []
            for gn in gene_names:
                matched_variants.extend(gene_variants.get(gn.upper(), []))
            var_name = f"nccn_{gene_key}_result"
            nccn_vars[var_name] = _format_nccn_result(matched_variants)

        elif gene_type == "mutation_amplification":
            # HER2: separate mutation and amplification results
            matched_variants = []
            for gn in gene_names:
                matched_variants.extend(gene_variants.get(gn.upper(), []))

            # Separate by variant type
            mutation_vars = [v for v in matched_variants if "扩增" not in v.get("mutation_type", "")]
            amplification_vars = [v for v in matched_variants if "扩增" in v.get("mutation_type", "")]

            nccn_vars[f"nccn_{gene_key}_mutation_result"] = _format_nccn_result(mutation_vars)
            nccn_vars[f"nccn_{gene_key}_amplification_result"] = _format_nccn_result(amplification_vars)
            nccn_vars[f"nccn_{gene_key}_result"] = _format_nccn_result(matched_variants)

        elif gene_type == "exon_amplification":
            # MET: exon 14 skipping and amplification
            gene_upper = gene_key.upper()
            gene_var_list = gene_variants.get(gene_upper, [])

            for exon in config.get("exons", []):
                exon_variants = [
                    v for v in gene_var_list
                    if v.get("exon", "") == exon or "14" in str(v.get("exon", ""))
                ]
                var_name = f"nccn_{gene_key}_exon{exon}_result"
                nccn_vars[var_name] = _format_nccn_result(exon_variants)

            # Amplification
            amplification_vars = [v for v in gene_var_list if "扩增" in v.get("mutation_type", "")]
            nccn_vars[f"nccn_{gene_key}_amplification_result"] = _format_nccn_result(amplification_vars)
            nccn_vars[f"nccn_{gene_key}_result"] = _format_nccn_result(gene_var_list)

        elif gene_type == "codon_specific":
            # BRAF: V600 specific
            gene_upper = gene_key.upper()
            gene_var_list = gene_variants.get(gene_upper, [])

            for codon in config.get("codons", []):
                # Match variants at this codon position (e.g., V600E, V600K)
                codon_variants = [
                    v for v in gene_var_list
                    if codon in v.get("pHGVS", "") or codon in v.get("cHGVS", "")
                ]
                var_name = f"nccn_{gene_key}_{codon}_result"
                nccn_vars[var_name] = _format_nccn_result(codon_variants)

            nccn_vars[f"nccn_{gene_key}_result"] = _format_nccn_result(gene_var_list)

        elif gene_type == "mutation_fusion":
            # FGFR: separate mutation and fusion
            matched_variants = []
            for gn in gene_names:
                matched_variants.extend(gene_variants.get(gn.upper(), []))

            # Separate by variant type
            mutation_vars = [v for v in matched_variants if "融合" not in v.get("mutation_type", "")]
            fusion_vars = [v for v in matched_variants if "融合" in v.get("mutation_type", "")]

            nccn_vars[f"nccn_{gene_key}_mutation_result"] = _format_nccn_result(mutation_vars)
            nccn_vars[f"nccn_{gene_key}_fusion_result"] = _format_nccn_result(fusion_vars)
            nccn_vars[f"nccn_{gene_key}_result"] = _format_nccn_result(matched_variants)

        elif gene_type == "mutation":
            # BRCA, IDH: simple mutation detection across multiple genes
            matched_variants = []
            for gn in gene_names:
                matched_variants.extend(gene_variants.get(gn.upper(), []))
            var_name = f"nccn_{gene_key}_result"
            nccn_vars[var_name] = _format_nccn_result(matched_variants)

    return nccn_vars


def build_nccn_detected_rows(
    all_variants: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    """
    Build dynamic NCCN table rows for detected variants only.

    Returns a list of rows, each with:
    - gene: Gene display name (e.g., "KRAS", "EGFR")
    - content: Detection content (e.g., "外显子2", "融合", "密码子600")
    - result: Variant result with annotation for Ⅲ类

    Only includes genes that have detected variants (Ⅰ类, Ⅱ类, or Ⅲ类).
    Logic per user annotation:
    - Ⅰ类、Ⅱ类: show result directly
    - Ⅲ类: show result + "(意义未明突变)"

    Args:
        all_variants: List of all detected variants

    Returns:
        List of row dictionaries for Jinja2 for loop
    """
    rows: List[Dict[str, str]] = []

    # Build gene -> variants index
    gene_variants: Dict[str, List[Dict[str, str]]] = {}
    for v in all_variants:
        gene = v.get("gene", "").upper()
        if gene not in gene_variants:
            gene_variants[gene] = []
        gene_variants[gene].append(v)

    # Process each NCCN gene in order
    for gene_key, config in NCCN_TABLE_GENES.items():
        gene_type = config["type"]
        display_name = config.get("display", gene_key)
        gene_names = config.get("genes", [gene_key]) + config.get("aliases", [])

        # Collect all variants for this gene
        matched_variants: List[Dict[str, str]] = []
        for gn in gene_names:
            matched_variants.extend(gene_variants.get(gn.upper(), []))

        # Also check the main gene key
        matched_variants.extend(gene_variants.get(gene_key.upper(), []))

        # Remove duplicates (by comparing essential fields)
        seen = set()
        unique_variants = []
        for v in matched_variants:
            key = (v.get("gene", ""), v.get("cHGVS", ""), v.get("pHGVS", ""))
            if key not in seen:
                seen.add(key)
                unique_variants.append(v)

        if not unique_variants:
            continue  # Skip genes with no detected variants

        # Generate rows based on gene type
        if gene_type == "exon_specific":
            # Group by exon
            exon_groups: Dict[str, List[Dict[str, str]]] = {}
            for v in unique_variants:
                exon = v.get("exon", "其他")
                if exon not in exon_groups:
                    exon_groups[exon] = []
                exon_groups[exon].append(v)

            for exon, variants in exon_groups.items():
                content = f"外显子{exon}" if exon != "其他" else "其他"
                result = _format_nccn_result(variants)
                rows.append({"gene": display_name, "content": content, "result": result})

        elif gene_type == "fusion":
            # Fusion type
            result = _format_nccn_result(unique_variants)
            rows.append({"gene": display_name, "content": "融合", "result": result})

        elif gene_type == "mutation_amplification":
            # Separate mutation and amplification
            mutation_vars = [v for v in unique_variants if "扩增" not in v.get("mutation_type", "")]
            amplification_vars = [v for v in unique_variants if "扩增" in v.get("mutation_type", "")]

            if mutation_vars:
                result = _format_nccn_result(mutation_vars)
                rows.append({"gene": display_name, "content": "突变", "result": result})
            if amplification_vars:
                result = _format_nccn_result(amplification_vars)
                rows.append({"gene": display_name, "content": "扩增", "result": result})

        elif gene_type == "exon_amplification":
            # Exon-specific and amplification
            exon_vars = [v for v in unique_variants if "扩增" not in v.get("mutation_type", "")]
            amplification_vars = [v for v in unique_variants if "扩增" in v.get("mutation_type", "")]

            if exon_vars:
                # Group by exon
                exon_groups = {}
                for v in exon_vars:
                    exon = v.get("exon", "14")
                    if exon not in exon_groups:
                        exon_groups[exon] = []
                    exon_groups[exon].append(v)
                for exon, variants in exon_groups.items():
                    content = f"外显子{exon}跳跃" if exon == "14" else f"外显子{exon}"
                    result = _format_nccn_result(variants)
                    rows.append({"gene": display_name, "content": content, "result": result})

            if amplification_vars:
                result = _format_nccn_result(amplification_vars)
                rows.append({"gene": display_name, "content": "扩增", "result": result})

        elif gene_type == "codon_specific":
            # Codon-specific (like BRAF V600)
            result = _format_nccn_result(unique_variants)
            codons = config.get("codons", [""])
            content = f"密码子{codons[0]}" if codons else "突变"
            rows.append({"gene": display_name, "content": content, "result": result})

        elif gene_type == "mutation_fusion":
            # Separate mutation and fusion
            mutation_vars = [v for v in unique_variants if "融合" not in v.get("mutation_type", "")]
            fusion_vars = [v for v in unique_variants if "融合" in v.get("mutation_type", "")]

            if mutation_vars:
                result = _format_nccn_result(mutation_vars)
                rows.append({"gene": display_name, "content": "突变", "result": result})
            if fusion_vars:
                result = _format_nccn_result(fusion_vars)
                rows.append({"gene": display_name, "content": "融合", "result": result})

        elif gene_type == "mutation":
            # Simple mutation
            result = _format_nccn_result(unique_variants)
            rows.append({"gene": display_name, "content": "突变", "result": result})

    return rows


def enhance_report_data(
    report_data: ReportData,
    excel_data: ExcelDataSource,
    *,
    field_mapper: Optional[Any] = None,
    gene_knowledge_provider: Optional[GeneKnowledgeProvider] = None,
    cancer_type_gene_provider: Optional[CancerTypeGeneProvider] = None,
    base_path: Optional[str] = None,
) -> ReportData:
    """
    Enhance ReportData with template-specific fields for 358-gene panel.

    Adds:
    - variants (主表：只含重要基因的Ⅰ类、Ⅱ类 - 批注#3)
    - all_variants (全部变异，含Ⅲ类)
    - summary_variants (汇总表：含Ⅲ类但加标注 - 批注#19)
    - immune_positive_variants (免疫正相关 - 批注#12)
    - immune_negative_variants (免疫负相关)
    - immune_hyperprogression_variants (超进展相关)
    - undetected_genes (未检出基因，动态按癌种获取 - 批注#33)
    - gene_knowledge_sections (基因诊疗知识章节 - 批注#20-35)
    - numbered_references (编号参考文献列表 - 批注#34)
    - MSI summary fields
    - TMB summary fields

    Args:
        report_data: Existing ReportData from FieldMapper
        excel_data: Original Excel data
        field_mapper: Optional FieldMapper for drug lookup
        gene_knowledge_provider: Optional GeneKnowledgeProvider for gene knowledge
        cancer_type_gene_provider: Optional CancerTypeGeneProvider for cancer-specific genes
        base_path: Base path for loading knowledge databases

    Returns:
        Enhanced ReportData
    """
    # Optional: leverage FieldMapper's knowledge base (targeted_drug_db) for drug tips
    drug_lookup: Optional[Callable[[str, str, str, str], Tuple[str, str]]] = None
    if field_mapper is not None:
        try:
            lookup_fn = getattr(field_mapper, "_lookup_targeted_drugs_for_variant", None)
        except Exception:
            lookup_fn = None

        if callable(lookup_fn):
            def drug_lookup(gene: str, c_hgvs: str, p_hgvs: str, gene_class: str) -> Tuple[str, str]:
                try:
                    benefit, caution, _ = lookup_fn(
                        gene, c_point=c_hgvs, p_point=p_hgvs, variant_level=gene_class
                    )
                    return (benefit or "--", caution or "--")
                except Exception as e:
                    logger.warning(f"药物查询失败: gene={gene}, c_hgvs={c_hgvs}, error={e}")
                    return ("--", "--")

    # 终版口径：以FieldMapper variants表的过滤规则为准（避免直接按“真实c.HGVS”全量计数）
    detected_variants = build_filtered_variants_for_template(
        excel_data,
        field_mapper=field_mapper,
        filter_class_i_ii_only=False,
        important_genes_only=False,
        drug_lookup=drug_lookup,
    )
    report_data.set_table("all_variants", detected_variants)

    # Build main variants table (批注#3: 只含重要基因的Ⅰ类、Ⅱ类)
    variants = [
        v
        for v in detected_variants
        if v.get("gene", "").upper() in CRC_IMPORTANT_GENES
        and v.get("gene_class") in {"Ⅰ类", "Ⅱ类"}
    ]
    report_data.set_table("variants", variants)

    # Build summary variants (批注#19: Ⅲ类加"意义未明突变"标注)
    summary_variants = build_summary_variants(detected_variants)
    report_data.set_table("summary_variants", summary_variants)

    # Build NCCN table variables (section 2.3)
    # Logic: Ⅰ/Ⅱ类 show result; Ⅲ类 show result + "(意义未明突变)"; not detected = "未检出"
    nccn_vars = build_nccn_table_variables(detected_variants)
    for var_name, var_value in nccn_vars.items():
        report_data.set_field(var_name, var_value)

    # Build NCCN detected rows for dynamic table (only shows detected genes)
    # Used with Jinja2 {% for row in nccn_detected_rows %}
    nccn_detected_rows = build_nccn_detected_rows(detected_variants)
    report_data.set_table("nccn_detected_rows", nccn_detected_rows)

    # Build immune variants (批注#12: 只含Ⅰ类、Ⅱ类)
    immune_variants = build_immune_variants(
        excel_data, filter_class_i_ii_only=True, drug_lookup=drug_lookup
    )
    report_data.set_table("immune_positive_variants", immune_variants["positive"])
    report_data.set_table("immune_negative_variants", immune_variants["negative"])
    report_data.set_table("immune_hyperprogression_variants", immune_variants["hyperprogression"])

    # Generate formatted immune result strings for template (v8 template variables)
    # immune_positive_count: 正相关基因数量
    report_data.set_field("immune_positive_count", len(immune_variants["positive"]))

    # immune_positive_result: 正相关基因完整显示文本
    # Format: "检出（N个）\nGENE1：cHGVS，pHGVS\n..."
    report_data.set_field(
        "immune_positive_result",
        format_immune_positive_result(immune_variants["positive"])
    )

    # immune_positive_genes: 仅基因变异列表（不含"检出（N个）"前缀）
    # Format: "GENE1：cHGVS，pHGVS\nGENE2：cHGVS，pHGVS\n..."
    if immune_variants["positive"]:
        positive_genes_lines = []
        for v in immune_variants["positive"]:
            gene = v.get("gene", "")
            c_hgvs = v.get("cHGVS", "")
            p_hgvs = v.get("pHGVS", "")
            if p_hgvs and p_hgvs not in ("--", "*", ""):
                positive_genes_lines.append(f"{gene}：{c_hgvs}，{p_hgvs}")
            else:
                positive_genes_lines.append(f"{gene}：{c_hgvs}")
        report_data.set_field("immune_positive_genes", "\n".join(positive_genes_lines))
    else:
        report_data.set_field("immune_positive_genes", "")

    # immune_negative_result: 负相关基因结果 ("未检出" 或检出列表)
    report_data.set_field(
        "immune_negative_result",
        format_immune_result(immune_variants["negative"], "negative")
    )

    # immune_hyperprogression_result: 超进展相关基因结果 ("未检出" 或检出列表)
    report_data.set_field(
        "immune_hyperprogression_result",
        format_immune_result(immune_variants["hyperprogression"], "hyperprogression")
    )

    # 生成每个免疫基因的检测结果变量（32个基因 + 3个特殊变量）
    per_gene_immune_results = build_per_gene_immune_results(detected_variants)
    for var_name, result_text in per_gene_immune_results.items():
        report_data.set_field(var_name, result_text)

    # Statistics fields (v8 template variables)
    # total_variants_count: 总变异数（all_variants包含Ⅰ/Ⅱ/Ⅲ类）
    report_data.set_field("total_variants_count", len(detected_variants))

    # drug_related_count: 药物相关变异数
    report_data.set_field("drug_related_count", count_drug_related_variants(variants))

    # panel_gene_count: 检测基因数（358或301）
    report_data.set_field("panel_gene_count", get_panel_size(excel_data))

    # Build undetected genes (批注#33: 根据癌种动态生成基因检测列表)
    detected_genes = {v["gene"] for v in detected_variants}
    cancer_type_genes_list: Optional[List[str]] = None

    # 尝试从 CancerTypeGeneProvider 获取癌种特异性基因列表
    if cancer_type_gene_provider is not None:
        try:
            cancer_type_gene_provider.load(base_path)
            # 获取癌种名称（优先使用已解析的cancer_type字段）
            cancer_type_for_genes = _norm_text(report_data.get_field("cancer_type"))
            if not cancer_type_for_genes or cancer_type_for_genes in {"-", "--"}:
                # 回退：从项目名称或临床诊断推断
                project_name = _norm_text(report_data.get_field("project_name"))
                clinical_diagnosis = _norm_text(report_data.get_field("clinical_diagnosis"))
                for hint in [project_name, clinical_diagnosis]:
                    if any(k in hint for k in ("结直肠", "结肠", "直肠", "肠")):
                        cancer_type_for_genes = "肠癌"
                        break

            if cancer_type_for_genes:
                cancer_type_genes_list = cancer_type_gene_provider.get_genes_for_cancer(
                    cancer_type_for_genes
                )
        except Exception:
            # 加载失败时静默回退到默认列表
            pass

    undetected_genes = build_undetected_genes(
        detected_genes,
        cancer_type_genes=cancer_type_genes_list,
        gene_transcript_provider=gene_knowledge_provider,
    )
    report_data.set_table("undetected_genes", undetected_genes)

    # MSI/TMB 字段由 FieldMapper 生成（终版口径）；此处仅做缺失兜底，避免覆盖
    for key, value in build_msi_summary(excel_data).items():
        cur = report_data.get_field(key)
        if cur is None or str(cur).strip() in {"", "--"}:
            report_data.set_field(key, value)

    for key, value in build_tmb_summary(excel_data).items():
        cur = report_data.get_field(key)
        if cur is None or str(cur).strip() in {"", "--"}:
            report_data.set_field(key, value)

    # Build gene knowledge sections (批注#20-35: 基因诊疗知识)
    if gene_knowledge_provider is not None:
        try:
            # Load knowledge base if not already loaded
            gene_knowledge_provider.load(base_path)

            # Build knowledge sections for all detected variants
            # Use detected_variants to include all detected mutations (终版口径)
            gene_knowledge_sections = gene_knowledge_provider.build_all_gene_knowledge_sections(
                variants=detected_variants,
                cancer_type="结直肠癌"
            )
            report_data.set_table("gene_knowledge_sections", gene_knowledge_sections)

            # Build drug analysis sections (用药提示解析)
            # Use variants (主表) which contains drug information
            drug_analysis_sections = gene_knowledge_provider.build_drug_analysis_sections(
                variants=variants
            )
            report_data.set_table("drug_analysis_sections", drug_analysis_sections)

            # Build references (参考文献)
            references = gene_knowledge_provider.build_all_references_flat(
                variants=detected_variants,
                max_per_gene=5
            )
            report_data.set_table("references", references)

            # Also provide grouped references by gene
            references_by_gene = gene_knowledge_provider.build_references(
                variants=detected_variants,
                max_per_gene=5
            )
            report_data.set_table("references_by_gene", references_by_gene)

            # Build numbered references for template (批注#34: 参考文献自动汇总)
            # 使用 PubMed/ClinicalTrials 服务自动丰富参考文献信息
            cache_dir = Path(base_path) / "data" / "cache" if base_path else Path("data/cache")
            pubmed_cache = cache_dir / "pubmed_cache.json"
            nct_cache = cache_dir / "nct_cache.json"

            try:
                pubmed_service = PubMedService(
                    cache_path=str(pubmed_cache) if pubmed_cache.parent.exists() else None,
                    auto_save=True
                )
                nct_service = ClinicalTrialsService(
                    cache_path=str(nct_cache) if nct_cache.parent.exists() else None,
                    auto_save=True
                )

                # 使用丰富化的参考文献（自动从 PubMed/NCT 补全信息）
                numbered_references = gene_knowledge_provider.build_enriched_references(
                    variants=detected_variants,
                    pubmed_service=pubmed_service,
                    clinicaltrials_service=nct_service,
                    max_per_gene=5,
                    enrich_missing=True
                )
            except Exception:
                # 如果服务初始化失败，回退到基础方法
                numbered_references = gene_knowledge_provider.build_numbered_references(
                    variants=detected_variants,
                    max_per_gene=5
                )

            report_data.set_table("numbered_references", numbered_references)

        except Exception:
            # Silent failure - don't block report generation
            pass

    # --- v8/v9 终版模板抬头字段补齐 ---
    # 报告日期：若上游未提供，兜底为当天（YYYYMMDD）
    if not _norm_text(report_data.get_field("report_date")):
        report_data.set_field("report_date", datetime.now().strftime("%Y%m%d"))

    # 癌种：358结直肠项目若缺失/为"-"，兜底为“结直肠癌”
    cancer_type = _norm_text(report_data.get_field("cancer_type"))
    if not cancer_type or cancer_type in {"-", "--"}:
        project_name = _norm_text(report_data.get_field("project_name"))
        if any(k in project_name for k in ("结直肠", "结肠", "直肠", "肠", "358", "301")):
            report_data.set_field("cancer_type", "结直肠癌")

    # 报告编号：若缺失，优先用病理号生成（示例：MLJY-LZ258792）
    if not _norm_text(report_data.get_field("report_number")):
        pathology_id = _norm_text(report_data.get_field("pathology_id"))
        if pathology_id:
            pid = pathology_id.upper()
            if pid.startswith("MLJY-"):
                report_data.set_field("report_number", pid)
            elif pid.startswith("LZ") or re.match(r"^[A-Z]{2}\d+$", pid):
                report_data.set_field("report_number", f"MLJY-{pid}")
            else:
                report_data.set_field("report_number", pid)

    # 送检日期：终版模板使用sample_date（YYYYMMDD）；优先receive_date，其次collection_date
    if not _norm_text(report_data.get_field("sample_date")):
        raw = report_data.get_field("receive_date") or report_data.get_field("collection_date")
        sample_date = _format_date_yyyymmdd(raw)
        if sample_date:
            report_data.set_field("sample_date", sample_date)

    # 参考文献：即使知识库未加载，也保证模板变量存在（空列表即可安全渲染）
    if not report_data.has_table("references"):
        report_data.set_table("references", [])

    return report_data
