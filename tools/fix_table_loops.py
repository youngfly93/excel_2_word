#!/usr/bin/env python3
"""
修复模板中的表格循环结构

将错误的单元格内循环改为行级别循环
并删除硬编码的行
"""

import re
import subprocess
import tempfile
from pathlib import Path


def fix_table_loops(input_docx: str, output_docx: str = None):
    """修复表格循环结构"""
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

        # 1. 修复第一个表格的循环 (靶向药物相关体细胞变异用药提示)
        # 查找 "{% for row in variants %}{{ row.gene }}" 并替换为 "{%tr for row in variants %}{{ row.gene }}"
        old_loop_start = "{% for row in variants %}{{ row.gene }}"
        new_loop_start = "{%tr for row in variants %}{{ row.gene }}"
        if old_loop_start in content:
            content = content.replace(old_loop_start, new_loop_start, 1)
            changes.append('variants表: 修复循环开始标签 -> {%tr for row in variants %}')

        # 替换 "{% endfor %}" 为 "{%tr endfor %}" (第一个匹配)
        old_loop_end = "{{ row.caution_drugs }}{% endfor %}"
        new_loop_end = "{{ row.caution_drugs }}{%tr endfor %}"
        if old_loop_end in content:
            content = content.replace(old_loop_end, new_loop_end, 1)
            changes.append('variants表: 修复循环结束标签 -> {%tr endfor %}')

        # 2. 修复第二个表格的循环 (summary_variants)
        old_summary_start = "{% for row in summary_variants %}{{ row.gene }}"
        new_summary_start = "{%tr for row in summary_variants %}{{ row.gene }}"
        if old_summary_start in content:
            content = content.replace(old_summary_start, new_summary_start, 1)
            changes.append('summary_variants表: 修复循环开始标签')

        # 3. 修复 undetected_genes 表格的循环
        old_undetected_start = "{% for gene in undetected_genes %}{{ gene.name }}"
        new_undetected_start = "{%tr for gene in undetected_genes %}{{ gene.name }}"
        if old_undetected_start in content:
            content = content.replace(old_undetected_start, new_undetected_start, 1)
            changes.append('undetected_genes表: 修复循环开始标签')

        # 3.1 修复 summary_variants 和 undetected_genes 的 endfor 标签
        # 这些 {% endfor %} 在行级别(在 </w:tc> 之后)，需要替换为 {%tr endfor %}
        # 使用正则表达式查找并替换
        old_row_endfor = r'(</w:tc>\s*\n?\s*){% endfor %}'
        new_row_endfor = r'\g<1>{%tr endfor %}'
        content, count = re.subn(old_row_endfor, new_row_endfor, content)
        if count > 0:
            changes.append(f'修复行级endfor标签: {count}处')

        # 4-5. 删除硬编码的表格行 (SETD2, ATM)
        # 使用正确的方法: 找到所有表格行，检查每行是否包含目标文本
        def find_and_delete_row(xml_content, target_text, description):
            """找到包含target_text的表格行并删除"""
            # 找到所有 <w:tr...> 行起始位置
            tr_start_pattern = r'<w:tr(?:\s+[^>]*)?>'
            tr_starts = [m.start() for m in re.finditer(tr_start_pattern, xml_content)]

            target_marker = f'<w:t>{target_text}</w:t>'
            target_pos = xml_content.find(target_marker)

            if target_pos == -1:
                return xml_content, False

            # 找到包含目标的行
            for start in tr_starts:
                end = xml_content.find('</w:tr>', start)
                if end == -1:
                    continue
                end += len('</w:tr>')

                if start < target_pos < end:
                    row_content = xml_content[start:end]
                    # 确保这不是包含模板循环的行
                    if 'for row in' in row_content or '{%tr' in row_content:
                        print(f"  警告: {description} 行包含循环模板，跳过删除")
                        return xml_content, False

                    # 删除这一行
                    return xml_content[:start] + xml_content[end:], True

            return xml_content, False

        # 删除 SETD2 行
        content, deleted = find_and_delete_row(content, 'SETD2', 'SETD2')
        if deleted:
            changes.append('删除硬编码的SETD2表格行')

        # 删除 ATM 行 (只删除表格中的第一个，不删除基因知识部分的)
        content, deleted = find_and_delete_row(content, 'ATM', 'ATM')
        if deleted:
            changes.append('删除硬编码的ATM表格行')

        # 保存修改
        doc_xml_path.write_text(content, encoding='utf-8')

        subprocess.run(['python3', pack_script, str(unpacked), str(output_docx)],
                      capture_output=True, check=True)

        print("=" * 60)
        print("表格循环修复完成")
        print("=" * 60)
        for c in changes:
            print(f"✓ {c}")
        print(f"\n输出文件: {output_docx}")

        # 输出警告
        print("\n" + "=" * 60)
        print("重要提示")
        print("=" * 60)
        print("1. 基因诊疗知识部分(第三部分)仍需手动处理")
        print("2. 免疫相关基因表格也需要添加循环")
        print("3. 建议在Word中打开检查并手动调整格式")

        return str(output_docx)


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python fix_table_loops.py <template.docx> [output.docx]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    fix_table_loops(input_file, output_file)
