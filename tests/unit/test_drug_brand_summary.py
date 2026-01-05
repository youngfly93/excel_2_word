from pathlib import Path

from reportgen.core.template_bridge_358 import build_marketed_drugs_brand_summary

PROJECT_ROOT = Path(__file__).parent.parent.parent


def test_build_marketed_drugs_brand_summary_filters_unknown() -> None:
    variants = [
        {
            "gene": "TP53",
            "benefit_drugs": "西妥昔单抗（A）\nAZD1775（C）",
            "caution_drugs": "--",
        }
    ]

    summary = build_marketed_drugs_brand_summary(variants, base_path=str(PROJECT_ROOT))

    assert summary.endswith("。")
    assert "西妥昔单抗[爱必妥]" in summary
    assert "AZD1775" not in summary


def test_build_marketed_drugs_brand_summary_empty_returns_none_marker() -> None:
    variants = [{"benefit_drugs": "AZD1775（C）", "caution_drugs": "--"}]
    assert build_marketed_drugs_brand_summary(variants, base_path=str(PROJECT_ROOT)) == "无。"

