"""
Golden regression - CRC358 core outputs

用最小脱敏样本构造一份“类似真实结构”的 Variations Excel，并配套最小基因知识库，
回归验证以下输出口径不会再漂移：
- 2.1 九列表（summary_variants）行数/关键字段
- 计数（total_variants_count / drug_related_count）
- 药物解析（drug_analysis_sections）
- 参考文献编号格式（numbered_references）
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from reportgen.config.loader import ConfigLoader
from reportgen.core.data_cleaner import DataCleaner
from reportgen.core.excel_reader import ExcelReader
from reportgen.core.field_mapper import FieldMapper
from reportgen.core.template_bridge_358 import enhance_report_data
from reportgen.core.template_contract import TemplateContractValidator, select_contract
from reportgen.core.template_renderer import TemplateRenderer
from reportgen.knowledge import GeneKnowledgeProvider


def _write_min_gene_kb(path: Path) -> None:
    gene_analysis = pd.DataFrame(
        [
            {
                "基因名称": "TP53",
                "基因简介": "TP53 简介",
                "基因变异说明": "TP53 变异说明：{{ c_hgvs }}",
                "基因变异解析": "TP53 变异解析示例",
            }
        ]
    )

    # 用药提示解析：仅需满足 GeneKnowledgeProvider._build_drug_analysis_cache 的列识别逻辑
    drug_analysis = pd.DataFrame(
        [
            {
                "基因名称": "TP53",
                "潜在获益靶向/免疫药物解析": "AZD1775",
                "获益_关联分析": "关联分析示例",
                "获益_占位": "",
                "获益_临床解析": "临床解析示例",
                "潜在负相关靶向/免疫药物解析": "",
                "负相关_关联分析": "",
                "负相关_占位": "",
                "负相关_临床解析": "",
            }
        ]
    )

    references = pd.DataFrame(
        [
            {
                "基因名称": "TP53",
                "参考文献": "TP53 相关研究（示例引用）",
            }
        ]
    )

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        gene_analysis.to_excel(writer, sheet_name="基因变异解析", index=False)
        drug_analysis.to_excel(writer, sheet_name="用药提示解析", index=False)
        references.to_excel(writer, sheet_name="参考文献", index=False)


def _write_min_crc358_excel(path: Path) -> None:
    meta = pd.DataFrame(
        [
            {
                "患者姓名": "测试患者001",
                "样本编号": "SAMPLE001",
                "项目名称": "结直肠癌358基因+MSI",
                "癌种": "结直肠癌",
                "性别": "男",
                "年龄": 60,
                "报告日期": "2026-01-01",
            }
        ]
    )

    # 注意：ExcelReader 会跳过只有 1 行数据的表格，因此 Variations 至少给 2 行
    variations = pd.DataFrame(
        [
            {
                "ExistInsmall358": 1,
                "Gene_Symbol": "TP53",
                "cHGVS": "c.844C>T",
                "pHGVS_S": "p.R282W",
                "Transcript": "NM_000546",
                "Chr": "chr17",
                "ExIn_ID": "EX8",
                "Function": "Missense",
                "Freq(%)": 10.5,
                "ExistIn552": 1,
                "CLNSIG": "致病",
            },
            {
                "ExistInsmall358": 1,
                "Gene_Symbol": "APC",
                "cHGVS": "c.3927_3931del",
                "pHGVS_S": "p.E1309fs",
                "Transcript": "NM_000038",
                "Chr": "chr5",
                "ExIn_ID": "EX15",
                "Function": "Frameshift",
                "Freq(%)": 8.0,
                "ExistIn552": 1,
                "CLNSIG": "致病",
            },
        ]
    )

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        meta.to_excel(writer, sheet_name="Meta", index=False)
        variations.to_excel(writer, sheet_name="Variations", index=False)


def test_crc358_golden_regression(tmp_path: Path) -> None:
    repo_root = Path(__file__).parent.parent.parent
    config_dir = repo_root / "config"

    excel_path = tmp_path / "sample_crc358.xlsx"
    kb_path = tmp_path / "gene_kb.xlsx"
    variant_insights_path = tmp_path / "variant_insights.yaml"
    _write_min_crc358_excel(excel_path)
    _write_min_gene_kb(kb_path)
    variant_insights_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "variant_insights": [
                    {
                        "gene": "TP53",
                        "p_hgvs": "p.R282W",
                        "text": "INSIGHT: TP53 p.R282W hotspot example.",
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    # 解析 Excel -> ReportData
    excel_reader = ExcelReader(config_dir=str(config_dir))
    excel_data = excel_reader.read(str(excel_path), include_tables=True)

    field_mapper = FieldMapper(config_dir=str(config_dir))

    # 让模板桥在没有外部靶向药物库时也能稳定产出“获益药物”用于回归
    def _stub_lookup_targeted_drugs_for_variant(
        gene: str,
        *,
        c_point: str,
        p_point: str,
        variant_level: str = "",
        cancer_type: str = "",
    ):
        if str(gene).strip().upper() == "TP53":
            return "AZD1775（C）", "--", 100.0
        return "--", "--", 0.0

    field_mapper._lookup_targeted_drugs_for_variant = _stub_lookup_targeted_drugs_for_variant  # type: ignore[attr-defined]

    report_data = field_mapper.map(excel_data)
    report_data = DataCleaner().validate_and_clean(report_data)

    gene_kb_cfg = {
        "enabled": True,
        "gene_knowledge_db": {
            "enabled": True,
            "path": str(kb_path),
            "sheets": {
                "gene_analysis": "基因变异解析",
                "drug_analysis": "用药提示解析",
                "references": "参考文献",
            },
            "columns": {
                "gene_name": "基因名称",
                "gene_intro": "基因简介",
                "mutation_desc_template": "基因变异说明",
                "mutation_analysis": "基因变异解析",
                "drug_analysis": "药物疗效临床解析",
                "ref_id": "序号",
                "ref_content": "参考文献",
                "ref_genes": "关联基因",
            },
        },
        "variant_insights_db": {
            "enabled": True,
            "path": str(variant_insights_path),
            "format": "yaml",
        },
        "gene_transcript_db": {"enabled": False},
    }
    gene_provider = GeneKnowledgeProvider(config=gene_kb_cfg)

    # 避免测试污染仓库缓存：把 enrichment cache 指向 tmp 目录
    (tmp_path / "data" / "cache").mkdir(parents=True, exist_ok=True)

    report_data = enhance_report_data(
        report_data,
        excel_data,
        field_mapper=field_mapper,
        gene_knowledge_provider=gene_provider,
        cancer_type_gene_provider=None,
        base_path=str(tmp_path),
    )

    # --- 变异表/计数口径 ---
    summary = report_data.get_table("summary_variants")
    assert len(summary) == 2
    assert report_data.get_field("total_variants_count") == 2

    genes = {r.get("gene") for r in summary}
    assert {"TP53", "APC"} <= genes

    # 2.1 位点列格式：有 pHGVS 时 cHGVS 以逗号结尾
    tp53_row = next(r for r in summary if r.get("gene") == "TP53")
    assert str(tp53_row.get("cHGVS", "")).endswith(",")

    # --- 药物解析 ---
    assert report_data.get_field("drug_related_count") == 1
    drug_sections = report_data.get_table("drug_analysis_sections")
    assert len(drug_sections) == 1
    assert drug_sections[0].get("gene") == "TP53"
    assert drug_sections[0].get("drug_name") == "AZD1775"

    # --- 参考文献格式 ---
    refs = report_data.get_table("numbered_references")
    assert refs and refs[0].get("number") == 1
    assert "TP53" in str(refs[0].get("text", ""))

    # --- 位点个性化一句话（批注#27） ---
    sections = report_data.get_table("gene_knowledge_sections")
    assert sections
    tp53_sec = next(s for s in sections if s.get("gene") == "TP53")
    assert str(tp53_sec.get("mutation_analysis", "")).startswith(
        "INSIGHT: TP53 p.R282W hotspot example."
    )

    # --- 契约校验：对齐 v18 模板的关键一致性/引用格式/变量存在性 ---
    contracts_cfg = ConfigLoader(
        config_dir=str(config_dir)
    ).load_template_contracts_config()
    template_path = repo_root / "templates" / "jinja2_template_358_v18.docx"
    contract = select_contract(contracts_cfg, str(template_path))
    assert contract is not None

    renderer = TemplateRenderer()
    template_vars = renderer.get_template_variables(str(template_path))
    loop_item_vars = renderer.get_template_loop_item_variables(str(template_path))
    violations = TemplateContractValidator(contract).validate(
        report_data, template_vars=template_vars, loop_item_vars=loop_item_vars
    )
    assert violations == [], [v.message for v in violations]
