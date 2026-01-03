#!/usr/bin/env python3
"""
Test the existing reportgen pipeline with real Excel data.

This script:
1. Uses ExcelReader to parse the real Excel file
2. Uses FieldMapper to generate report data
3. Shows what data format is produced
4. Identifies gaps between current output and template requirements

Python 3.9 compatible.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from reportgen.core.excel_reader import ExcelReader
from reportgen.core.field_mapper import FieldMapper
from reportgen.core.report_generator import ReportGenerator


def test_excel_reader():
    """Test ExcelReader with real Excel file."""
    print("=" * 70)
    print("1. Testing ExcelReader")
    print("=" * 70)

    excel_path = project_root / "data" / "input" / "MLF2509307001T_MLB2509307001.result.xlsx"
    config_dir = str(project_root / "config")

    if not excel_path.exists():
        print(f"  ERROR: Excel file not found: {excel_path}")
        return None

    reader = ExcelReader(config_dir=config_dir, log_level="WARNING")
    excel_data = reader.read(str(excel_path))

    print(f"\n  File: {excel_path.name}")
    print(f"  Sample ID: {excel_data.metadata.get('sample_id_from_filename', 'N/A')}")

    print("\n  Single Values:")
    for key, value in list(excel_data.single_values.items())[:10]:
        print(f"    {key}: {value}")
    if len(excel_data.single_values) > 10:
        print(f"    ... and {len(excel_data.single_values) - 10} more")

    print("\n  Table Data:")
    for table_name, rows in excel_data.table_data.items():
        print(f"    {table_name}: {len(rows)} rows")
        if rows and len(rows) > 0:
            print(f"      Columns: {list(rows[0].keys())[:5]}...")

    return excel_data


def test_field_mapper(excel_data):
    """Test FieldMapper with parsed Excel data."""
    print("\n" + "=" * 70)
    print("2. Testing FieldMapper")
    print("=" * 70)

    if excel_data is None:
        print("  Skipped: No Excel data")
        return None

    config_dir = str(project_root / "config")
    mapper = FieldMapper(config_dir=config_dir, log_level="WARNING")

    report_data = mapper.map(excel_data)

    print("\n  Report Data Context:")
    context = report_data.get_template_context()

    # Show single values
    single_values = {k: v for k, v in context.items() if not isinstance(v, list)}
    print(f"\n  Single Values ({len(single_values)}):")
    for key, value in list(single_values.items())[:15]:
        val_str = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
        print(f"    {key}: {val_str}")

    # Show table data
    tables = {k: v for k, v in context.items() if isinstance(v, list)}
    print(f"\n  Tables ({len(tables)}):")
    for table_name, rows in tables.items():
        print(f"    {table_name}: {len(rows)} rows")
        if rows and len(rows) > 0:
            print(f"      Columns: {list(rows[0].keys())}")
            # Show first row as sample
            if len(rows) > 0:
                print(f"      Sample row: {rows[0]}")

    # Check for specific tables needed by template
    print("\n  Template Requirements Check:")
    required_tables = ["variants", "summary_variants", "undetected_genes", "variants_2_1"]
    for table in required_tables:
        if table in tables:
            print(f"    [OK] {table}: {len(tables[table])} rows")
        else:
            print(f"    [MISSING] {table}")

    return report_data


def analyze_data_format_gap(report_data):
    """Analyze the gap between current format and template requirements."""
    print("\n" + "=" * 70)
    print("3. Data Format Gap Analysis")
    print("=" * 70)

    if report_data is None:
        print("  Skipped: No report data")
        return

    context = report_data.get_template_context()

    # Template expects these columns in 'variants'
    template_variant_columns = [
        "gene", "transcript", "chromosome", "exon", "cHGVS", "pHGVS",
        "mutation_type", "frequency", "gene_class", "clinical_significance",
        "benefit_drugs", "caution_drugs"
    ]

    # FieldMapper produces 'variants_2_1' with these columns
    variants_2_1_columns = [
        "gene", "transcript", "chr", "exon", "locus", "var_type_cn",
        "af_pct", "benefit_drugs", "caution_drugs"
    ]

    print("\n  Template 'variants' expected columns:")
    for col in template_variant_columns:
        print(f"    - {col}")

    print("\n  FieldMapper 'variants_2_1' actual columns:")
    if "variants_2_1" in context:
        actual_cols = list(context["variants_2_1"][0].keys()) if context["variants_2_1"] else []
        for col in actual_cols:
            print(f"    - {col}")
    else:
        print("    (table not generated)")

    # Mapping suggestions
    print("\n  Column Mapping Required:")
    mapping_needed = [
        ("chr", "chromosome", "rename"),
        ("locus", "cHGVS, pHGVS", "split on comma"),
        ("var_type_cn", "mutation_type", "rename"),
        ("af_pct", "frequency", "rename"),
        ("(none)", "gene_class", "derive from ExistIn552 column"),
        ("(none)", "clinical_significance", "derive from CLNSIG or default '致病'"),
    ]
    for src, dst, action in mapping_needed:
        print(f"    {src} -> {dst}: {action}")

    # Additional tables needed
    print("\n  Additional Tables Needed:")
    print("    - summary_variants: Simplified variant list for summary section")
    print("    - undetected_genes: List of panel genes with no detected mutations")


def test_full_pipeline():
    """Test the full ReportGenerator pipeline (without actual rendering)."""
    print("\n" + "=" * 70)
    print("4. Testing Full Pipeline (Preview)")
    print("=" * 70)

    excel_path = project_root / "data" / "input" / "MLF2509307001T_MLB2509307001.result.xlsx"
    template_path = project_root / "templates" / "jinja2_template_358_v5.docx"
    config_dir = str(project_root / "config")

    if not excel_path.exists():
        print(f"  ERROR: Excel file not found: {excel_path}")
        return

    if not template_path.exists():
        print(f"  ERROR: Template not found: {template_path}")
        return

    generator = ReportGenerator(config_dir=config_dir, log_level="WARNING")

    # Validate inputs
    is_valid, errors = generator.validate_inputs(
        str(excel_path), str(template_path), str(project_root / "output")
    )

    print(f"\n  Input Validation: {'PASSED' if is_valid else 'FAILED'}")
    if errors:
        for error in errors:
            print(f"    - {error}")

    # Show statistics
    stats = generator.get_statistics()
    print(f"\n  Generator Statistics:")
    for key, value in stats.items():
        print(f"    {key}: {value}")


def main():
    """Run all tests."""
    print("=" * 70)
    print("ReportGen Pipeline Test")
    print("=" * 70)

    # Test 1: Excel Reader
    excel_data = test_excel_reader()

    # Test 2: Field Mapper
    report_data = test_field_mapper(excel_data)

    # Test 3: Gap Analysis
    analyze_data_format_gap(report_data)

    # Test 4: Full Pipeline Preview
    test_full_pipeline()

    print("\n" + "=" * 70)
    print("Test Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
