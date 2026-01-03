#!/usr/bin/env python3
"""
Clean up gene variant table for Jinja2 loop rendering.

This script:
1. Finds the TP53 row (which already has loop markers from previous script)
2. Cleans up extra hardcoded content after {{ row.benefit_drugs }}
3. Deletes additional gene rows (SETD2, etc.) since the loop generates them

Python 3.9 compatible.
"""

import re


def add_variant_table_loops():
    doc_path = "/tmp/docx_template_358/word/document.xml"

    print("=" * 60)
    print("Cleaning Gene Variant Table for Jinja2 Loops")
    print("=" * 60)

    # Read the document
    print("\n[1/5] Reading document.xml...")
    with open(doc_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_size = len(content)
    print(f"  Original size: {original_size:,} bytes")

    # Step 1: Find TP53 row (which already has loop markers)
    print("\n[2/5] Locating TP53 row...")
    tp53_loop_pos = content.find('{% for row in variants %}{{ row.gene }}')
    if tp53_loop_pos == -1:
        print("  Loop marker not found, looking for TP53...")
        tp53_text_pos = content.find('<w:t>TP53</w:t>')
        if tp53_text_pos == -1:
            print("  ERROR: Could not find TP53 in document")
            return
        search_pos = tp53_text_pos
    else:
        search_pos = tp53_loop_pos
        print("  Found existing loop marker")

    tp53_row_start = content.rfind('<w:tr', 0, search_pos)
    tp53_row_end = content.find('</w:tr>', search_pos) + len('</w:tr>')
    print(f"  TP53 row: chars {tp53_row_start} to {tp53_row_end}")

    # Step 2: Find the next gene row (SETD2)
    print("\n[3/5] Locating additional gene rows...")
    setd2_pos = content.find('<w:t>SETD2</w:t>')
    if setd2_pos != -1:
        setd2_row_start = content.rfind('<w:tr', 0, setd2_pos)
        setd2_row_end = content.find('</w:tr>', setd2_pos) + len('</w:tr>')
        print(f"  SETD2 row: chars {setd2_row_start} to {setd2_row_end}")
    else:
        setd2_row_start = setd2_row_end = None
        print("  No SETD2 row found")

    # Step 3: Clean up TP53 row
    print("\n[4/5] Cleaning TP53 row...")
    tp53_row = content[tp53_row_start:tp53_row_end]

    # Find the benefit_drugs variable and remove content after it
    benefit_drugs_pos = tp53_row.find('{{ row.benefit_drugs }}')
    if benefit_drugs_pos != -1:
        # Find the cell containing benefit_drugs
        # Pattern: the whole third cell (潜在获益靶向药物)
        # We need to find where benefit_drugs cell starts and ends
        # Look for </w:tc> after the benefit_drugs variable
        cell_end_after_benefit = tp53_row.find('</w:tc>', benefit_drugs_pos)

        # Find the paragraph containing benefit_drugs
        para_end = tp53_row.find('</w:p>', benefit_drugs_pos)

        # Check if there's additional paragraphs in this cell
        between = tp53_row[para_end + len('</w:p>'):cell_end_after_benefit]

        if '<w:p' in between:
            extra_count = between.count('<w:p')
            print(f"  Found {extra_count} extra paragraph(s) to remove")

            # Create cleaned row by removing extra paragraphs
            cleaned_row = tp53_row[:para_end + len('</w:p>')] + '\n        ' + tp53_row[cell_end_after_benefit:]
            print("  ✓ Removed extra drug paragraphs from TP53 row")
        else:
            cleaned_row = tp53_row
            print("  No extra content to remove in benefit_drugs cell")
    else:
        cleaned_row = tp53_row
        print("  Could not find benefit_drugs variable")

    # Step 5: Build new content
    print("\n[5/5] Building new document...")

    if setd2_row_start and setd2_row_end:
        # Remove SETD2 row
        new_content = content[:tp53_row_start] + cleaned_row + content[setd2_row_end:]
        print(f"  ✓ Removed SETD2 row")
    else:
        # Just replace TP53 row with cleaned version
        new_content = content[:tp53_row_start] + cleaned_row + content[tp53_row_end:]

    # Save
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    new_size = len(new_content)
    print(f"\n  Original size: {original_size:,} bytes")
    print(f"  New size: {new_size:,} bytes")
    print(f"  Removed: {original_size - new_size:,} bytes")

    print("\n" + "=" * 60)
    print("Gene variant table cleanup completed!")
    print("=" * 60)

    # Verify the result
    print("\nVerification:")
    if '{% for row in variants %}' in new_content:
        print("  ✓ Loop start marker found")
    else:
        print("  ✗ Loop start marker NOT found!")

    if '{% endfor %}' in new_content:
        print("  ✓ Loop end marker found")
    else:
        print("  ✗ Loop end marker NOT found!")

    if 'SETD2' not in new_content:
        print("  ✓ SETD2 row successfully removed")
    else:
        print("  ⚠ SETD2 still found in document")


if __name__ == "__main__":
    add_variant_table_loops()
