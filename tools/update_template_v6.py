#!/usr/bin/env python3
"""
更新模板变量 - 完整版

将所有硬编码的值替换为Jinja2变量
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def update_template_v6(input_docx: str, output_docx: str = None):
    """更新模板变量 - 完整版"""
    input_path = Path(input_docx)
    if output_docx is None:
        output_docx = input_path.parent / f"{input_path.stem}_v6{input_path.suffix}"

    unpack_script = '/home/afei/.claude/skills/docx/ooxml/scripts/unpack.py'
    pack_script = '/home/afei/.claude/skills/docx/ooxml/scripts/pack.py'

    with tempfile.TemporaryDirectory() as tmpdir:
        unpacked = Path(tmpdir) / 'unpacked'
        subprocess.run(['python3', unpack_script, str(input_path), str(unpacked)],
                      capture_output=True, check=True)

        doc_xml_path = unpacked / 'word' / 'document.xml'
        content = doc_xml_path.read_text(encoding='utf-8')

        changes = []

        # 1. 送检日期: 找到 2025 后面跟着 1121 的模式
        pattern = r'(<w:t>)2025(</w:t>[\s\S]*?</w:r>[\s\S]*?<w:r>[\s\S]*?<w:t>)1121(</w:t>)'
        match = re.search(pattern, content)
        if match:
            # 合并为单个变量，删除中间的 run
            old = match.group(0)
            new = f'{match.group(1)}{{{{ sample_date }}}}{match.group(3)}'
            # 但我们需要保留第一个 run 的结束和第二个 run 的开始
            # 更简单的方法：只替换两个 <w:t> 中的内容
            content = re.sub(r'(<w:t>)2025(</w:t>)', r'\g<1>{{ sample_date }}\g<2>', content, count=1)
            content = re.sub(r'(<w:t>)1121(</w:t>)', r'\g<1>\g<2>', content, count=1)  # 清空第二个
            changes.append('送检日期: 2025+1121 -> {{ sample_date }}')

        # 2. 报告日期: 找到 2025 后面跟着 1204 的模式
        content = re.sub(r'(<w:t>)2025(</w:t>)', r'\g<1>{{ report_date }}\g<2>', content, count=1)
        content = re.sub(r'(<w:t>)1204(</w:t>)', r'\g<1>\g<2>', content, count=1)
        changes.append('报告日期: 2025+1204 -> {{ report_date }}')

        # 3. 项目编码: LZ25 + 8792
        content = re.sub(r'(<w:t>)LZ25(</w:t>)', r'\g<1>{{ sample_id }}\g<2>', content, count=1)
        content = re.sub(r'(<w:t>)8792(</w:t>)', r'\g<1>\g<2>', content, count=1)
        changes.append('项目编码: LZ25+8792 -> {{ sample_id }}')

        # 4. 样本类型: 组织 (XML编码为 &#32452;&#32455;)
        # 第一个是在患者信息表中
        content = re.sub(
            r'(<w:t[^>]*>)(&#32452;&#32455;)(</w:t>)',
            r'\g<1>{{ sample_type }}\g<3>',
            content, count=1
        )
        changes.append('样本类型(1): 组织 -> {{ sample_type }}')

        # 5. 检测内容中的 组织 (第二个)
        content = re.sub(
            r'(<w:t[^>]*>)(&#32452;&#32455;)(</w:t>)',
            r'\g<1>{{ sample_type }}\g<3>',
            content, count=1
        )
        changes.append('样本类型(2): 组织 -> {{ sample_type }}')

        doc_xml_path.write_text(content, encoding='utf-8')

        subprocess.run(['python3', pack_script, str(unpacked), str(output_docx)],
                      capture_output=True, check=True)

        print("=" * 60)
        print("模板更新完成")
        print("=" * 60)
        for c in changes:
            print(f"✓ {c}")
        print(f"\n输出文件: {output_docx}")
        return str(output_docx)


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python update_template_v6.py <template.docx> [output.docx]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    update_template_v6(input_file, output_file)
