"""
Convert a filled final report (.docx) into a docxtpl-ready template by keeping
all static structure (sections, headers/footers, ToC, table headers) identical
to the baseline and inserting Jinja placeholders only in variable regions.

Usage:
  python3 tools/make_template_from_baseline.py \
      --baseline "杨庆铁-盲肠癌-结直肠癌358基因+msi-mljy-lz250929-终版.docx" \
      --out templates/aligned_template_final.docx

Notes:
  - This script makes best-effort heuristic replacements for common fields
    (patient info, TMB/MSI) and converts recognized data tables (variants,
    chemotherapy) into docxtpl row loops.
  - It preserves multi-section structure, headers/footers, and table headers by
    editing the baseline document in-place and saving as a new file.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import List

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def normalize_label(text: str) -> str:
    if text is None:
        return ""
    s = re.sub(r"\s+", "", text)
    s = s.replace(":", "").replace("：", "")
    return s


def delete_row(table, row_idx: int):
    tr = table.rows[row_idx]._tr
    tbl = tr.getparent()
    tbl.remove(tr)


def table_header_cells(table) -> List[str]:
    if not table.rows:
        return []
    return [cell.text.strip() for cell in table.rows[0].cells]


def contains_any(texts: List[str], keywords: List[str]) -> bool:
    s = "|".join(texts)
    return any(k in s for k in keywords)


def replace_patient_info_placeholders(table):
    # Map label keywords to placeholders
    mapping = {
        "姓名": "{{ patient_name }}",
        "姓    名": "{{ patient_name }}",
        "报告编号": "{{ sample_id }}",
        "样本编号": "{{ sample_id }}",
        "样本类型": "{{ sample_type }}",
        "病理号": "{{ pathology_id }}",
        "病理编号": "{{ pathology_id }}",
        "送检日期": "{{ collection_date }}",
        "接收日期": "{{ receive_date }}",
        "报告日期": "{{ report_date }}",
        "送检医院": "{{ hospital }}",
        "科室": "{{ department }}",
        "性别": "{{ gender }}",
        "年龄": "{{ age }}",
    }

    for row in table.rows:
        cells = row.cells
        for j, cell in enumerate(cells):
            label_raw = cell.text.strip()
            label_key = normalize_label(label_raw)
            # match against mapping keys after normalize
            for k, ph in mapping.items():
                if normalize_label(k) and normalize_label(k) in label_key:
                    # put placeholder into the next cell if possible
                    if j + 1 < len(cells):
                        cells[j + 1].text = ph
                    else:
                        cell.text = f"{label_raw} {ph}"
                    break


def replace_patient_info_in_paragraphs(doc: Document):
    # Replace values in plain paragraphs like "姓    名：   xxx" → "姓    名：   {{ patient_name }}"
    mapping = {
        "姓名": "{{ patient_name }}",
        "姓    名": "{{ patient_name }}",
        "报告编号": "{{ sample_id }}",
        "样本编号": "{{ sample_id }}",
        "送检日期": "{{ collection_date }}",
        "接收日期": "{{ receive_date }}",
        "报告日期": "{{ report_date }}",
        "样本类型": "{{ sample_type }}",
    }

    def clear_runs(p):
        # remove existing runs to rebuild with formatting
        for r in list(p.runs):
            p._element.remove(r._element)

    def set_bottom_border(p):
        # add bottom border to paragraph (visual underline across the line)
        pPr = p._element.get_or_add_pPr()
        pBdr = OxmlElement('w:pBdr')
        bottom = OxmlElement('w:bottom')
        bottom.set(qn('w:val'), 'single')
        bottom.set(qn('w:sz'), '6')  # line weight
        bottom.set(qn('w:space'), '1')
        bottom.set(qn('w:color'), 'auto')
        pBdr.append(bottom)
        # remove existing borders if any then set
        for child in list(pPr):
            if child.tag == qn('w:pBdr'):
                pPr.remove(child)
        pPr.append(pBdr)

    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        norm = normalize_label(text)
        for k, ph in mapping.items():
            if normalize_label(k) in norm and ("：" in text or ":" in text):
                # split at the last colon-like char to preserve prefix spacing
                if "：" in text:
                    sep = "："
                else:
                    sep = ":"
                parts = text.split(sep, 1)
                if len(parts) == 2:
                    prefix, _ = parts
                    clear_runs(p)
                    # label (bold)
                    r1 = p.add_run(f"{prefix}{sep}  ")
                    r1.bold = True
                    # value (underlined) – only underline the placeholder text
                    r2 = p.add_run(ph)
                    r2.underline = True
                    # add a paragraph bottom border to mimic full-line underline
                    set_bottom_border(p)
                break


def convert_to_loop(table, loop_name: str, header_to_expr: dict):
    # Keep header row; remove all other rows
    while len(table.rows) > 1:
        delete_row(table, 1)

    # Build normalized key map for robust header matching
    norm_map = {normalize_label(k): v for k, v in (header_to_expr or {}).items()}

    # Create the data row that will be repeated. Put the start tag in first cell.
    data = table.add_row().cells
    headers = table_header_cells(table)

    for idx, h in enumerate(headers):
        expr = ""
        # 1) exact normalized match from provided map
        nm = normalize_label(h)
        if nm in norm_map:
            expr = norm_map[nm]
        # 2) heuristics
        if not expr:
            hn = nm
            if any(k in hn for k in ["gene", "基因"]):
                expr = "{{ row.gene or row.Gene or row.Gene_Symbol or row.基因 }}"
            elif any(k in hn for k in ["chgvs", "突变", "位点", "variant"]):
                expr = "{{ row.variant_site or row.cHGVS or row.变异位点 or row.突变位点 }}"
            elif any(k in hn for k in ["蛋白", "phgvs", "aa"]):
                expr = "{{ row.pHGVS or row.pHGVS_S or row.pHGVS_A }}"
            elif any(k in hn for k in ["频率", "freq", "%"]):
                expr = "{{ row.af or row['Freq(%)'] }}"
            elif any(k in hn for k in ["外显子", "exon", "exin"]):
                expr = "{{ row.exon or row.ExIn_ID }}"
            elif any(k in hn for k in ["获益", "靶向药物", "benefit"]):
                expr = "{{ row.benefit_drugs }}"
            elif any(k in hn for k in ["耐药", "慎重", "caution"]):
                expr = "{{ row.caution_drugs }}"
            elif any(k in hn for k in ["药物", "drug"]):
                expr = "{{ row.Drug or row.drug_name or row.药物 }}"
            elif any(k in hn for k in ["证据", "evidence"]):
                expr = "{{ row.Evidence_level or row.evidence_level }}"

        data[idx].text = expr

    # Prepend loop start tag to first cell so this row repeats
    data[0].text = f"{{% for row in {loop_name} %}}" + (data[0].text or "")

    # Add end tag row
    end = table.add_row().cells
    end[0].text = "{% endfor %}"


def is_variants_table(headers: List[str]) -> bool:
    joined = "|".join(headers)
    return ("基因" in joined or "Gene" in joined) and (
        "突变" in joined or "cHGVS" in joined or "位点" in joined
    )


def is_chemotherapy_table(headers: List[str]) -> bool:
    joined = "|".join(headers)
    return ("药物名称" in joined or "药物" in joined) and ("基因" in joined or "Gene" in joined)


def is_biomarker_table(headers: List[str]) -> bool:
    joined = "|".join(headers)
    return "TMB" in joined or "MSI" in joined or "生物标志物" in joined


def is_gene_interpretation_table(headers: List[str]) -> bool:
    # e.g. 基因 | 检测结果 | 临床解读
    needed = ["基因", "检测结果", "临床解读"]
    return all(any(k in h for h in headers) for k in needed)


def is_targeted_drug_tip_table(headers: List[str]) -> bool:
    # e.g. 基因 | 突变位点 | 潜在获益靶向药物（证据等级） | 可能耐药或慎重药物（证据等级）
    joined = "|".join(headers)
    return ("基因" in joined) and ("突变位点" in joined or "突变" in joined or "位点" in joined) and (
        "潜在获益" in joined or "靶向药物" in joined
    ) and ("耐药" in joined or "慎重" in joined)


def is_tested_genes_summary_table(headers: List[str]) -> bool:
    # e.g. 检测基因 | 检测内容 | 检测结果
    needed = ["检测基因", "检测内容", "检测结果"]
    return all(any(k in h for h in headers) for k in needed)


def is_hereditary_variants_table(headers: List[str]) -> bool:
    joined = "|".join(headers)
    return ("CLNSIG" in joined or "CLNDBN" in joined) and ("Gene" in joined or "基因" in joined)


def is_hotspot_table(headers: List[str]) -> bool:
    joined = "|".join(headers)
    return ("#Chr" in joined or "Chr" in joined or "chr" in joined) and (
        "Cancer_Ori_AA_Dep" in joined or "Normal_Ori_AA_Dep" in joined
    )


def is_fusions_table(headers: List[str]) -> bool:
    joined = "|".join(headers)
    return ("gene1" in joined or "基因1" in joined) and ("gene2" in joined or "基因2" in joined)


def is_cnvs_table(headers: List[str]) -> bool:
    joined = "|".join(headers)
    return ("Gene" in joined or "基因" in joined) and ("AvgCP" in joined or "Cnvkit" in joined or "拷贝" in joined)


def is_hla_table(headers: List[str]) -> bool:
    joined = "|".join(headers)
    return "HLA-A" in joined and "HET" in joined


def fill_biomarker_placeholders(table):
    # Try to locate TMB/MSI rows: first column labels
    for row in table.rows[1:]:
        label = row.cells[0].text.strip()
        if "TMB" in label.upper():
            if len(row.cells) > 1:
                # 统一变量名：tmb_value/tmb_unit
                row.cells[1].text = "{{ tmb_value }} {{ tmb_unit }}"
        if "MSI" in label.upper():
            if len(row.cells) > 1:
                # 统一变量名：msi_status
                row.cells[1].text = "{{ msi_status }}"


def process_document(baseline: Path, out_path: Path):
    doc = Document(str(baseline))

    # First, replace patient info in plain paragraphs on the cover/early pages
    replace_patient_info_in_paragraphs(doc)

    for t in doc.tables:
        headers = table_header_cells(t)
        hn = [normalize_label(h) for h in headers]

        # Patient info tables: look for presence of any labels
        if contains_any(hn, ["姓名", "报告编号", "样本编号", "送检日期", "报告日期", "送检医院", "科室", "性别", "年龄", "样本类型", "病理号", "病理编号"]):
            replace_patient_info_placeholders(t)
            continue

        # Biomarker TMB/MSI table
        if is_biomarker_table(headers):
            fill_biomarker_placeholders(t)
            continue

        # Gene interpretation 3-col table
        if is_gene_interpretation_table(headers):
            convert_to_loop(
                t,
                loop_name="gene_interpretations",
                header_to_expr={
                    "基因": "{{ row.gene or row.Gene or row.基因 }}",
                    "检测结果": "{{ row.result or row.检测结果 or '' }}",
                    "临床解读": "{{ row.interpretation or row.临床解读 or '' }}",
                },
            )
            continue

        # Targeted drug tips table
        if is_targeted_drug_tip_table(headers):
            convert_to_loop(
                t,
                loop_name="targeted_drug_tips",
                header_to_expr={
                    "基因": "{{ row.gene or row.Gene or row.基因 }}",
                    "突变位点": "{{ row.variant_site or row.cHGVS or row.突变位点 or '' }}",
                    "潜在获益靶向药物 （证据等级)": "{{ row.benefit_drugs or row.潜在获益药物 or '' }}",
                    "潜在获益靶向药物 （证据等级）": "{{ row.benefit_drugs or row.潜在获益药物 or '' }}",
                    "可能耐药或慎重药物 （证据等级)": "{{ row.caution_drugs or row.耐药药物 or '' }}",
                    "可能耐药或慎重药物 （证据等级）": "{{ row.caution_drugs or row.耐药药物 or '' }}",
                },
            )
            continue

        # Tested genes summary
        if is_tested_genes_summary_table(headers):
            convert_to_loop(
                t,
                loop_name="tested_genes",
                header_to_expr={
                    "检测基因": "{{ row.gene or row.Gene or row.检测基因 }}",
                    "检测内容": "{{ row.content or row.检测内容 or '' }}",
                    "检测结果": "{{ row.result or row.检测结果 or '' }}",
                },
            )
            continue

        # Hereditary tumor variants
        if is_hereditary_variants_table(headers):
            convert_to_loop(
                t,
                loop_name="hereditary_variants",
                header_to_expr={
                    "基因": "{{ row.gene or row.Gene_Symbol }}",
                    "Gene": "{{ row.gene or row.Gene_Symbol }}",
                    "cHGVS": "{{ row.cHGVS }}",
                    "蛋白改变": "{{ row.pHGVS or row.pHGVS_S or row.pHGVS_A }}",
                    "Function": "{{ row.function }}",
                    "Freq(%)": "{{ row.af }}",
                    "外显子": "{{ row.exon }}",
                    "ExIn_ID": "{{ row.exon }}",
                    "CLNSIG": "{{ row.clnsig }}",
                    "CLNDBN": "{{ row.clndbn }}",
                    "SpliceAI": "{{ row.spliceai }}",
                },
            )
            continue

        # Hotspot
        if is_hotspot_table(headers):
            convert_to_loop(
                t,
                loop_name="hotspot",
                header_to_expr={
                    "#Chr": "{{ row.chromosome }}",
                    "Chr": "{{ row.chromosome }}",
                    "Start": "{{ row.start }}",
                    "End": "{{ row.end }}",
                    "Gene": "{{ row.gene }}",
                    "Cancer_Ori_AA_Dep": "{{ row.cancer_ori_aa_dep }}",
                    "Normal_Ori_AA_Dep": "{{ row.normal_ori_aa_dep }}",
                    "Cancer_Hot_Var_AA_Info": "{{ row.cancer_hot_var_aa_info }}",
                    "Normal_Hot_Var_AA_Info": "{{ row.normal_hot_var_aa_info }}",
                },
            )
            continue

        # Fusions
        if is_fusions_table(headers):
            convert_to_loop(
                t,
                loop_name="fusions",
                header_to_expr={
                    "gene1": "{{ row.gene1 }}",
                    "gene2": "{{ row.gene2 }}",
                    "chr1": "{{ row.chr1 }}",
                    "chr2": "{{ row.chr2 }}",
                    "pos1": "{{ row.pos1 }}",
                    "pos2": "{{ row.pos2 }}",
                    "annotation1": "{{ row.annotation1 }}",
                    "annotation2": "{{ row.annotation2 }}",
                    "support_reads1": "{{ row.support_reads1 }}",
                    "support_reads2": "{{ row.support_reads2 }}",
                    "depth1": "{{ row.depth1 }}",
                    "depth2": "{{ row.depth2 }}",
                    "paired_depth": "{{ row.paired_depth }}",
                },
            )
            continue

        # CNVs
        if is_cnvs_table(headers):
            convert_to_loop(
                t,
                loop_name="cnvs",
                header_to_expr={
                    "Gene": "{{ row.gene }}",
                    "基因": "{{ row.gene }}",
                    "AvgCP": "{{ row.copy_number }}",
                    "Cnvkit": "{{ row.cnv_type }}",
                    "类型": "{{ row.cnv_type }}",
                    "拷贝数": "{{ row.copy_number }}",
                },
            )
            continue

        # HLA typing
        if is_hla_table(headers):
            convert_to_loop(
                t,
                loop_name="hla_typing",
                header_to_expr={
                    "HLA-A": "{{ row.locus }}",
                    "HET": "{{ row.het }}",
                    "分型": "{{ row.value }}",
                    "Type": "{{ row.value }}",
                },
            )
            continue

        # Variants detail table → loop
        if is_variants_table(headers):
            convert_to_loop(
                t,
                loop_name="variants",
                header_to_expr={},
            )
            continue

        # Chemotherapy table → loop
        if is_chemotherapy_table(headers):
            convert_to_loop(
                t,
                loop_name="chemotherapy",
                header_to_expr={
                    "药物名称": "{{ row.药物 or row.Drug or '' }}",
                    "相关基因": "{{ row.检测基因 or row.Gene or '' }}",
                    "药物适应情况": "{{ row.药物适应情况 or row.检测结果 or '' }}",
                },
            )
            continue

    # Save as new template
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True, help="Path to baseline final docx")
    ap.add_argument("--out", required=True, help="Output template path (.docx)")
    args = ap.parse_args()

    baseline = Path(args.baseline)
    out_path = Path(args.out)

    process_document(baseline, out_path)
    print(f"Template written: {out_path}")


if __name__ == "__main__":
    main()
