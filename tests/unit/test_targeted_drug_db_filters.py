import pandas as pd
import yaml

from reportgen.core.field_mapper import FieldMapper


def _make_mapper(tmp_path, settings: dict) -> FieldMapper:
    mapping = {
        "schema_version": "1.0",
        "single_values": {},
        "table_data": {},
    }
    (tmp_path / "mapping.yaml").write_text(
        yaml.safe_dump(mapping, allow_unicode=True), encoding="utf-8"
    )
    (tmp_path / "settings.yaml").write_text(
        yaml.safe_dump(settings, allow_unicode=True), encoding="utf-8"
    )
    return FieldMapper(config_dir=str(tmp_path))


def _attach_db(mapper: FieldMapper, df: pd.DataFrame) -> None:
    mapper._targeted_drug_db_loaded = True
    mapper._targeted_drug_db = df
    mapper._targeted_drug_db_cols = {
        "gene": "基因名称",
        "level": "变异等级",
        "c": "c_point",
        "p": "p_point",
        "benefit": "潜在获益靶向药物（证据等级）",
        "caution": "可能耐药或慎重药物（证据等级）",
    }


def test_targeted_db_filters_require_position_match_filters_public_gene_level_rows(tmp_path):
    settings = {
        "knowledge_bases": {
            "targeted_drug_db": {
                "enabled": True,
                "filters": {
                    "enabled": True,
                    "apply_to_sources": ["CGI"],
                    "require_position_match": True,
                    "evidence": {"enabled": False},
                    "cancer_type": {"enabled": False},
                },
            }
        }
    }
    mapper = _make_mapper(tmp_path, settings)

    df = pd.DataFrame(
        [
            {
                "基因名称": "BRAF",
                "变异等级": "",
                "c_point": "",
                "p_point": "",
                "潜在获益靶向药物（证据等级）": "DrugGeneLevel",
                "可能耐药或慎重药物（证据等级）": "--",
                "source_db": "CGI",
            },
            {
                "基因名称": "BRAF",
                "变异等级": "",
                "c_point": "",
                "p_point": "p.V600E",
                "潜在获益靶向药物（证据等级）": "DrugV600E",
                "可能耐药或慎重药物（证据等级）": "--",
                "source_db": "CGI",
            },
        ]
    )
    _attach_db(mapper, df)

    benefit, caution, score = mapper._lookup_targeted_drugs_for_variant(
        "BRAF",
        c_point="c.1799T>A",
        p_point="p.V600E",
        variant_level="Ⅱ类",
        cancer_type="结直肠癌",
    )
    assert "DrugV600E" in benefit
    assert caution == "--"
    assert score > 0


def test_targeted_db_filters_cancer_type_filters_cgi_primary_tumor_type(tmp_path):
    settings = {
        "knowledge_bases": {
            "targeted_drug_db": {
                "enabled": True,
                "filters": {
                    "enabled": True,
                    "apply_to_sources": ["CGI"],
                    "require_position_match": True,
                    "cancer_type": {
                        "enabled": True,
                        "crc_keywords": ["结直肠"],
                        "cgi_allowed_primary_tumor_types": ["COREAD"],
                    },
                    "evidence": {"enabled": False},
                },
            }
        }
    }
    mapper = _make_mapper(tmp_path, settings)

    df = pd.DataFrame(
        [
            {
                "基因名称": "BRAF",
                "变异等级": "",
                "c_point": "",
                "p_point": "p.V600E",
                "潜在获益靶向药物（证据等级）": "DrugWrongCancer",
                "可能耐药或慎重药物（证据等级）": "--",
                "source_db": "CGI",
                "cgi_primary_tumor_type": "NSCLC",
            }
        ]
    )
    _attach_db(mapper, df)

    benefit, caution, score = mapper._lookup_targeted_drugs_for_variant(
        "BRAF",
        c_point="c.1799T>A",
        p_point="p.V600E",
        variant_level="Ⅱ类",
        cancer_type="结直肠癌",
    )
    assert benefit == "--"
    assert caution == "--"
    assert score == 0.0


def test_targeted_db_filters_evidence_filters_low_rank_cgi_rows(tmp_path):
    settings = {
        "knowledge_bases": {
            "targeted_drug_db": {
                "enabled": True,
                "filters": {
                    "enabled": True,
                    "apply_to_sources": ["CGI"],
                    "require_position_match": True,
                    "cancer_type": {"enabled": False},
                    "evidence": {"enabled": True, "cgi_min_rank": 4},
                },
            }
        }
    }
    mapper = _make_mapper(tmp_path, settings)

    df = pd.DataFrame(
        [
            {
                "基因名称": "BRAF",
                "变异等级": "",
                "c_point": "",
                "p_point": "p.V600E",
                "潜在获益靶向药物（证据等级）": "DrugCaseReport",
                "可能耐药或慎重药物（证据等级）": "--",
                "source_db": "CGI",
                "cgi_evidence_level": "Case report",
            }
        ]
    )
    _attach_db(mapper, df)

    benefit, caution, score = mapper._lookup_targeted_drugs_for_variant(
        "BRAF",
        c_point="c.1799T>A",
        p_point="p.V600E",
        variant_level="Ⅱ类",
        cancer_type="结直肠癌",
    )
    assert benefit == "--"
    assert caution == "--"
    assert score == 0.0


def test_targeted_db_filters_do_not_apply_to_internal_by_default(tmp_path):
    settings = {
        "knowledge_bases": {
            "targeted_drug_db": {
                "enabled": True,
                "filters": {
                    "enabled": True,
                    "apply_to_sources": ["CGI"],
                    "require_position_match": True,
                    "evidence": {"enabled": True, "cgi_min_rank": 5},
                    "cancer_type": {"enabled": True, "if_missing_patient_cancer": "reject"},
                },
            }
        }
    }
    mapper = _make_mapper(tmp_path, settings)

    df = pd.DataFrame(
        [
            {
                "基因名称": "TP53",
                "变异等级": "",
                "c_point": "",
                "p_point": "",
                "潜在获益靶向药物（证据等级）": "DrugInternalGeneLevel",
                "可能耐药或慎重药物（证据等级）": "--",
                "source_db": "internal",
            }
        ]
    )
    _attach_db(mapper, df)

    benefit, caution, score = mapper._lookup_targeted_drugs_for_variant(
        "TP53",
        c_point="c.215C>G",
        p_point="p.P72R",
        variant_level="Ⅱ类",
        cancer_type="-",
    )
    assert "DrugInternalGeneLevel" in benefit
    assert caution == "--"
    assert score > 0

