#!/usr/bin/env python3
"""
Add Jinja2 loop markers to the summary variant table.

This script:
1. Finds the summary table (around line 10620)
2. Locates the TP53 row (first gene data row around line 11419)
3. Locates the SETD2 row (second gene data row around line 14011)
4. Adds {% for row in summary_variants %} before first row
5. Replaces hardcoded values with template variables
6. Adds {% endfor %} after last row
7. Removes SETD2 row(s) since the loop generates them

Python 3.9 compatible.
"""

import re


def add_summary_table_loop():
    doc_path = "/tmp/docx_template_358/word/document.xml"

    print("=" * 60)
    print("Adding Summary Table Jinja2 Loop")
    print("=" * 60)

    # Read the document
    print("\n[1/6] Reading document.xml...")
    with open(doc_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_size = len(content)
    print(f"  Original size: {original_size:,} bytes")

    # Step 1: Find the summary table header (转录本号)
    print("\n[2/6] Locating summary table and TP53 data row...")

    # Find the "转录本号" header which marks the summary table
    transcript_header = content.find('&#36716;&#24405;&#26412;&#21495;')
    if transcript_header == -1:
        transcript_header = content.find('转录本号')

    if transcript_header == -1:
        print("  ERROR: Could not find 转录本号 header")
        return

    print(f"  Found 转录本号 header at position {transcript_header}")

    # Find TP53 AFTER the header (in the data rows, not other sections)
    tp53_pos = content.find('<w:t>TP53</w:t>', transcript_header)
    if tp53_pos == -1:
        print("  ERROR: Could not find TP53 after header")
        return

    print(f"  Found TP53 at position {tp53_pos}")

    # Verify this TP53 is in a table row and has transcript nearby
    nearby = content[tp53_pos:tp53_pos+500]
    if 'NM_000546' not in nearby:
        print("  WARNING: TP53 found but no NM_000546 transcript nearby")
        print("  Searching for correct TP53...")
        # Find next TP53
        tp53_pos = content.find('<w:t>TP53</w:t>', tp53_pos + 100)
        if tp53_pos == -1:
            print("  ERROR: Could not find TP53 with transcript")
            return

    # Find the row containing this TP53
    tp53_row_start = content.rfind('<w:tr', 0, tp53_pos)
    tp53_row_end = content.find('</w:tr>', tp53_pos) + len('</w:tr>')
    print(f"  TP53 row: chars {tp53_row_start} to {tp53_row_end}")

    # Step 2: Find SETD2 row
    print("\n[3/6] Locating SETD2 data row...")
    setd2_pos = content.find('<w:t>SETD2</w:t>', tp53_row_end)
    if setd2_pos != -1:
        setd2_row_start = content.rfind('<w:tr', 0, setd2_pos)
        setd2_row_end = content.find('</w:tr>', setd2_pos) + len('</w:tr>')
        print(f"  SETD2 row: chars {setd2_row_start} to {setd2_row_end}")

        # Check for continuation rows (vMerge continue)
        # SETD2 may have multiple rows with merged cells
        last_row_end = setd2_row_end
        while True:
            # Look for the next row
            next_row_start = content.find('<w:tr', last_row_end)
            if next_row_start == -1 or next_row_start > setd2_pos + 10000:
                break
            next_row_end = content.find('</w:tr>', next_row_start) + len('</w:tr>')
            row_content = content[next_row_start:next_row_end]
            # Check if this is a continuation row (vMerge continue without a gene name)
            if '<w:vMerge w:val="continue"/>' in row_content and '<w:t>SETD2</w:t>' not in row_content:
                # Check if no new gene appears
                if not re.search(r'<w:t>[A-Z][A-Z0-9]+</w:t>', row_content.replace('NM_', 'NM-')):
                    last_row_end = next_row_end
                    continue
            break
        setd2_row_end = last_row_end
        print(f"  SETD2 rows end at: {setd2_row_end}")
    else:
        setd2_row_start = setd2_row_end = None
        print("  No SETD2 row found")

    # Step 3: Extract and modify TP53 row as template
    print("\n[4/6] Creating template row from TP53...")
    tp53_row = content[tp53_row_start:tp53_row_end]

    # Replace TP53 with loop start + gene variable
    template_row = tp53_row.replace(
        '<w:t>TP53</w:t>',
        '<w:t>{% for row in summary_variants %}{{ row.gene }}</w:t>'
    )

    # Replace transcript NM_000546.6
    template_row = re.sub(
        r'<w:t>NM_\d+\.\d+</w:t>',
        '<w:t>{{ row.transcript }}</w:t>',
        template_row,
        count=1
    )

    # Replace chromosome number (first single digit after transcript)
    template_row = re.sub(
        r'(<w:t>)(\d{1,2})(</w:t>)',
        r'\1{{ row.chromosome }}\3',
        template_row,
        count=1
    )

    # Replace exon number (second single/double digit)
    # This is tricky because there are multiple numbers

    # Replace cHGVS (pattern like c.XXX)
    template_row = re.sub(
        r'<w:t>c\.[^<]+</w:t>',
        '<w:t>{{ row.cHGVS }},</w:t>',
        template_row,
        count=1
    )

    # Replace pHGVS (pattern like p.XXX)
    template_row = re.sub(
        r'<w:t>p\.[^<]+</w:t>',
        '<w:t>{{ row.pHGVS }}</w:t>',
        template_row,
        count=1
    )

    # Replace mutation type (Chinese text for mutation type)
    # Common types: 错义突变, 无义突变, 缺失突变, 插入突变, 移码突变
    mutation_types = ['错义突变', '无义突变', '缺失突变', '插入突变', '移码突变',
                      '&#38169;&#20041;&#31361;&#21464;', '&#26080;&#20041;&#31361;&#21464;',
                      '&#32570;&#22833;&#31361;&#21464;', '&#25554;&#20837;&#31361;&#21464;',
                      '&#31227;&#30721;&#31361;&#21464;']
    for mt in mutation_types:
        if mt in template_row:
            template_row = template_row.replace(f'<w:t>{mt}</w:t>', '<w:t>{{ row.mutation_type }}</w:t>', 1)
            break

    # Replace frequency (pattern like XX.XX or XX%)
    template_row = re.sub(
        r'<w:t>(\d+\.?\d*%?)</w:t>',
        '<w:t>{{ row.frequency }}</w:t>',
        template_row,
        count=1
    )

    print("  Created template with variables:")
    print("    - {{ row.gene }}")
    print("    - {{ row.transcript }}")
    print("    - {{ row.chromosome }}")
    print("    - {{ row.cHGVS }}")
    print("    - {{ row.pHGVS }}")
    print("    - {{ row.mutation_type }}")
    print("    - {{ row.frequency }}")

    # Step 4: Handle benefit/caution drugs
    print("\n[5/6] Handling drug columns...")

    # The last cells should have benefit_drugs and caution_drugs
    # Find where to add endfor (last cell of the row)

    # Find the last </w:tc> before </w:tr>
    last_cell_end = template_row.rfind('</w:tc>')
    if last_cell_end != -1:
        # Find the last <w:t> content in the last cell
        last_cell_start = template_row.rfind('<w:tc>', 0, last_cell_end)
        last_cell = template_row[last_cell_start:last_cell_end + len('</w:tc>')]

        # Check if there's content (--) to replace with caution_drugs
        if '<w:t>--</w:t>' in last_cell:
            new_last_cell = last_cell.replace(
                '<w:t>--</w:t>',
                '<w:t>{{ row.caution_drugs }}{% endfor %}</w:t>'
            )
            template_row = template_row[:last_cell_start] + new_last_cell + template_row[last_cell_end + len('</w:tc>'):]
        else:
            # Add endfor to the last text element
            # Find the last </w:t> in the last cell
            last_t_end = template_row.rfind('</w:t>')
            if last_t_end != -1:
                template_row = template_row[:last_t_end] + '{% endfor %}' + template_row[last_t_end:]

    # Also replace benefit_drugs (second to last cell)
    second_last_cell_end = template_row.rfind('</w:tc>', 0, last_cell_start if last_cell_start else -1)
    if second_last_cell_end != -1:
        second_last_cell_start = template_row.rfind('<w:tc>', 0, second_last_cell_end)
        second_last_cell = template_row[second_last_cell_start:second_last_cell_end + len('</w:tc>')]
        if '<w:t>--</w:t>' in second_last_cell:
            new_second_last_cell = second_last_cell.replace(
                '<w:t>--</w:t>',
                '<w:t>{{ row.benefit_drugs }}</w:t>'
            )
            template_row = template_row[:second_last_cell_start] + new_second_last_cell + template_row[second_last_cell_end + len('</w:tc>'):]

    # Step 5: Build new content
    print("\n[6/6] Building new document...")

    if setd2_row_start and setd2_row_end:
        # Remove TP53 row and SETD2 rows, insert template
        # But we need to check if there are continuation rows for TP53 too

        # Find where TP53 data ends (including its continuation rows)
        tp53_last_row_end = tp53_row_end
        pos = tp53_row_end
        while True:
            next_row_start = content.find('<w:tr', pos)
            if next_row_start == -1 or next_row_start >= setd2_row_start:
                break
            next_row_end = content.find('</w:tr>', next_row_start) + len('</w:tr>')
            row_content = content[next_row_start:next_row_end]
            if '<w:vMerge w:val="continue"/>' in row_content:
                tp53_last_row_end = next_row_end
                pos = next_row_end
            else:
                break

        # Build new content: before TP53 row + template row + after SETD2 rows
        new_content = content[:tp53_row_start] + template_row + content[setd2_row_end:]
        print(f"  ✓ Replaced TP53 row with template")
        print(f"  ✓ Removed all rows from TP53 continuation to SETD2 end")
    else:
        # Just replace TP53 row with template
        new_content = content[:tp53_row_start] + template_row + content[tp53_row_end:]
        print("  ✓ Replaced TP53 row with template")

    # Save
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    new_size = len(new_content)
    print(f"\n  Original size: {original_size:,} bytes")
    print(f"  New size: {new_size:,} bytes")
    print(f"  Removed: {original_size - new_size:,} bytes")

    print("\n" + "=" * 60)
    print("Summary table loop added!")
    print("=" * 60)

    # Verify the result
    print("\nVerification:")
    if '{% for row in summary_variants %}' in new_content:
        print("  ✓ Loop start marker found")
    else:
        print("  ✗ Loop start marker NOT found!")

    if new_content.count('{% endfor %}') >= 2:  # At least 2 endfor (main + summary)
        print("  ✓ Loop end marker found (multiple loops)")
    else:
        print("  ⚠ Only one endfor found")

    if 'SETD2' not in new_content:
        print("  ✓ SETD2 successfully removed from summary table")
    else:
        setd2_count = new_content.count('SETD2')
        print(f"  ⚠ SETD2 still found {setd2_count} time(s) in document")
        print("    (May be in diagnostic knowledge section - expected)")


if __name__ == "__main__":
    add_summary_table_loop()
