#!/usr/bin/env python3
"""
Add Jinja2 loop for undetected genes (未见突变基因列表).

This script:
1. Removes extra variant gene rows (EPHA2, FANCI, ATM) - they're in summary_variants data
2. Creates a loop for undetected genes starting with BRAF
3. Uses BRAF row as template for undetected_genes loop
4. Removes all other undetected gene rows

Current structure (after summary_variants loop):
- EPHA2: lines 11973-12354 (has variant - should be in summary_variants)
- FANCI: lines 12355-12766 (has variant - should be in summary_variants)
- ATM: lines 12767-13598 (has variant - should be in summary_variants)
- BRAF: lines 13599-13985 (未见突变 - template for undetected_genes)
- More 未见突变 genes follow...

Python 3.9 compatible.
"""

import re


def add_undetected_genes_loop():
    doc_path = "/tmp/docx_template_358/word/document.xml"

    print("=" * 60)
    print("Adding Undetected Genes Loop (未见突变基因列表)")
    print("=" * 60)

    # Read the document
    print("\n[1/7] Reading document.xml...")
    with open(doc_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    original_line_count = len(lines)
    print(f"  Total lines: {original_line_count:,}")

    # Step 1: Verify structure
    print("\n[2/7] Verifying document structure...")

    # Find EPHA2 (should be removed)
    epha2_line = None
    for i, line in enumerate(lines):
        if '<w:t>EPHA2</w:t>' in line:
            epha2_line = i + 1  # 1-indexed
            break

    if epha2_line:
        print(f"  EPHA2 at line {epha2_line}")
    else:
        print("  EPHA2 not found (may already be removed)")

    # Find BRAF (template for undetected genes)
    braf_line = None
    for i, line in enumerate(lines):
        if '<w:t>BRAF</w:t>' in line and i > 13000:  # After summary table area
            braf_line = i + 1  # 1-indexed
            break

    if braf_line:
        print(f"  BRAF at line {braf_line}")
    else:
        print("  ERROR: BRAF not found")
        return

    # Find 未见突变 instances
    weijian_count = 0
    for line in lines:
        if '&#26410;&#35265;&#31361;&#21464;' in line or '未见突变' in line:
            weijian_count += 1
    print(f"  Found {weijian_count} genes with 未见突变")

    # Step 2: Find exact row boundaries
    print("\n[3/7] Finding row boundaries...")

    # Find row starts and ends
    rows_info = []
    row_start = None
    for i, line in enumerate(lines):
        if '<w:tr ' in line or '<w:tr>' in line:
            row_start = i
        if '</w:tr>' in line and row_start is not None:
            row_end = i
            # Check what gene is in this row
            row_content = ''.join(lines[row_start:row_end+1])
            gene_match = re.search(r'<w:t>([A-Z][A-Z0-9]+)</w:t>', row_content)
            if gene_match:
                gene = gene_match.group(1)
                if gene not in ['NM', 'CS', 'NS', 'CI', 'RI', 'OR']:  # Skip common non-gene patterns
                    has_weijian = '&#26410;&#35265;&#31361;&#21464;' in row_content or '未见突变' in row_content
                    rows_info.append({
                        'gene': gene,
                        'start': row_start,
                        'end': row_end,
                        'has_weijian': has_weijian
                    })
            row_start = None

    # Filter to relevant rows (after summary loop, around lines 11900+)
    relevant_rows = [r for r in rows_info if r['start'] > 11900 and r['start'] < 25000]

    # Find EPHA2, FANCI, ATM rows (to remove)
    variant_rows = [r for r in relevant_rows if r['gene'] in ['EPHA2', 'FANCI', 'ATM']]
    print(f"  Variant rows to remove: {[r['gene'] for r in variant_rows]}")

    # Find undetected genes (with 未见突变)
    undetected_rows = [r for r in relevant_rows if r['has_weijian']]
    print(f"  Undetected gene rows: {len(undetected_rows)}")
    if undetected_rows:
        print(f"    First: {undetected_rows[0]['gene']} (lines {undetected_rows[0]['start']+1}-{undetected_rows[0]['end']+1})")
        print(f"    Last: {undetected_rows[-1]['gene']} (lines {undetected_rows[-1]['start']+1}-{undetected_rows[-1]['end']+1})")

    if not undetected_rows:
        print("  ERROR: No undetected gene rows found")
        return

    # Step 3: Extract BRAF row as template
    print("\n[4/7] Creating template from first undetected gene (BRAF)...")
    first_undetected = undetected_rows[0]
    template_row_lines = lines[first_undetected['start']:first_undetected['end']+1]
    template_row = ''.join(template_row_lines)

    # Step 4: Add loop markers to template
    print("\n[5/7] Adding Jinja2 loop markers...")

    # Replace gene name with loop start
    template_row = re.sub(
        r'<w:t>BRAF</w:t>',
        '<w:t>{% for gene in undetected_genes %}{{ gene.name }}</w:t>',
        template_row,
        count=1
    )

    # Replace transcript
    template_row = re.sub(
        r'<w:t>NM_\d+\.\d+</w:t>',
        '<w:t>{{ gene.transcript }}</w:t>',
        template_row,
        count=1
    )

    # Replace chromosome
    template_row = re.sub(
        r'(<w:t>)(\d{1,2})(</w:t>)',
        r'\1{{ gene.chromosome }}\3',
        template_row,
        count=1
    )

    # 未见突变 should stay as-is or be a variable
    # For simplicity, keep it as-is since all undetected genes show the same text

    # Add endfor at the end
    template_row = template_row.rstrip()
    if template_row.endswith('</w:tr>'):
        template_row = template_row[:-len('</w:tr>')] + '{% endfor %}</w:tr>\n'

    print("  Template variables:")
    print("    - {% for gene in undetected_genes %}")
    print("    - {{ gene.name }}")
    print("    - {{ gene.transcript }}")
    print("    - {{ gene.chromosome }}")
    print("    - {% endfor %}")

    # Step 5: Calculate what to remove
    print("\n[6/7] Calculating rows to remove...")

    # Rows to remove:
    # 1. Variant rows (EPHA2, FANCI, ATM)
    # 2. All undetected rows except first (which is template)

    remove_ranges = []

    # Add variant rows
    for r in variant_rows:
        remove_ranges.append((r['start'], r['end']))
        print(f"  Remove {r['gene']}: lines {r['start']+1}-{r['end']+1}")

    # Add undetected rows (except first)
    for r in undetected_rows[1:]:
        remove_ranges.append((r['start'], r['end']))

    print(f"  Remove {len(undetected_rows)-1} undetected gene rows after BRAF")

    # Sort ranges by start position (descending) to remove from end first
    remove_ranges.sort(key=lambda x: x[0], reverse=True)

    # Step 6: Build new document
    print("\n[7/7] Building new document...")

    new_lines = lines.copy()

    # Replace first undetected row with template
    first_start = first_undetected['start']
    first_end = first_undetected['end']
    template_lines = template_row.split('\n')
    # Preserve newlines
    template_lines = [l + '\n' if not l.endswith('\n') and l else l for l in template_lines]

    # Remove ranges (from end to start to preserve indices)
    for start, end in remove_ranges:
        if start >= first_start and end <= first_end:
            continue  # Don't remove the template row
        del new_lines[start:end+1]

    # Now find where template row is and replace it
    # Need to recalculate after deletions
    # Find BRAF row again
    template_start = None
    for i, line in enumerate(new_lines):
        if '<w:t>BRAF</w:t>' in line:
            # Find row start
            for j in range(i, -1, -1):
                if '<w:tr ' in new_lines[j] or '<w:tr>' in new_lines[j]:
                    template_start = j
                    break
            break

    if template_start is not None:
        # Find row end
        for i in range(template_start, len(new_lines)):
            if '</w:tr>' in new_lines[i]:
                template_end = i
                break

        # Replace with template
        new_lines = new_lines[:template_start] + template_lines + new_lines[template_end+1:]

    new_content = ''.join(new_lines)

    print(f"  Original lines: {original_line_count:,}")
    print(f"  New lines: {len(new_lines):,}")
    print(f"  Removed: {original_line_count - len(new_lines):,} lines")

    # Save
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("  ✓ Document saved")

    # Verification
    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)

    if '{% for gene in undetected_genes %}' in new_content:
        print("  ✓ Undetected genes loop start marker found")
    else:
        print("  ✗ Undetected genes loop start marker NOT found!")

    endfor_count = new_content.count('{% endfor %}')
    print(f"  Found {endfor_count} endfor markers")

    # Check removed genes
    for gene in ['EPHA2', 'FANCI', 'ATM']:
        # Check only in the table area
        if f'<w:t>{gene}</w:t>' not in new_content[400000:700000]:
            print(f"  ✓ {gene} removed from table area")
        else:
            print(f"  ⚠ {gene} may still be in table area")

    print("\n" + "=" * 60)
    print("Undetected genes loop completed!")
    print("=" * 60)


if __name__ == "__main__":
    add_undetected_genes_loop()
