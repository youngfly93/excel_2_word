#!/usr/bin/env python3
"""
Test the full ReportGenerator pipeline with the integrated template bridge.

This script tests the end-to-end report generation using:
- ExcelReader -> FieldMapper -> DataCleaner -> Template Bridge -> TemplateRenderer

Python 3.9 compatible.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from reportgen.core.report_generator import ReportGenerator


def test_full_pipeline():
    """Test the complete report generation pipeline."""
    print("=" * 70)
    print("Full Pipeline Test with Template Bridge Integration")
    print("=" * 70)

    # Paths
    excel_path = project_root / "data" / "input" / "MLF2509307001T_MLB2509307001.result.xlsx"
    template_path = project_root / "templates" / "jinja2_template_358_v5.docx"
    output_dir = project_root / "output"
    config_dir = str(project_root / "config")

    # Check files
    print("\n[1/3] Checking input files...")
    if not excel_path.exists():
        print(f"  ERROR: Excel file not found: {excel_path}")
        return False
    print(f"  [OK] Excel: {excel_path.name}")

    if not template_path.exists():
        print(f"  ERROR: Template not found: {template_path}")
        return False
    print(f"  [OK] Template: {template_path.name}")

    # Create generator
    print("\n[2/3] Initializing ReportGenerator...")
    generator = ReportGenerator(config_dir=config_dir, log_level="INFO")
    print("  [OK] Generator initialized")

    # Validate inputs
    is_valid, errors = generator.validate_inputs(
        str(excel_path), str(template_path), str(output_dir)
    )
    print(f"\n  Input validation: {'PASSED' if is_valid else 'FAILED'}")
    if errors:
        for error in errors:
            print(f"    - {error}")

    # Generate report
    print("\n[3/3] Generating report...")
    result = generator.generate(
        excel_file=str(excel_path),
        template_file=str(template_path),
        output_dir=str(output_dir),
        output_filename="test_pipeline_output.docx",
        strict_mode=False,
    )

    print(f"\n  Result:")
    print(f"    Success: {result['success']}")
    print(f"    Duration: {result['duration']:.2f} seconds")

    if result['success']:
        print(f"    Output: {result['output_file']}")
        import os
        size = os.path.getsize(result['output_file'])
        print(f"    Size: {size:,} bytes")
    else:
        print(f"    Errors: {result['errors']}")

    if result.get('warnings'):
        print(f"    Warnings: {len(result['warnings'])}")

    # Show statistics
    stats = generator.get_statistics()
    print(f"\n  Generator Statistics:")
    for key, value in stats.items():
        print(f"    {key}: {value}")

    print("\n" + "=" * 70)
    print(f"Full Pipeline Test: {'SUCCESS' if result['success'] else 'FAILED'}")
    print("=" * 70)

    return result['success']


if __name__ == "__main__":
    success = test_full_pipeline()
    sys.exit(0 if success else 1)
