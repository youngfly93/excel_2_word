from pathlib import Path

import yaml

from reportgen.core.report_generator import ReportGenerator
from reportgen.models.excel_data import ExcelDataSource


def test_generate_reuses_prefetched_excel_data(tmp_path):
    # minimal config for FieldMapper/ExcelReader init
    (tmp_path / "mapping.yaml").write_text(
        yaml.safe_dump(
            {"schema_version": "1.0", "single_values": {}, "table_data": {}},
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    excel_path = tmp_path / "sample.xlsx"
    excel_path.write_bytes(b"x")  # only needs to exist for ExcelDataSource

    excel_data = ExcelDataSource(
        file_path=str(excel_path),
        sheet_names=[],
        single_values={"患者姓名": "张三"},
        table_data={},
        metadata={"sample_id_from_filename": "S001"},
    )

    generator = ReportGenerator(config_dir=str(tmp_path))

    # if called, this would indicate we didn't reuse excel_data
    generator.excel_reader.read = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("excel_reader.read should not be called when excel_data is provided")
    )

    def stub_render(_template_path: str, _report_data, output_path: str) -> str:
        Path(output_path).write_bytes(b"dummy-docx")
        return output_path

    generator.template_renderer.render = stub_render

    out_dir = tmp_path / "out"
    template_path = tmp_path / "template.docx"
    template_path.write_bytes(b"dummy-template")

    result = generator.generate(
        excel_file=str(excel_path),
        template_file=str(template_path),
        output_dir=str(out_dir),
        excel_data=excel_data,
    )

    assert result["success"] is True
    assert result["output_file"]
    assert Path(result["output_file"]).exists()

