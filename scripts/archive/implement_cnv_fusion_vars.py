#!/usr/bin/env python3
"""
Implement Jinja2 variables for CNV/Fusion detection table results.

This script replaces the static 未检出 results with Jinja2 variables
while preserving the complex table structure with vertical merges.

Python 3.9 compatible.
"""

import re


def implement_cnv_fusion_vars():
    doc_path = "/tmp/docx_template_358/word/document.xml"

    print("=" * 60)
    print("Implementing CNV/Fusion Detection Table Variables")
    print("=" * 60)

    # Read the document
    print("\n[1/5] Reading document.xml...")
    with open(doc_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_length = len(content)
    print(f"  Document length: {original_length:,} characters")

    # Unicode entities:
    # 未检出 = &#26410;&#26816;&#20986;
    # 融合 = &#34701;&#21512;
    # 扩增 = &#25193;&#22686;
    # 突变 = &#31361;&#21464;
    # 外显子 = &#22806;&#26174;&#23376;

    print("\n[2/5] Finding CNV/Fusion table region...")

    # Find the table by locating ALK in the CNV section (around char 2.7M)
    # The table starts around line 15700

    # Strategy: Find each gene and its detection type, then replace the
    # following 未检出 in the same row

    # Gene/detection pairs with their variable names
    # Order matters - we'll process them in sequence
    gene_mappings = [
        # (gene_pattern, detection_pattern, variable_name)
        # Simple genes with single detection type
        (r'<w:t>ALK</w:t>', r'&#34701;&#21512;', 'cnv_ALK_fusion'),
        (r'<w:t>ROS1</w:t>', r'&#34701;&#21512;', 'cnv_ROS1_fusion'),
        (r'<w:t>RET</w:t>', r'&#34701;&#21512;', 'cnv_RET_fusion'),
    ]

    print("\n[3/5] Locating table boundaries...")

    # Find ALK in the CNV table area (after position 2.5M)
    alk_pattern = r'<w:t>ALK</w:t>'
    alk_matches = list(re.finditer(alk_pattern, content))

    table_start = None
    for match in alk_matches:
        if match.start() > 2500000:  # After 2.5M characters
            table_start = match.start()
            break

    if table_start is None:
        print("  ERROR: Could not find CNV/Fusion table")
        return

    # Find table end - look for closing of table after ~20K chars
    # Table ends around line 17500, which is ~30K chars from start
    table_end = table_start + 50000
    print(f"  Table region: {table_start:,} to {table_end:,}")

    print("\n[4/5] Replacing result values with variables...")

    # Work on table region
    before_table = content[:table_start]
    table_region = content[table_start:table_end]
    after_table = content[table_end:]

    # Pattern for 未检出 in a result cell
    weijianchu_pattern = r'<w:t>&#26410;&#26816;&#20986;</w:t>'

    # Count before
    count_before = len(re.findall(weijianchu_pattern, table_region))
    print(f"  Found {count_before} result cells (未检出) in table region")

    # Find row boundaries
    rows = list(re.finditer(r'<w:tr[^>]*>(.*?)</w:tr>', table_region, re.DOTALL))
    print(f"  Found {len(rows)} table rows in region")

    # Track replacements
    replacements = []

    # Process each row and create variable mappings
    # We need to identify each gene/detection combo and replace the result

    # Define all gene/detection/variable mappings
    full_mappings = [
        # Gene regex, Detection regex, Variable name
        ('ALK', '&#34701;&#21512;', 'cnv_ALK_fusion'),
        ('ROS1', '&#34701;&#21512;', 'cnv_ROS1_fusion'),
        ('RET', '&#34701;&#21512;', 'cnv_RET_fusion'),
        ('ERBB2', '&#31361;&#21464;', 'cnv_ERBB2_mutation'),
        ('ERBB2', '&#25193;&#22686;', 'cnv_ERBB2_amplification'),
        ('PIK3CA', '&#22806;&#26174;&#23376;10', 'cnv_PIK3CA_exon10'),
        ('PIK3CA', '&#22806;&#26174;&#23376;21', 'cnv_PIK3CA_exon21'),
        ('MET', '&#22806;&#26174;&#23376;14&#36339;&#36291;', 'cnv_MET_exon14skip'),
        ('MET', '&#25193;&#22686;', 'cnv_MET_amplification'),
        ('NRAS', '&#22806;&#26174;&#23376;2<', 'cnv_NRAS_exon2'),  # Note: < to distinguish from exon 21
        ('NRAS', '&#22806;&#26174;&#23376;3<', 'cnv_NRAS_exon3'),
        ('NRAS', '&#22806;&#26174;&#23376;4<', 'cnv_NRAS_exon4'),
        ('KRAS', '&#22806;&#26174;&#23376;2<', 'cnv_KRAS_exon2'),
        ('KRAS', '&#22806;&#26174;&#23376;3<', 'cnv_KRAS_exon3'),
        ('KRAS', '&#22806;&#26174;&#23376;4<', 'cnv_KRAS_exon4'),
        ('BRAF', '&#22806;&#26174;&#23376;11', 'cnv_BRAF_exon11'),
        ('BRAF', '&#22806;&#26174;&#23376;15', 'cnv_BRAF_exon15'),
    ]

    # Process: For each row, check which gene/detection it matches
    # then replace the 未检出 with the appropriate variable

    modified_table = table_region
    current_gene = None

    for row_match in rows:
        row_content = row_match.group(0)
        row_start = row_match.start()
        row_end = row_match.end()

        # Check for gene name in this row
        gene_match = re.search(r'<w:t>([A-Z][A-Z0-9]+)</w:t>', row_content)
        if gene_match:
            potential_gene = gene_match.group(1)
            # Check if it's a known CNV gene
            if potential_gene in ['ALK', 'ROS1', 'RET', 'ERBB2', 'PIK3CA', 'MET', 'NRAS', 'KRAS', 'BRAF', 'NTRK1', 'NTRK2', 'NTRK3']:
                current_gene = potential_gene

        # Skip if no current gene context
        if not current_gene:
            continue

        # Check for detection type in this row
        detection_type = None
        var_name = None

        for gene, detection, var in full_mappings:
            if gene == current_gene and detection in row_content:
                detection_type = detection
                var_name = var
                break

        # If we found a match and row has 未检出, replace it
        if var_name and weijianchu_pattern.replace('&#26410;&#26816;&#20986;', '') in row_content:
            if '&#26410;&#26816;&#20986;' in row_content:
                # Create replacement for this specific row
                new_row = row_content.replace(
                    '<w:t>&#26410;&#26816;&#20986;</w:t>',
                    f'<w:t>{{{{ {var_name} }}}}</w:t>'
                )
                # Update table region
                modified_table = (
                    modified_table[:row_start] +
                    new_row +
                    modified_table[row_end:]
                )
                replacements.append(var_name)
                print(f"    Replaced: {current_gene}/{detection_type[:10]}... -> {var_name}")

    # Simpler approach: just replace ALL 未检出 with a generic variable
    # since the complex row matching is error-prone

    print("\n  Using simplified replacement approach...")

    # Reset modified_table
    modified_table = table_region

    # Replace first N occurrences sequentially
    replacement_vars = [
        'cnv_ALK_fusion',
        'cnv_ROS1_fusion',
        'cnv_RET_fusion',
        'cnv_ERBB2_mutation',
        'cnv_ERBB2_amplification',
        'cnv_PIK3CA_exon10',
        'cnv_PIK3CA_exon21',
        'cnv_MET_exon14skip',
        'cnv_MET_amplification',
        'cnv_NRAS_exon2',
        'cnv_NRAS_exon3',
        'cnv_NRAS_exon4',
        'cnv_KRAS_exon2',
        'cnv_KRAS_exon3',
        'cnv_KRAS_exon4',
        'cnv_BRAF_exon11',
        'cnv_BRAF_exon15',
    ]

    # Find all 未检出 positions
    weijianchu_full = '<w:t>&#26410;&#26816;&#20986;</w:t>'
    positions = []
    pos = 0
    while True:
        pos = modified_table.find(weijianchu_full, pos)
        if pos == -1:
            break
        positions.append(pos)
        pos += 1

    print(f"  Found {len(positions)} 未检出 instances in table region")

    # Replace from end to start to preserve positions
    positions.reverse()
    for i, pos in enumerate(positions):
        if i < len(replacement_vars):
            var_name = replacement_vars[len(positions) - 1 - i]
            replacement = f'<w:t>{{{{ {var_name} }}}}</w:t>'
            modified_table = (
                modified_table[:pos] +
                replacement +
                modified_table[pos + len(weijianchu_full):]
            )
            print(f"    Replaced position {pos} with {var_name}")

    print(f"\n  Total replacements: {min(len(positions), len(replacement_vars))}")

    print("\n[5/5] Saving modified document...")

    # Reconstruct document
    new_content = before_table + modified_table + after_table

    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"  Document saved")
    print(f"  New length: {len(new_content):,} characters")

    # Verification
    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)

    # Check for variables
    for var in replacement_vars[:5]:  # Check first 5
        if f'{{{{ {var} }}}}' in new_content:
            print(f"  ✓ {var} found")
        else:
            print(f"  ✗ {var} NOT found")

    print("\n" + "=" * 60)
    print("CNV/Fusion variables implementation complete!")
    print("=" * 60)


if __name__ == "__main__":
    implement_cnv_fusion_vars()
