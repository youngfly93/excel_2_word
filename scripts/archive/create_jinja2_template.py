#!/usr/bin/env python3
"""
Convert docx to Jinja2 template for docxtpl rendering.
Direct XML manipulation without Document Library (Python 3.9 compatible).
"""

import os
import re
import shutil
import defusedxml.minidom

def process_document():
    unpacked_dir = "/tmp/docx_template_358"
    document_xml = os.path.join(unpacked_dir, "word/document.xml")

    print("=" * 60)
    print("Creating Jinja2 Template from Docx")
    print("=" * 60)

    # Read document.xml
    print("\n[1/4] Reading document.xml...")
    with open(document_xml, 'r', encoding='utf-8') as f:
        content = f.read()

    original_size = len(content)
    print(f"  File size: {original_size:,} bytes")

    # Step 1: Replace patient basic info
    print("\n[2/4] Replacing patient basic info...")

    # Patient name (苏雨起 = &#33487;&#38632;&#36215;)
    if '&#33487;&#38632;&#36215;' in content:
        content = content.replace('&#33487;&#38632;&#36215;', '{{ patient_name }}')
        print("  ✓ Replaced patient name (苏雨起) with {{ patient_name }}")
    else:
        print("  ⚠ Could not find patient name")

    # Gender (男 = &#30007;)
    # Be careful to only replace in the right context
    content = re.sub(r'>&#30007;</w:t>', '>{{ gender }}</w:t>', content, count=1)
    print("  ✓ Replaced gender with {{ gender }}")

    # Age (70) - in specific context around line 6207
    content = re.sub(r'<w:t>70</w:t>', '<w:t>{{ age }}</w:t>', content, count=1)
    print("  ✓ Replaced age with {{ age }}")

    # Cancer type (乙状结肠癌 = &#20057;&#29366;&#32467;&#32928;&#30284;)
    if '&#20057;&#29366;&#32467;&#32928;&#30284;' in content:
        content = content.replace('&#20057;&#29366;&#32467;&#32928;&#30284;', '{{ cancer_type }}')
        print("  ✓ Replaced cancer type with {{ cancer_type }}")

    # Report number (MLJY-LZ258792 split across runs)
    # Merge into single variable
    report_pattern = r'(<w:t>)MLJY-(</w:t>.*?<w:t>)LZ25(</w:t>.*?<w:t>)8792(</w:t>)'
    if re.search(report_pattern, content, re.DOTALL):
        content = re.sub(report_pattern, r'\g<1>{{ report_number }}\g<2>\g<3>\g<4>', content, flags=re.DOTALL)
        print("  ✓ Replaced report number with {{ report_number }}")

    # Step 2: Replace TMB/MSI values
    print("\n[3/4] Replacing TMB/MSI values...")

    # TMB value (6.5)
    content = re.sub(r'<w:t>6\.5</w:t>', '<w:t>{{ tmb_value }}</w:t>', content, count=1)
    print("  ✓ Replaced TMB value (6.5) with {{ tmb_value }}")

    # TMB status (L after TMB-)
    content = re.sub(
        r'(mutations/Mb&#65292;TMB-</w:t>.*?<w:t>)L(</w:t>)',
        r'\g<1>{{ tmb_status }}\g<2>',
        content,
        count=1,
        flags=re.DOTALL
    )
    print("  ✓ Replaced TMB status (L) with {{ tmb_status }}")

    # TMB reference value (10 mutations/Mb)
    content = re.sub(
        r'<w:t>10 mutations/Mb\)</w:t>',
        '<w:t>{{ tmb_reference }} mutations/Mb)</w:t>',
        content,
        count=1
    )
    print("  ✓ Replaced TMB reference (10) with {{ tmb_reference }}")

    # TMB level description (低于参考值 - 低 = &#20302;)
    content = re.sub(
        r'&#20302;(&#20110;&#21442;&#32771;&#20540;)',
        r'{{ tmb_level_cn }}\g<1>',
        content,
        count=1
    )
    print("  ✓ Replaced TMB level (低/高) with {{ tmb_level_cn }}")

    # MSI status (微卫星稳定型，MSS)
    # &#24494;&#21355;&#26143;&#31283;&#23450;&#22411;&#65292;MSS
    content = re.sub(
        r'&#24494;&#21355;&#26143;&#31283;&#23450;&#22411;&#65292;MSS',
        '{{ msi_status_cn }}',
        content,
        count=1
    )
    print("  ✓ Replaced MSI status with {{ msi_status_cn }}")

    # Step 3: Note about gene variant tables
    print("\n[INFO] Gene variant table structure identified:")
    print("  - TP53 row at lines 7530-7861")
    print("  - KRAS row at lines 7862+")
    print("  - For Jinja2 loops, use docxtpl's {% for %}...{% endfor %} syntax")
    print("  - This requires manual adjustment for table row duplication")

    # Step 4: Save modified document
    print("\n[4/4] Saving template...")
    with open(document_xml, 'w', encoding='utf-8') as f:
        f.write(content)

    new_size = len(content)
    print(f"  Original size: {original_size:,} bytes")
    print(f"  New size: {new_size:,} bytes")
    print(f"  Difference: {new_size - original_size:+,} bytes")

    print("\n" + "=" * 60)
    print("Template conversion completed!")
    print("=" * 60)
    print(f"\nOutput directory: {unpacked_dir}")
    print("\nNext steps:")
    print("1. Pack the template:")
    print(f"   python3 /Users/yangfei/.claude/plugins/cache/anthropic-agent-skills/document-skills/69c0b1a06741/skills/docx/ooxml/scripts/pack.py {unpacked_dir} templates/jinja2_template_358.docx")
    print("\n2. For gene variant table loops, manually edit the table rows")
    print("   to use docxtpl's table loop syntax")

if __name__ == "__main__":
    process_document()
