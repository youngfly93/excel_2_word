#!/usr/bin/env python3
"""
Test the template_bridge_358 module with real Excel data.

This script verifies that:
1. build_variants_for_template() correctly filters and formats variants
2. build_summary_variants() creates the summary table
3. build_undetected_genes() identifies genes without mutations
4. enhance_report_data() integrates all pieces

Python 3.9 compatible.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from reportgen.core.excel_reader import ExcelReader
from reportgen.core.field_mapper import FieldMapper
from reportgen.core.template_bridge_358 import (
    build_variants_for_template,
    build_summary_variants,
    build_undetected_genes,
    build_msi_summary,
    build_tmb_summary,
    enhance_report_data,
)


def test_build_variants():
    """Test build_variants_for_template function."""
    print("=" * 70)
    print("1. Testing build_variants_for_template()")
    print("=" * 70)

    excel_path = project_root / "data" / "input" / "MLF2509307001T_MLB2509307001.result.xlsx"
    config_dir = str(project_root / "config")

    if not excel_path.exists():
        print(f"  ERROR: Excel file not found: {excel_path}")
        return None

    reader = ExcelReader(config_dir=config_dir, log_level="WARNING")
    excel_data = reader.read(str(excel_path))

    variants = build_variants_for_template(excel_data)

    print(f"\n  Found {len(variants)} variants in 358 panel")

    if variants:
        print("\n  Expected columns:")
        expected = [
            "gene", "transcript", "chromosome", "exon", "cHGVS", "pHGVS",
            "mutation_type", "frequency", "gene_class", "clinical_significance",
            "benefit_drugs", "caution_drugs"
        ]
        for col in expected:
            if col in variants[0]:
                print(f"    [OK] {col}: '{variants[0][col]}'")
            else:
                print(f"    [MISSING] {col}")

        print("\n  Sample variants:")
        for v in variants[:5]:
            print(f"    - {v['gene']}: {v['cHGVS']}, {v['pHGVS']} ({v['frequency']}%)")
            print(f"      Class: {v['gene_class']}, Type: {v['mutation_type']}")

    return excel_data, variants


def test_build_summary_variants(variants):
    """Test build_summary_variants function."""
    print("\n" + "=" * 70)
    print("2. Testing build_summary_variants()")
    print("=" * 70)

    if not variants:
        print("  Skipped: No variants")
        return None

    summary = build_summary_variants(variants)
    print(f"\n  Generated {len(summary)} summary variants")

    if summary:
        print("\n  Sample summary variant:")
        s = summary[0]
        print(f"    Gene: {s['gene']}")
        print(f"    Transcript: {s['transcript']}")
        print(f"    Mutation: {s['cHGVS']}, {s['pHGVS']}")
        print(f"    Type: {s['mutation_type']}")

    return summary


def test_build_undetected_genes(variants):
    """Test build_undetected_genes function."""
    print("\n" + "=" * 70)
    print("3. Testing build_undetected_genes()")
    print("=" * 70)

    detected = {v["gene"] for v in variants} if variants else set()
    print(f"\n  Detected genes ({len(detected)}): {', '.join(sorted(detected)[:10])}...")

    undetected = build_undetected_genes(detected)
    print(f"\n  Undetected panel genes ({len(undetected)}):")
    for g in undetected[:8]:
        print(f"    - {g['name']} ({g['transcript']}) - chr{g['chromosome']}")

    return undetected


def test_msi_tmb_summary(excel_data):
    """Test MSI and TMB summary functions."""
    print("\n" + "=" * 70)
    print("4. Testing MSI/TMB Summary")
    print("=" * 70)

    if not excel_data:
        print("  Skipped: No Excel data")
        return

    msi = build_msi_summary(excel_data)
    print("\n  MSI Summary:")
    for key, value in msi.items():
        print(f"    {key}: {value}")

    tmb = build_tmb_summary(excel_data)
    print("\n  TMB Summary:")
    for key, value in tmb.items():
        print(f"    {key}: {value}")


def test_enhance_report_data(excel_data):
    """Test the full enhance_report_data function."""
    print("\n" + "=" * 70)
    print("5. Testing enhance_report_data()")
    print("=" * 70)

    if not excel_data:
        print("  Skipped: No Excel data")
        return None

    config_dir = str(project_root / "config")
    mapper = FieldMapper(config_dir=config_dir, log_level="WARNING")
    report_data = mapper.map(excel_data)

    print("\n  Before enhancement:")
    context_before = report_data.get_template_context()
    tables_before = {k: v for k, v in context_before.items() if isinstance(v, list)}
    for name, rows in tables_before.items():
        print(f"    {name}: {len(rows)} rows")

    # Enhance with template bridge
    enhanced = enhance_report_data(report_data, excel_data)

    print("\n  After enhancement:")
    context_after = enhanced.get_template_context()

    # Check required tables
    required = ["variants", "summary_variants", "undetected_genes"]
    for table in required:
        if table in context_after and isinstance(context_after[table], list):
            print(f"    [OK] {table}: {len(context_after[table])} rows")
        else:
            print(f"    [MISSING] {table}")

    # Check MSI/TMB fields
    msi_tmb_fields = ["msi_status", "msi_status_cn", "tmb_value", "tmb_status"]
    print("\n  MSI/TMB Fields:")
    for field in msi_tmb_fields:
        if field in context_after:
            print(f"    [OK] {field}: {context_after[field]}")
        else:
            print(f"    [MISSING] {field}")

    return enhanced


def test_template_rendering(report_data):
    """Test rendering the Jinja2 template with enhanced data."""
    print("\n" + "=" * 70)
    print("6. Testing Template Rendering")
    print("=" * 70)

    if not report_data:
        print("  Skipped: No report data")
        return

    template_path = project_root / "templates" / "jinja2_template_358_v5.docx"
    output_path = project_root / "templates" / "test_bridge_output.docx"

    if not template_path.exists():
        print(f"  ERROR: Template not found: {template_path}")
        return

    try:
        from docxtpl import DocxTemplate

        doc = DocxTemplate(str(template_path))
        context = report_data.get_template_context()

        print(f"\n  Template: {template_path.name}")
        print(f"  Context keys: {len(context)}")

        # Show key table sizes
        print("\n  Table sizes for rendering:")
        for key in ["variants", "summary_variants", "undetected_genes"]:
            if key in context:
                print(f"    {key}: {len(context[key])} rows")

        doc.render(context)
        doc.save(str(output_path))

        import os
        size = os.path.getsize(output_path)
        print(f"\n  [SUCCESS] Rendered to: {output_path.name}")
        print(f"  Output size: {size:,} bytes")

    except Exception as e:
        print(f"\n  [ERROR] Rendering failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests."""
    print("=" * 70)
    print("Template Bridge 358 Module Test")
    print("=" * 70)

    # Test 1: Build variants
    result = test_build_variants()
    if result is None:
        return
    excel_data, variants = result

    # Test 2: Build summary variants
    summary = test_build_summary_variants(variants)

    # Test 3: Build undetected genes
    undetected = test_build_undetected_genes(variants)

    # Test 4: MSI/TMB summary
    test_msi_tmb_summary(excel_data)

    # Test 5: Full enhancement
    enhanced = test_enhance_report_data(excel_data)

    # Test 6: Template rendering
    test_template_rendering(enhanced)

    print("\n" + "=" * 70)
    print("All Tests Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
