from __future__ import annotations

from pathlib import Path

import yaml

from reportgen.knowledge import GeneKnowledgeProvider


def test_variant_insight_is_injected_into_gene_knowledge_section(
    tmp_path: Path,
) -> None:
    insight_path = tmp_path / "variant_insights.yaml"
    insight_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "variant_insights": [
                    {
                        "gene": "TP53",
                        "p_hgvs": "p.R282W",
                        "text": "INSIGHT: hotspot example.",
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    provider = GeneKnowledgeProvider(
        config={
            "enabled": True,
            "variant_insights_db": {
                "enabled": True,
                "path": str(insight_path),
                "format": "yaml",
            },
        }
    )
    provider.load()
    provider._gene_analysis_cache["TP53"] = "BASE ANALYSIS"

    section = provider.build_gene_knowledge_section(
        gene="TP53",
        c_hgvs="c.844C>T",
        p_hgvs="p.R282W",
        frequency=10.0,
        has_drug=False,
    )

    assert section["mutation_analysis"].startswith("INSIGHT: hotspot example.")
    assert "BASE ANALYSIS" in section["mutation_analysis"]


def test_variant_insight_falls_back_to_c_hgvs(tmp_path: Path) -> None:
    insight_path = tmp_path / "variant_insights.yaml"
    insight_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "variant_insights": [
                    {
                        "gene": "APC",
                        "c_hgvs": "c.3927_3931del",
                        "text": "INSIGHT: c.HGVS fallback.",
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    provider = GeneKnowledgeProvider(
        config={
            "enabled": True,
            "variant_insights_db": {
                "enabled": True,
                "path": str(insight_path),
                "format": "yaml",
            },
        }
    )
    provider.load()

    section = provider.build_gene_knowledge_section(
        gene="APC",
        c_hgvs="c.3927_3931del",
        p_hgvs="--",
        frequency=10.0,
        has_drug=False,
    )

    assert "INSIGHT: c.HGVS fallback." in section["mutation_analysis"]
