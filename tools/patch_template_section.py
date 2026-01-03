"""
Patch a specific section in a docx template (built from tempe_test)
to ensure TMB/MSI placeholders and immuno tips are correctly wired.

Usage:
  python3 tools/patch_template_section.py \
      --in templates/aligned_template_from_tempe_test.docx
"""

from __future__ import annotations

from pathlib import Path
import argparse
from docx import Document
from docx.shared import RGBColor
from docx.table import Table
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl


def patch_biomarker_table(doc: Document) -> int:
    """Find the biomarker table (TMB/MSI/用药提示) and inject placeholders.

    Returns number of rows patched.
    """
    patched = 0

    def is_target_table(tbl) -> bool:
        try:
            if not tbl.rows:
                return False
            header = "|".join(c.text for c in tbl.rows[0].cells)
            return ("TMB/MSI" in header) and ("用药提示" in header)
        except Exception:
            return False

    for t in doc.tables:
        if not is_target_table(t):
            continue

        for row in t.rows[1:]:  # skip header
            cells = row.cells
            if not cells:
                continue
            label = (cells[0].text or "").strip().upper()

            # TMB row
            if "TMB" in label:
                if len(cells) > 1:
                    cells[1].text = "{{ tmb_summary }}"
                patched += 1
                continue

            # MSI row
            if "MSI" in label:
                if len(cells) > 1:
                    cells[1].text = "{{ msi_summary }}"
                patched += 1
                continue

            # Immune-related gene lists
            if "免疫正相关基因" in label:
                if len(cells) > 1:
                    cells[1].text = "{{ immuno_positive_genes }}"
                patched += 1
                continue
            if "免疫负相关基因" in label:
                if len(cells) > 1:
                    cells[1].text = "{{ immuno_negative_genes }}"
                patched += 1
                continue
            if "免疫超进展相关基因" in label:
                if len(cells) > 1:
                    cells[1].text = "{{ immuno_hyperprogression_genes }}"
                patched += 1
                continue

        # Only patch the first matched table
        break

    return patched


def patch_targeted_drug_table(doc: Document) -> int:
    """Find the targeted drug tips table and inject placeholders.

    Expected table header includes:
      - 基因
      - 突变位点
      - 潜在获益靶向药物（证据等级）
      - 可能耐药或慎重药物（证据等级）

    The patched loop will iterate `targeted_drug_tips` (4 columns):
      gene / variant_site / benefit_drugs / caution_drugs
    """
    patched = 0

    def is_target_table(tbl) -> bool:
        try:
            if not tbl.rows:
                return False
            header = "|".join(c.text for c in tbl.rows[0].cells)
            return ("潜在获益靶向药物" in header) and ("可能耐药" in header) and ("突变位点" in header)
        except Exception:
            return False

    for tbl in doc.tables:
        if not is_target_table(tbl):
            continue

        # keep only the header row
        while len(tbl.rows) > 1:
            tbl._tbl.remove(tbl._tbl.tr_lst[1])

        # inject docxtpl loop rows
        s = tbl.add_row().cells
        s[0].text = "{% for row in targeted_drug_tips %}"
        d = tbl.add_row().cells
        d[0].text = "{{ row.gene }}"
        d[1].text = "{{ row.variant_site }}"
        d[2].text = "{{ row.benefit_drugs }}"
        d[3].text = "{{ row.caution_drugs }}"

        def style_blue_underline(cell):
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.underline = True
                    run.font.color.rgb = RGBColor(0x05, 0x63, 0xC1)  # hyperlink-like blue

        style_blue_underline(d[0])
        style_blue_underline(d[2])

        e = tbl.add_row().cells
        e[0].text = "{% endfor %}"

        patched = 1
        break

    return patched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="input", required=True, help="Input docx path")
    ap.add_argument("--out", dest="output", default=None, help="Output docx path (optional, overwrite if omitted)")
    ap.add_argument("--patch-variants", action="store_true", help="Patch 2.1 variants 9-column loop")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        raise SystemExit(f"Input not found: {src}")

    out = Path(args.output) if args.output else src
    if args.output:
        out.parent.mkdir(parents=True, exist_ok=True)

    doc = Document(str(src))
    n1 = patch_biomarker_table(doc)
    n_drug = patch_targeted_drug_table(doc)

    if args.patch_variants:
        n2 = patch_variants_2_1(doc)
    else:
        n2 = 0

    doc.save(str(out))
    print(
        f"Patched biomarker rows: {n1}; targeted_drug_table: {n_drug}; variants rows: {n2}; written: {out}"
    )


