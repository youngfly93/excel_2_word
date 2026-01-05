import yaml

from reportgen.core.field_mapper import FieldMapper


def test_validate_table_row_with_reason_frequency_filter_disabled_does_not_crash(tmp_path):
    # minimal mapping config required by FieldMapper
    mapping = {
        "schema_version": "1.0",
        "single_values": {},
        "table_data": {
            "variants": {
                "sheet_name": "Variations",
                "columns": {},
            }
        },
    }
    (tmp_path / "mapping.yaml").write_text(
        yaml.safe_dump(mapping, allow_unicode=True), encoding="utf-8"
    )

    filtering = {
        "variations": {
            "enabled": True,
            "frequency_filter": {
                "enabled": False,
                "min_frequency": 5.0,
                "frequency_columns": ["Freq(%)"],
            },
            "clinical_significance_filter": {
                "enabled": True,
                "significant_keywords": ["Missense"],
                "function_columns": ["Function"],
            },
            "basic_validation": {
                "require_gene": True,
                "gene_columns": ["Gene_Symbol"],
                "require_variant": True,
                "variant_columns": ["cHGVS"],
            },
        }
    }
    (tmp_path / "filtering.yaml").write_text(
        yaml.safe_dump(filtering, allow_unicode=True), encoding="utf-8"
    )

    mapper = FieldMapper(config_dir=str(tmp_path))

    row = {
        "Gene_Symbol": "TP53",
        "cHGVS": "c.1A>T",
        "Freq(%)": "1.0",
        "Function": "Synonymous",
    }

    is_valid, reason = mapper._validate_table_row_with_reason("variants", row)
    assert is_valid is False
    assert reason == "not_significant"


def test_validate_table_row_with_reason_class_filter_ignores_numeric_flag(tmp_path):
    """ExistIn552=0/1（布尔标记）不应触发“分级过滤”拦截。"""
    mapping = {
        "schema_version": "1.0",
        "single_values": {},
        "table_data": {
            "variants": {
                "sheet_name": "Variations",
                "columns": {},
            }
        },
    }
    (tmp_path / "mapping.yaml").write_text(
        yaml.safe_dump(mapping, allow_unicode=True), encoding="utf-8"
    )

    filtering = {
        "variations": {
            "enabled": True,
            "class_filter": {
                "enabled": True,
                "class_columns": ["ExistIn552"],
                "allowed_classes": ["Ⅰ类", "Ⅱ类", "Ⅲ类"],
            },
            "frequency_filter": {
                "enabled": True,
                "min_frequency": 5.0,
                "frequency_columns": ["Freq(%)"],
            },
            "clinical_significance_filter": {
                "enabled": True,
                "significant_keywords": ["Missense"],
                "function_columns": ["Function"],
            },
            "basic_validation": {
                "require_gene": True,
                "gene_columns": ["Gene_Symbol"],
                "require_variant": True,
                "variant_columns": ["cHGVS"],
            },
        }
    }
    (tmp_path / "filtering.yaml").write_text(
        yaml.safe_dump(filtering, allow_unicode=True), encoding="utf-8"
    )

    mapper = FieldMapper(config_dir=str(tmp_path))

    row = {
        "Gene_Symbol": "TP53",
        "cHGVS": "c.1A>T",
        "Freq(%)": "10.0",
        "Function": "Missense",
        "ExistIn552": 1,  # 0/1 标记（非“Ⅰ类/Ⅱ类/Ⅲ类”）
    }

    is_valid, reason = mapper._validate_table_row_with_reason("variants", row)
    assert is_valid is True
    assert reason == ""


def test_validate_table_row_with_reason_class_filter_rejects_unknown_label(tmp_path):
    """ExistIn552 为非允许分级（如“Ⅳ类”）应被分级过滤拒绝。"""
    mapping = {
        "schema_version": "1.0",
        "single_values": {},
        "table_data": {
            "variants": {
                "sheet_name": "Variations",
                "columns": {},
            }
        },
    }
    (tmp_path / "mapping.yaml").write_text(
        yaml.safe_dump(mapping, allow_unicode=True), encoding="utf-8"
    )

    filtering = {
        "variations": {
            "enabled": True,
            "class_filter": {
                "enabled": True,
                "class_columns": ["ExistIn552"],
                "allowed_classes": ["Ⅰ类", "Ⅱ类", "Ⅲ类"],
            },
            "frequency_filter": {
                "enabled": True,
                "min_frequency": 5.0,
                "frequency_columns": ["Freq(%)"],
            },
            "clinical_significance_filter": {
                "enabled": True,
                "significant_keywords": ["Missense"],
                "function_columns": ["Function"],
            },
            "basic_validation": {
                "require_gene": True,
                "gene_columns": ["Gene_Symbol"],
                "require_variant": True,
                "variant_columns": ["cHGVS"],
            },
        }
    }
    (tmp_path / "filtering.yaml").write_text(
        yaml.safe_dump(filtering, allow_unicode=True), encoding="utf-8"
    )

    mapper = FieldMapper(config_dir=str(tmp_path))

    row = {
        "Gene_Symbol": "TP53",
        "cHGVS": "c.1A>T",
        "Freq(%)": "10.0",
        "Function": "Missense",
        "ExistIn552": "Ⅳ类",
    }

    is_valid, reason = mapper._validate_table_row_with_reason("variants", row)
    assert is_valid is False
    assert reason == "class_filtered"
