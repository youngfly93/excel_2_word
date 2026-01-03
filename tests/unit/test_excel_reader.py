import pandas as pd
import yaml

from reportgen.core.excel_reader import ExcelReader


def test_read_without_tables_skips_table_data(tmp_path):
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

    excel_path = tmp_path / "sample.xlsx"
    main_df = pd.DataFrame([{"患者姓名": "张三", "样本编号": "S001"}])
    var_df = pd.DataFrame(
        [
            {"Gene_Symbol": "TP53", "cHGVS": "c.1A>T"},
            {"Gene_Symbol": "KRAS", "cHGVS": "c.2G>A"},
        ]
    )
    other_df = pd.DataFrame([{"x": 1}, {"x": 2}])

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        main_df.to_excel(writer, index=False, sheet_name="Sheet1")
        var_df.to_excel(writer, index=False, sheet_name="Variations")
        other_df.to_excel(writer, index=False, sheet_name="Other")

    reader = ExcelReader(config_dir=str(tmp_path))
    data = reader.read(str(excel_path), include_tables=False)

    assert data.single_values.get("患者姓名") == "张三"
    assert data.table_data == {}


def test_read_tables_only_reads_mapping_sheets(tmp_path):
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

    excel_path = tmp_path / "sample.xlsx"
    main_df = pd.DataFrame([{"患者姓名": "张三", "样本编号": "S001"}])
    var_df = pd.DataFrame(
        [
            {"Gene_Symbol": "TP53", "cHGVS": "c.1A>T"},
            {"Gene_Symbol": "KRAS", "cHGVS": "c.2G>A"},
        ]
    )
    other_df = pd.DataFrame([{"x": 1}, {"x": 2}])

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        main_df.to_excel(writer, index=False, sheet_name="Sheet1")
        var_df.to_excel(writer, index=False, sheet_name="Variations")
        other_df.to_excel(writer, index=False, sheet_name="Other")

    reader = ExcelReader(config_dir=str(tmp_path))
    data = reader.read(str(excel_path), include_tables=True)

    assert "Variations" in data.table_data
    assert "Other" not in data.table_data