def _next_table_after_paragraph(doc: Document, paragraph_index: int) -> Table | None:
    blocks = []
    for child in doc._element.body.iterchildren():
        if isinstance(child, CT_P):
            blocks.append(("p", child))
        elif isinstance(child, CT_Tbl):
            blocks.append(("tbl", child))
    p_el = doc.paragraphs[paragraph_index]._element
    bidx = next((i for i, (t, el) in enumerate(blocks) if t == "p" and el == p_el), None)
    if bidx is None:
        return None
    for t, el in blocks[bidx + 1 :]:
        if t == "tbl":
            return Table(el, doc)
    return None


def patch_variants_2_1(doc: Document) -> int:
    """Locate the 2.1 section and inject a docxtpl loop row with 9 cells.

    We keep the first two header rows and replace data rows with a
    three-row loop: start, data, end.
    """
    # 1) find heading paragraph containing the section title
    title = "2.1 基因变异检测结果及相关靶向药物信息"
    try:
        pidx = next(i for i, p in enumerate(doc.paragraphs) if title in (p.text or ""))
    except StopIteration:
        return 0

    tbl = _next_table_after_paragraph(doc, pidx)
    if not tbl:
        return 0

    # 2) 识别应保留的表头行数：
    #    终版有两行表头（分组表头 + 列名表头）。部分旧模板只有分组表头，
    #    这里会自动补齐列名表头。
    keep_rows = 1
    if len(tbl.rows) > 1:
        txt_row1 = "|".join(c.text for c in tbl.rows[1].cells)
        if "转录本号" in txt_row1 and "位点" in txt_row1:
            keep_rows = 2

    while len(tbl.rows) > keep_rows:
        tbl._tbl.remove(tbl._tbl.tr_lst[keep_rows])

    # 若缺少列名表头，则补齐一行
    if keep_rows == 1:
        hdr = tbl.add_row().cells
        hdr[0].text = "基因名称"
        hdr[1].text = "转录本号"
        hdr[2].text = "染色体"
        hdr[3].text = "外显子"
        hdr[4].text = "位点"
        hdr[5].text = "突变 类型"
        hdr[6].text = "频率 (%)"
        hdr[7].text = "潜在获益靶向药物 （证据等级）"
        hdr[8].text = "可能耐药或 慎重药物 （证据等级）"

    # 3) create 3-row loop (start, data, end) — canonical docxtpl row loop
    s = tbl.add_row().cells
    s[0].text = "{% for row in variants_2_1 %}"
    d = tbl.add_row().cells
    d[0].text = "{{ row.gene }}"
    d[1].text = "{{ row.transcript }}"
    d[2].text = "{{ row.chr }}"
    d[3].text = "{{ row.exon }}"
    d[4].text = "{{ row.locus }}"
    d[5].text = "{{ row.var_type_cn }}"
    d[6].text = "{{ row.af_pct }}"
    d[7].text = "{{ row.benefit_drugs }}"
    d[8].text = "{{ row.caution_drugs }}"
    # Apply blue+underline style to gene and benefit_drugs cells to mimic final template
    def style_blue_underline(cell):
        for p in cell.paragraphs:
            for run in p.runs:
                run.font.underline = True
                run.font.color.rgb = RGBColor(0x05, 0x63, 0xC1)  # hyperlink-like blue
    style_blue_underline(d[0])
    style_blue_underline(d[7])
    e = tbl.add_row().cells
    e[0].text = "{% endfor %}"

    return 3


if __name__ == "__main__":
    main()
