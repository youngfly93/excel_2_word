from __future__ import annotations

from pathlib import Path

from docx import Document


def test_crc358_v18_template_mutation_site_is_comma_newline_separated() -> None:
    """批注#4：突变位点需为英文逗号 + 换行分隔。"""
    repo_root = Path(__file__).parent.parent.parent
    template_path = repo_root / "templates" / "jinja2_template_358_v18.docx"

    doc = Document(str(template_path))

    cell_texts: list[str] = []
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text:
                    cell_texts.append(cell.text)

    assert "{{ row.cHGVS }},\n{{ row.pHGVS }}" in cell_texts
    assert "{{ row.cHGVS }}\n{{ row.pHGVS }}" in cell_texts
