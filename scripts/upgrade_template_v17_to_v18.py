#!/usr/bin/env python3
"""
升级模板从 v17 到 v18
将硬编码的参考文献列表替换为 Jinja2 动态渲染

主要变更:
1. 移除硬编码的 68 条参考文献
2. 添加 Jinja2 for 循环，使用 numbered_references 变量
"""

import zipfile
import os
import re
import shutil
from pathlib import Path


def create_references_loop_xml():
    """
    创建参考文献部分的 Jinja2 循环模板

    结构:
    - for循环遍历 numbered_references
    - 每条参考文献显示: 编号. 文本
    """

    # Jinja2 for 循环开始
    loop_start = '''<w:p w14:paraId=\"REFLOOP01\"><w:pPr><w:spacing w:after=\"0\"/></w:pPr><w:r><w:t>{%p for ref in numbered_references %}</w:t></w:r></w:p>'''

    # 参考文献内容段落
    # 格式: {{ ref.number }}. {{ ref.text }}
    ref_content = '''<w:p w14:paraId=\"REFLOOP02\"><w:pPr><w:spacing w:after=\"0\"/><w:rPr><w:rFonts w:ascii=\"微软雅黑\" w:hAnsi=\"微软雅黑\" w:cs=\"微软雅黑\"/><w:sz w:val=\"21\"/></w:rPr></w:pPr><w:r><w:rPr><w:rFonts w:hint=\"eastAsia\" w:ascii=\"微软雅黑\" w:hAnsi=\"微软雅黑\" w:cs=\"微软雅黑\"/><w:sz w:val=\"21\"/></w:rPr><w:t>{{ ref.number }}. {{ ref.text }}</w:t></w:r></w:p>'''

    # 循环结束
    loop_end = '''<w:p w14:paraId=\"REFLOOP03\"><w:pPr><w:spacing w:after=\"0\"/></w:pPr><w:r><w:t>{%p endfor %}</w:t></w:r></w:p>'''

    return loop_start + ref_content + loop_end


def find_references_range(content: str) -> tuple:
    """
    找到参考文献列表的起始和结束位置

    Returns:
        (start_pos, end_pos) - 需要替换的范围
    """
    # 找到 '5. 参考文献' 标题
    main_ref_pos = content.find('5. 参考文献')
    if main_ref_pos == -1:
        # 尝试其他格式
        main_ref_pos = content.find('5.参考文献')
    if main_ref_pos == -1:
        main_ref_pos = content.find('5、参考文献')

    if main_ref_pos == -1:
        raise ValueError("Could not find '5. 参考文献' title in template")

    print(f"  找到参考文献标题位置: {main_ref_pos}")

    # 从标题位置开始搜索第一个 PMID
    search_start = main_ref_pos
    first_pmid_match = re.search(r'PMID[:\s]*\d+', content[search_start:search_start+10000])
    if not first_pmid_match:
        raise ValueError("Could not find first PMID after reference title")

    first_pmid_pos = search_start + first_pmid_match.start()
    print(f"  第一个 PMID 位置: {first_pmid_pos}")

    # 找到包含第一个 PMID 的段落开始
    p_start = content.rfind('<w:p ', first_pmid_pos - 2000, first_pmid_pos)
    if p_start == -1:
        raise ValueError("Could not find paragraph start for first reference")

    # 找到所有 PMID，确定最后一个的位置
    pmid_matches = list(re.finditer(r'PMID[:\s]*\d+', content[search_start:]))
    if not pmid_matches:
        raise ValueError("Could not find any PMID in reference section")

    last_pmid_match = pmid_matches[-1]
    last_pmid_pos = search_start + last_pmid_match.end()
    print(f"  最后一个 PMID 结束位置: {last_pmid_pos}")

    # 找到包含最后一个 PMID 的段落结束
    last_p_end = content.find('</w:p>', last_pmid_pos)
    if last_p_end == -1:
        raise ValueError("Could not find paragraph end for last reference")
    last_p_end += 6  # 包含 </w:p>

    return p_start, last_p_end


def upgrade_template(input_path: str, output_path: str):
    """
    升级模板从 v17 到 v18
    """
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")

    # 创建临时工作目录
    work_dir = Path('/tmp/template_v18_work')
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    # 解压模板
    print("Extracting template...")
    with zipfile.ZipFile(input_path, 'r') as zf:
        zf.extractall(work_dir)

    # 读取 document.xml
    doc_xml_path = work_dir / 'word' / 'document.xml'
    with open(doc_xml_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print("Finding reference list blocks...")
    try:
        start_pos, end_pos = find_references_range(content)
        print(f"  Block range: {start_pos} - {end_pos}")
        print(f"  Block size: {end_pos - start_pos} characters")
    except ValueError as e:
        print(f"Error: {e}")
        return False

    # 验证：检查区域内的 PMID 数量
    old_content = content[start_pos:end_pos]
    pmid_count = len(re.findall(r'PMID[:\s]*\d+', old_content))
    print(f"  Verified: Found {pmid_count} PMIDs in block")

    # 创建新的 Jinja2 循环模板
    print("Creating Jinja2 loop template...")
    new_loop = create_references_loop_xml()

    # 替换内容
    print("Replacing content...")
    new_content = content[:start_pos] + new_loop + content[end_pos:]

    # 验证替换
    new_pmid_count = len(re.findall(r'PMID[:\s]*\d+', new_content))
    print(f"  After replacement: {new_pmid_count} PMIDs (should be 0 in template)")

    # 检查 Jinja2 变量
    jinja_vars = re.findall(r'\{\{\s*ref\.\w+\s*\}\}', new_content)
    print(f"  Jinja2 variables added: {jinja_vars}")

    # 保存修改后的 document.xml
    with open(doc_xml_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    # 重新打包为 docx
    print("Repacking docx...")
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(work_dir):
            for file in files:
                file_path = Path(root) / file
                arc_name = file_path.relative_to(work_dir)
                zf.write(file_path, arc_name)

    print(f"Successfully created: {output_path}")

    # 清理
    shutil.rmtree(work_dir)

    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Upgrade template from v17 to v18')
    parser.add_argument('--input', '-i',
                       default='templates/jinja2_template_358_v17.docx',
                       help='Input template path')
    parser.add_argument('--output', '-o',
                       default='templates/jinja2_template_358_v18.docx',
                       help='Output template path')

    args = parser.parse_args()

    # 转换为绝对路径
    base_dir = Path(__file__).parent.parent
    input_path = base_dir / args.input
    output_path = base_dir / args.output

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return 1

    success = upgrade_template(str(input_path), str(output_path))
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
