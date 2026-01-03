#!/usr/bin/env python3
"""
更新模板中的Jinja2变量

将硬编码的值替换为Jinja2变量
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def update_template(input_docx: str, output_docx: str = None):
    """更新模板变量"""
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

        # 替换规则
        replacements = [
            # 送检日期: 2025 + 1121 -> {{ sample_date }}
            (r'(<w:t>)2025(</w:t>.*?<w:t>)1121(</w:t>)',
             r'\g<1>{{ sample_date }}\g<3>',
             '送检日期'),

            # 报告日期: 2025 + 1204 -> {{ report_date }}
            (r'(<w:t>)2025(</w:t>.*?<w:t>)1204(</w:t>)',
             r'\g<1>{{ report_date }}\g<3>',
             '报告日期'),
        ]

        for pattern, replacement, name in replacements:
            if re.search(pattern, content, re.DOTALL):
                content = re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)
                print(f'✓ 已替换: {name}')
            else:
                print(f'✗ 未找到: {name}')

        # 查找并替换其他硬编码值
        # 样本类型: 组织
        sample_type_pattern = r'(<w:t[^>]*>)(&#32452;&#32455;|组织)(</w:t>)'
        if re.search(sample_type_pattern, content):
            # 只替换患者信息表中的（第一个匹配）
            content = re.sub(sample_type_pattern, r'\g<1>{{ sample_type }}\g<3>', content, count=1)
            print('✓ 已替换: 样本类型 (第1个)')

        # 项目编码: LZ258792 (可能被拆分)
        project_code_pattern = r'(<w:t[^>]*>)LZ25(\d+)(</w:t>)'
        match = re.search(project_code_pattern, content)
        if match:
            # 可能是 LZ25 + 8792 拆分
            full_pattern = r'(<w:t[^>]*>)LZ25(</w:t>.*?<w:t[^>]*>)(\d+)(</w:t>)'
            if re.search(full_pattern, content, re.DOTALL):
                content = re.sub(full_pattern, r'\g<1>{{ sample_id }}\g<4>', content, count=1, flags=re.DOTALL)
                print('✓ 已替换: 项目编码 (拆分)')
            else:
                content = re.sub(project_code_pattern, r'\g<1>{{ sample_id }}\g<3>', content, count=1)
                print('✓ 已替换: 项目编码')

        doc_xml_path.write_text(content, encoding='utf-8')

        subprocess.run(['python3', pack_script, str(unpacked), str(output_docx)],
                      capture_output=True, check=True)

        print(f'\n模板已更新: {output_docx}')
        return str(output_docx)


def analyze_template(input_docx: str):
    """分析模板中的硬编码值"""
    unpack_script = '/home/afei/.claude/skills/docx/ooxml/scripts/unpack.py'

    with tempfile.TemporaryDirectory() as tmpdir:
        unpacked = Path(tmpdir) / 'unpacked'
        subprocess.run(['python3', unpack_script, str(input_docx), str(unpacked)],
                      capture_output=True, check=True)

        doc_xml_path = unpacked / 'word' / 'document.xml'
        content = doc_xml_path.read_text(encoding='utf-8')

        # 提取所有 <w:t> 内容
        t_elements = re.findall(r'<w:t[^>]*>([^<]*)</w:t>', content)

        print("=" * 60)
        print("模板中的文本元素分析")
        print("=" * 60)

        # 查找可能需要变量化的内容
        patterns_to_check = [
            (r'^\d{8}$', '日期格式 (YYYYMMDD)'),
            (r'^LZ\d+$', '项目编码'),
            (r'^20\d{2}$', '年份'),
            (r'^\d{4}$', '月日 (MMDD)'),
            (r'^组织|血液|石蜡$', '样本类型'),
            (r'^结直肠癌|肺癌|胃癌', '癌症类型'),
        ]

        for i, text in enumerate(t_elements):
            text = text.strip()
            if not text:
                continue
            for pattern, desc in patterns_to_check:
                if re.match(pattern, text):
                    print(f'[{i}] {desc}: "{text}"')
                    break


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python update_template_variables.py <template.docx> [output.docx]")
        print("  python update_template_variables.py --analyze <template.docx>")
        sys.exit(1)

    if sys.argv[1] == '--analyze':
        analyze_template(sys.argv[2])
    else:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        update_template(input_file, output_file)
