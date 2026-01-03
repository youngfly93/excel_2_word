#!/usr/bin/env python3
"""
Add Jinja2 loop markers to the summary variant table.

Based on analysis:
- Summary table header "转录本号" at line 10899
- TP53 row: lines 11419-11972
- KRAS row: lines 11973-13179
- APC rows: lines 13180-13951
- SETD2 row: lines 13952-14378

This script:
1. Reads TP53 row as template
2. Adds {% for row in summary_variants %} before gene name
3. Replaces hardcoded values with template variables
4. Adds {% endfor %} at the end
5. Removes KRAS, APC, SETD2 rows

Python 3.9 compatible.
"""

import re


def add_summary_table_loop():
    doc_path = "/tmp/docx_template_358/word/document.xml"

    print("=" * 60)
    print("Adding Summary Table Jinja2 Loop (v2)")
    print("=" * 60)

    # Read the document
    print("\n[1/7] Reading document.xml...")
    with open(doc_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    original_line_count = len(lines)
    print(f"  Total lines: {original_line_count:,}")

    # Step 1: Verify we have the right structure
    print("\n[2/7] Verifying document structure...")

    # Check for expected patterns at known lines
    if "TP53" not in lines[11477]:  # 0-indexed: line 11478
        print(f"  WARNING: TP53 not at expected line 11478")
        print(f"  Line 11478 content: {lines[11477][:80]}...")
    else:
        print("  ✓ TP53 found at line 11478")

    if "SETD2" not in lines[14010]:  # 0-indexed: line 14011
        print(f"  WARNING: SETD2 not at expected line 14011")
    else:
        print("  ✓ SETD2 found at line 14011")

    # Step 2: Extract TP53 row (lines 11419-11972, 0-indexed: 11418-11971)
    print("\n[3/7] Extracting TP53 row as template...")
    tp53_start = 11418  # 0-indexed
    tp53_end = 11972    # 0-indexed, exclusive

    tp53_row_lines = lines[tp53_start:tp53_end]
    tp53_row = ''.join(tp53_row_lines)
    print(f"  TP53 row: {len(tp53_row_lines)} lines, {len(tp53_row):,} chars")

    # Step 3: Create template from TP53 row
    print("\n[4/7] Creating template with Jinja2 variables...")

    template_row = tp53_row

    # 3a. Add loop start and replace gene name
    template_row = template_row.replace(
        '<w:t>TP53</w:t>',
        '<w:t>{% for row in summary_variants %}{{ row.gene }}</w:t>'
    )

    # 3b. Replace transcript (NM_000546.6)
    template_row = re.sub(
        r'<w:t>NM_\d+\.\d+</w:t>',
        '<w:t>{{ row.transcript }}</w:t>',
        template_row,
        count=1
    )

    # 3c. Replace chromosome number (17)
    # Find the pattern after transcript
    template_row = re.sub(
        r'(<w:t>)(\d{1,2})(</w:t>)',
        r'\1{{ row.chromosome }}\3',
        template_row,
        count=1
    )

    # 3d. Replace exon number (8)
    # The second number occurrence
    template_row = re.sub(
        r'(<w:t>)(\d{1,2})(</w:t>)',
        r'\1{{ row.exon }}\3',
        template_row,
        count=1
    )

    # 3e. Replace cHGVS (c.844C>T)
    template_row = re.sub(
        r'<w:t>c\.[^<]+</w:t>',
        '<w:t>{{ row.cHGVS }}</w:t>',
        template_row,
        count=1
    )

    # 3f. Replace pHGVS (p.R282W)
    template_row = re.sub(
        r'<w:t>p\.[^<]+</w:t>',
        '<w:t>{{ row.pHGVS }}</w:t>',
        template_row,
        count=1
    )

    # 3g. Replace mutation type (点突变 in Unicode entities)
    # &#28857;&#31361;&#21464; = 点突变
    mutation_patterns = [
        '&#28857;&#31361;&#21464;',  # 点突变
        '错义突变', '&#38169;&#20041;&#31361;&#21464;',
        '无义突变', '&#26080;&#20041;&#31361;&#21464;',
        '缺失突变', '&#32570;&#22833;&#31361;&#21464;',
        '插入突变', '&#25554;&#20837;&#31361;&#21464;',
        '移码突变', '&#31227;&#30721;&#31361;&#21464;',
    ]
    for mt in mutation_patterns:
        if f'<w:t>{mt}</w:t>' in template_row:
            template_row = template_row.replace(
                f'<w:t>{mt}</w:t>',
                '<w:t>{{ row.mutation_type }}</w:t>',
                1
            )
            print(f"    Replaced mutation type: {mt[:10]}...")
            break

    # 3h. Replace frequency (67.29)
    template_row = re.sub(
        r'<w:t>(\d+\.\d+)</w:t>',
        '<w:t>{{ row.frequency }}</w:t>',
        template_row,
        count=1
    )

    # 3i. Handle benefit_drugs and caution_drugs
    # Find the last two cells and replace their content

    # Split template into lines for easier manipulation
    template_lines = template_row.split('\n')

    # Find cells with drug content by looking for blue colored links
    # The drugs are typically in blue text with underline
    drugs_found = 0
    for i, line in enumerate(template_lines):
        # Look for drug names - they appear after the frequency
        if 'AZD1775' in line or 'Olaparib' in line or '奥拉帕利' in line:
            # This is benefit drugs cell
            template_lines[i] = re.sub(
                r'<w:t>[^<]+</w:t>',
                '<w:t>{{ row.benefit_drugs }}</w:t>',
                line
            )
            drugs_found += 1
            break

    template_row = '\n'.join(template_lines)

    # 3j. Add endfor at the very end of the row (before </w:tr>)
    template_row = template_row.rstrip()
    if template_row.endswith('</w:tr>'):
        # Insert endfor before the closing tag
        template_row = template_row[:-len('</w:tr>')] + '{% endfor %}</w:tr>\n'

    print("  Created template with variables:")
    print("    - {% for row in summary_variants %}")
    print("    - {{ row.gene }}")
    print("    - {{ row.transcript }}")
    print("    - {{ row.chromosome }}")
    print("    - {{ row.exon }}")
    print("    - {{ row.cHGVS }}")
    print("    - {{ row.pHGVS }}")
    print("    - {{ row.mutation_type }}")
    print("    - {{ row.frequency }}")
    print("    - {% endfor %}")

    # Step 4: Calculate what to remove
    print("\n[5/7] Calculating rows to remove...")

    # All gene rows: 11419-14378 (1-indexed)
    # In 0-indexed: 11418-14377 (exclusive: 14378)
    all_rows_start = 11418
    all_rows_end = 14378

    rows_to_remove = all_rows_end - all_rows_start
    print(f"  Removing lines {all_rows_start+1} to {all_rows_end} ({rows_to_remove} lines)")
    print(f"  This includes: TP53, KRAS, APC, SETD2 rows")

    # Step 5: Build new document
    print("\n[6/7] Building new document...")

    new_lines = lines[:all_rows_start] + [template_row] + lines[all_rows_end:]
    new_content = ''.join(new_lines)

    print(f"  Original lines: {original_line_count:,}")
    print(f"  New lines: {len(new_lines):,}")
    print(f"  Removed: {original_line_count - len(new_lines):,} lines")

    # Step 6: Save
    print("\n[7/7] Saving document...")
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("  ✓ Document saved")

    # Verification
    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)

    if '{% for row in summary_variants %}' in new_content:
        print("  ✓ Loop start marker found")
    else:
        print("  ✗ Loop start marker NOT found!")

    endfor_count = new_content.count('{% endfor %}')
    if endfor_count >= 2:
        print(f"  ✓ Found {endfor_count} endfor markers (main table + summary)")
    else:
        print(f"  ⚠ Only {endfor_count} endfor marker(s) found")

    # Check that extra genes are removed
    for gene in ['KRAS', 'APC', 'SETD2']:
        # Check in the summary table area (roughly)
        summary_area = new_content[400000:600000] if len(new_content) > 600000 else new_content[400000:]
        if f'<w:t>{gene}</w:t>' in summary_area:
            print(f"  ⚠ {gene} may still be in summary table area")
        else:
            print(f"  ✓ {gene} not in summary table area")

    print("\n" + "=" * 60)
    print("Summary table loop completed!")
    print("=" * 60)


if __name__ == "__main__":
    add_summary_table_loop()
