#!/usr/bin/env python3
"""
Test the Jinja2 template with real Excel data.

This script reads variant data from the Excel result file and
renders the template to verify the loops work correctly.

Python 3.9 compatible.
"""

import pandas as pd
from docxtpl import DocxTemplate
import os


def parse_excel_data(excel_path: str) -> dict:
    """Parse Excel file and return context dict for template."""

    print(f"  Reading: {excel_path}")

    # Read Variations sheet
    df = pd.read_excel(excel_path, sheet_name='Variations')
    print(f"  Found {len(df)} variants")

    # Filter for 358 panel genes
    df_358 = df[df['ExistInsmall358'] == 1].copy()
    print(f"  After filtering for 358 panel: {len(df_358)} variants")

    # Map columns to template format
    variants = []
    summary_variants = []

    for _, row in df_358.iterrows():
        gene = row.get('Gene_Symbol', '')
        if pd.isna(gene) or not gene:
            continue

        # Map mutation type
        function = str(row.get('Function', ''))
        if 'Missense' in function:
            mutation_type = '错义突变'
        elif 'Nonsense' in function:
            mutation_type = '无义突变'
        elif 'Frameshift' in function:
            mutation_type = '移码突变'
        elif 'Splice' in function:
            mutation_type = '剪接突变'
        else:
            mutation_type = function or '点突变'

        # Get exon from ExIn_ID (e.g., "EX16" -> "16")
        exin_id = str(row.get('ExIn_ID', ''))
        exon = exin_id.replace('EX', '').replace('IN', '') if exin_id else ''

        # Get chromosome (remove 'chr' prefix)
        chr_val = str(row.get('Chr', ''))
        chromosome = chr_val.replace('chr', '') if chr_val else ''

        # Get frequency
        freq = row.get('Freq(%)', 0)
        if pd.notna(freq):
            try:
                frequency = f"{float(freq):.2f}"
            except (ValueError, TypeError):
                frequency = '--'
        else:
            frequency = '--'

        # Get pHGVS (prefer short form)
        phgvs = row.get('pHGVS_S', '')
        if pd.isna(phgvs) or not phgvs:
            phgvs = row.get('pHGVS_A', '')
        if pd.isna(phgvs):
            phgvs = '--'

        # Get cHGVS
        chgvs = row.get('cHGVS', '')
        if pd.isna(chgvs):
            chgvs = '--'

        # Determine gene class (simplified - in production, use database)
        # Class I: KRAS, NRAS, BRAF, PIK3CA, ERBB2
        # Class II: APC, TP53, SMAD4, etc.
        # Class III: Other genes
        if gene in ['KRAS', 'NRAS', 'BRAF', 'PIK3CA', 'ERBB2', 'MLH1', 'MSH2', 'MSH6', 'PMS2']:
            gene_class = 'Ⅰ类'
        elif gene in ['APC', 'TP53', 'SMAD4']:
            gene_class = 'Ⅱ类'
        else:
            gene_class = 'Ⅲ类'

        # Get drug info
        drug = row.get('Drug', '')
        benefit_drugs = str(drug) if pd.notna(drug) and drug != '*' else '--'
        caution_drugs = '--'  # Would need separate logic

        # Get clinical significance
        clnsig = row.get('CLNSIG', '')
        if pd.notna(clnsig) and clnsig != '*':
            clinical_significance = str(clnsig)
        else:
            clinical_significance = '致病'

        variant = {
            'gene': gene,
            'transcript': str(row.get('Transcript', '')),
            'chromosome': chromosome,
            'exon': exon,
            'cHGVS': str(chgvs),
            'pHGVS': str(phgvs),
            'mutation_type': mutation_type,
            'frequency': frequency,
            'gene_class': gene_class,
            'clinical_significance': clinical_significance,
            'benefit_drugs': benefit_drugs,
            'caution_drugs': caution_drugs,
        }

        variants.append(variant)

        # Summary variant (same data, simplified)
        summary_variant = {
            'gene': gene,
            'transcript': str(row.get('Transcript', '')),
            'chromosome': chromosome,
            'exon': exon,
            'cHGVS': str(chgvs),
            'pHGVS': str(phgvs),
            'mutation_type': '点突变',  # Simplified for summary
            'frequency': frequency,
            'benefit_drugs': benefit_drugs,
            'caution_drugs': caution_drugs,
        }
        summary_variants.append(summary_variant)

    # Get detected gene names
    detected_genes = set(v['gene'] for v in variants)

    # Create undetected genes list (simplified - would come from panel definition)
    all_panel_genes = [
        {'name': 'BRAF', 'transcript': 'NM_004333.4', 'chromosome': '7'},
        {'name': 'ERBB2', 'transcript': 'NM_004448.4', 'chromosome': '17'},
        {'name': 'NRAS', 'transcript': 'NM_002524.5', 'chromosome': '1'},
        {'name': 'PIK3CA', 'transcript': 'NM_006218.4', 'chromosome': '3'},
        {'name': 'SMAD4', 'transcript': 'NM_005359.6', 'chromosome': '18'},
        {'name': 'MLH1', 'transcript': 'NM_000249.4', 'chromosome': '3'},
        {'name': 'MSH2', 'transcript': 'NM_000251.3', 'chromosome': '2'},
        {'name': 'MSH6', 'transcript': 'NM_000179.3', 'chromosome': '2'},
        {'name': 'PMS2', 'transcript': 'NM_000535.7', 'chromosome': '7'},
        {'name': 'PTEN', 'transcript': 'NM_000314.8', 'chromosome': '10'},
        {'name': 'AKT1', 'transcript': 'NM_001014431.2', 'chromosome': '14'},
        {'name': 'EGFR', 'transcript': 'NM_005228.5', 'chromosome': '7'},
        {'name': 'MET', 'transcript': 'NM_000245.4', 'chromosome': '7'},
        {'name': 'RET', 'transcript': 'NM_020975.6', 'chromosome': '10'},
        {'name': 'ROS1', 'transcript': 'NM_002944.2', 'chromosome': '6'},
    ]

    undetected_genes = [g for g in all_panel_genes if g['name'] not in detected_genes]

    return {
        'variants': variants,
        'summary_variants': summary_variants,
        'undetected_genes': undetected_genes,
    }


