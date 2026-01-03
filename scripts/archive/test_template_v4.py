#!/usr/bin/env python3
"""
Test the Jinja2 template v4 with docxtpl.
Tests main variant, summary variant, and undetected genes loops.
"""

from docxtpl import DocxTemplate
import os

def test_template():
    template_path = "/Volumes/KINGSTON/work/minhao/肠癌358基因/templates/jinja2_template_358_v4.docx"
    output_path = "/Volumes/KINGSTON/work/minhao/肠癌358基因/templates/test_output_v4.docx"

    print("=" * 60)
    print("Testing Template v4 with docxtpl")
    print("=" * 60)

    # Load template
    print("\n[1/3] Loading template...")
    doc = DocxTemplate(template_path)
    print(f"  Template loaded successfully")

    # Prepare test data
    print("\n[2/3] Preparing test data...")

    context = {
        # Basic patient info
        "patient_name": "测试患者",
        "gender": "男",
        "age": "55",
        "sample_id": "TEST-001",
        "pathological_diagnosis": "结肠癌",
        "specimen_type": "组织",
        "report_date": "2025-01-15",
        "received_date": "2025-01-10",

        # Main variant table - detailed gene info
        "variants": [
            {
                "gene": "TP53",
                "transcript": "NM_000546.6",
                "chromosome": "17",
                "exon": "8",
                "cHGVS": "c.844C>T",
                "pHGVS": "p.R282W",
                "mutation_type": "错义突变",
                "frequency": "67.29",
                "gene_class": "Ⅲ类",
                "clinical_significance": "致病",
                "benefit_drugs": "AZD1775（C）",
                "caution_drugs": "--"
            },
            {
                "gene": "KRAS",
                "transcript": "NM_033360.4",
                "chromosome": "12",
                "exon": "2",
                "cHGVS": "c.35G>A",
                "pHGVS": "p.G12D",
                "mutation_type": "错义突变",
                "frequency": "42.15",
                "gene_class": "Ⅰ类",
                "clinical_significance": "致病",
                "benefit_drugs": "--",
                "caution_drugs": "西妥昔单抗（1A）"
            },
        ],

        # Summary variant table - simplified for summary section
        "summary_variants": [
            {
                "gene": "TP53",
                "transcript": "NM_000546.6",
                "chromosome": "17",
                "exon": "8",
                "cHGVS": "c.844C>T",
                "pHGVS": "p.R282W",
                "mutation_type": "点突变",
                "frequency": "67.29",
                "benefit_drugs": "AZD1775（C）",
                "caution_drugs": "--"
            },
            {
                "gene": "KRAS",
                "transcript": "NM_033360.4",
                "chromosome": "12",
                "exon": "2",
                "cHGVS": "c.35G>A",
                "pHGVS": "p.G12D",
                "mutation_type": "点突变",
                "frequency": "42.15",
                "benefit_drugs": "--",
                "caution_drugs": "西妥昔单抗（1A）"
            },
            {
                "gene": "APC",
                "transcript": "NM_000038.6",
                "chromosome": "5",
                "exon": "16",
                "cHGVS": "c.4348C>T",
                "pHGVS": "p.R1450*",
                "mutation_type": "无义突变",
                "frequency": "55.30",
                "benefit_drugs": "--",
                "caution_drugs": "--"
            },
            # Additional variant genes that were in EPHA2, FANCI, ATM rows
            {
                "gene": "EPHA2",
                "transcript": "NM_004431.5",
                "chromosome": "1",
                "exon": "2",
                "cHGVS": "c.153+2T>C",
                "pHGVS": "--",
                "mutation_type": "点突变",
                "frequency": "32.10",
                "benefit_drugs": "--",
                "caution_drugs": "--"
            },
        ],

        # Undetected genes - genes with no mutations found
        "undetected_genes": [
            {"name": "BRAF", "transcript": "NM_004333.4", "chromosome": "7"},
            {"name": "ERBB2", "transcript": "NM_004448.4", "chromosome": "17"},
            {"name": "NRAS", "transcript": "NM_002524.5", "chromosome": "1"},
            {"name": "PIK3CA", "transcript": "NM_006218.4", "chromosome": "3"},
            {"name": "SMAD4", "transcript": "NM_005359.6", "chromosome": "18"},
            {"name": "MLH1", "transcript": "NM_000249.4", "chromosome": "3"},
            {"name": "MSH2", "transcript": "NM_000251.3", "chromosome": "2"},
            {"name": "MSH6", "transcript": "NM_000179.3", "chromosome": "2"},
            {"name": "PMS2", "transcript": "NM_000535.7", "chromosome": "7"},
        ],
    }

    print(f"  Main variants: {len(context['variants'])} genes")
    print(f"  Summary variants: {len(context['summary_variants'])} genes")
    print(f"  Undetected genes: {len(context['undetected_genes'])} genes")

    # Render
    print("\n[3/3] Rendering document...")
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
    print("Template test completed successfully!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    test_template()