def test_template_with_excel():
    """Test the template with real Excel data."""

    # Paths
    template_path = "/Volumes/KINGSTON/work/minhao/肠癌358基因/templates/jinja2_template_358_v5.docx"
    excel_path = "/Volumes/KINGSTON/work/minhao/肠癌358基因/data/input/MLF2509307001T_MLB2509307001.result.xlsx"
    output_path = "/Volumes/KINGSTON/work/minhao/肠癌358基因/templates/test_output_excel.docx"

    print("=" * 60)
    print("Testing Template with Real Excel Data")
    print("=" * 60)

    # Check if files exist
    if not os.path.exists(template_path):
        print(f"  ERROR: Template not found: {template_path}")
        return False

    if not os.path.exists(excel_path):
        print(f"  ERROR: Excel file not found: {excel_path}")
        return False

    # Load template
    print("\n[1/4] Loading template...")
    doc = DocxTemplate(template_path)
    print(f"  Template loaded: {template_path}")

    # Parse Excel data
    print("\n[2/4] Parsing Excel data...")
    data = parse_excel_data(excel_path)

    # Prepare context
    print("\n[3/4] Preparing template context...")

    context = {
        # Patient info (placeholder - would come from report metadata)
        "patient_name": "测试患者",
        "gender": "男",
        "age": "55",
        "sample_id": "MLF2509307001T",
        "pathological_diagnosis": "结直肠癌",
        "specimen_type": "组织",
        "report_date": "2025-01-15",
        "received_date": "2025-01-10",

        # Variant data from Excel
        "variants": data['variants'],
        "summary_variants": data['summary_variants'],
        "undetected_genes": data['undetected_genes'],
    }

    print(f"  Main variants: {len(context['variants'])} genes")
    print(f"  Summary variants: {len(context['summary_variants'])} genes")
    print(f"  Undetected genes: {len(context['undetected_genes'])} genes")

    # Show first few variants
    if context['variants']:
        print("\n  Sample variants:")
        for v in context['variants'][:3]:
            print(f"    - {v['gene']}: {v['cHGVS']}, {v['pHGVS']} ({v['frequency']}%)")

    # Render template
    print("\n[4/4] Rendering document...")
    try:
        doc.render(context)
        doc.save(output_path)
        print(f"  ✓ Document rendered successfully!")
        print(f"  Output: {output_path}")

        # Verify output
        output_size = os.path.getsize(output_path)
        print(f"  Size: {output_size:,} bytes")

    except Exception as e:
        print(f"  ✗ Render failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("Template test with real Excel data completed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    test_template_with_excel()
