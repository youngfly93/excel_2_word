#!/usr/bin/env python3
"""
升级模板从 v15 到 v16
将硬编码的8个基因知识块替换为 Jinja2 动态渲染

主要变更:
1. 移除8个硬编码基因块 (TP53, KRAS, APC x2, SETD2, EPHA2, FANCI, ATM)
2. 添加 {% for section in gene_knowledge_sections %} 循环
3. 使用动态变量: section.header, section.intro, section.mutation_desc, section.mutation_analysis
"""

import zipfile
import os
import re
import shutil
from pathlib import Path


def create_gene_knowledge_loop_xml():
    """
    创建基因知识块的 Jinja2 循环模板

    结构:
    - Header: 基因名:突变信息;频率 (红色或蓝色, 粗体, 下划线)
    - 基因简介标题 + 内容
    - 基因变异说明标题 + 内容
    - 基因变异解析标题 + 内容
    """

    # Jinja2 for循环 - 使用段落级别的循环标记 {%p}
    # {%p for ...%} 会让循环包含这个段落及其后续所有段落直到 {%p endfor %}
    loop_start_para = '''<w:p w14:paraId="GENEKNOW00"><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:t>{%p for section in gene_knowledge_sections %}</w:t></w:r></w:p>'''
    loop_end_para = '''<w:p w14:paraId="GENEKNOW99"><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:t>{%p endfor %}</w:t></w:r></w:p>'''

    # 基于实际模板格式构建XML段落
    # 使用 RichText 方式需要在代码中处理，这里使用简单文本替换

    # Header段落 - 使用动态颜色
    header_para = '''<w:p w14:paraId="GENEKNOW01"><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:rPr><w:rFonts w:hint="eastAsia" w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:cs="微软雅黑"/><w:b/><w:color w:val="{{ section.header_color }}"/><w:sz w:val="24"/><w:u w:val="single"/></w:rPr><w:t>{{ section.header }}</w:t></w:r></w:p>'''

    # 基因简介标题
    intro_title = '''<w:p w14:paraId="GENEKNOW02"><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:cs="微软雅黑"/><w:b/></w:rPr><w:t>基因简介：</w:t></w:r></w:p>'''

    # 基因简介内容
    intro_content = '''<w:p w14:paraId="GENEKNOW03"><w:pPr><w:spacing w:after="0"/><w:ind w:firstLine="400"/><w:jc w:val="both"/><w:rPr><w:rFonts w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:cs="微软雅黑"/><w:sz w:val="21"/></w:rPr></w:pPr><w:r><w:rPr><w:rFonts w:hint="eastAsia" w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:cs="微软雅黑"/><w:sz w:val="21"/></w:rPr><w:t>{{ section.intro }}</w:t></w:r></w:p>'''

    # 基因变异说明标题
    mutation_desc_title = '''<w:p w14:paraId="GENEKNOW04"><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:cs="微软雅黑"/><w:b/></w:rPr><w:t>基因变异说明：</w:t></w:r></w:p>'''

    # 基因变异说明内容
    mutation_desc_content = '''<w:p w14:paraId="GENEKNOW05"><w:pPr><w:spacing w:after="0"/><w:ind w:firstLine="400"/><w:jc w:val="both"/><w:rPr><w:rFonts w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:cs="微软雅黑"/><w:sz w:val="21"/></w:rPr></w:pPr><w:r><w:rPr><w:rFonts w:hint="eastAsia" w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:cs="微软雅黑"/><w:sz w:val="21"/></w:rPr><w:t>{{ section.mutation_desc }}</w:t></w:r></w:p>'''

    # 基因变异解析标题
    mutation_analysis_title = '''<w:p w14:paraId="GENEKNOW06"><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:cs="微软雅黑"/><w:b/></w:rPr><w:t>基因变异解析：</w:t></w:r></w:p>'''

    # 基因变异解析内容
    mutation_analysis_content = '''<w:p w14:paraId="GENEKNOW07"><w:pPr><w:spacing w:after="0"/><w:ind w:firstLine="400"/><w:jc w:val="both"/><w:rPr><w:rFonts w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:cs="微软雅黑"/><w:sz w:val="21"/></w:rPr></w:pPr><w:r><w:rPr><w:rFonts w:hint="eastAsia" w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:cs="微软雅黑"/><w:sz w:val="21"/></w:rPr><w:t>{{ section.mutation_analysis }}</w:t></w:r></w:p>'''

    # 组合所有段落
    full_template = (
        loop_start_para +
        header_para +
        intro_title +
        intro_content +
        mutation_desc_title +
        mutation_desc_content +
        mutation_analysis_title +
        mutation_analysis_content +
        loop_end_para
    )

    return full_template


def find_gene_blocks_range(content: str) -> tuple:
    """
    找到8个硬编码基因块的起始和结束位置

    Returns:
        (start_pos, end_pos) - 需要替换的范围
    """
    # 找到所有"基因简介"位置
    intro_matches = list(re.finditer(r'基因简介', content))
    if len(intro_matches) != 8:
        raise ValueError(f"Expected 8 '基因简介' occurrences, found {len(intro_matches)}")

    # 第一个基因块的开始 - TP53 header之前
    first_intro_pos = intro_matches[0].start()
    # 往前找到header段落的开始
    intro_p_start = content.rfind('<w:p ', max(0, first_intro_pos-500), first_intro_pos)
    prev_p_end = content.rfind('</w:p>', max(0, intro_p_start-2000), intro_p_start)
    first_block_start = content.rfind('<w:p ', max(0, prev_p_end-2000), prev_p_end)

    # 找到最后一个基因块(ATM)的结束
    # ATM的基因变异解析后面的内容是"潜在获益靶向/免疫药物解析"
    last_intro_pos = intro_matches[-1].start()  # ATM的基因简介位置

    # 从ATM位置往后找"基因变异解析"
    atm_analysis_pos = content.find('基因变异解析', last_intro_pos)

    # 找到ATM解析内容段落的结束
    # 遍历段落直到找到"潜在获益"或药物相关内容
    search_pos = atm_analysis_pos
    last_gene_p_end = None

    for _ in range(10):
        p_start = content.find('<w:p ', search_pos)
        if p_start == -1:
            break
        p_end = content.find('</w:p>', p_start)
        texts = re.findall(r'<w:t[^>]*>([^<]+)</w:t>', content[p_start:p_end])
        text = ''.join(texts)

        # 检查是否到达药物分析部分
        if '潜在获益' in text or '靶向/免疫药物' in text or 'AZD1775' in text:
            # 上一个段落是基因块的结束
            break

        # 空段落也可能是分隔
        last_gene_p_end = p_end + 6  # +6 for </w:p>
        search_pos = p_end + 7

    if last_gene_p_end is None:
        raise ValueError("Could not find the end of gene knowledge blocks")

    return first_block_start, last_gene_p_end


def upgrade_template(input_path: str, output_path: str):
    """
    升级模板从 v15 到 v16
    """
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")

    # 创建临时工作目录
    work_dir = Path('/tmp/template_v16_work')
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

    print("Finding gene knowledge blocks...")
    try:
        start_pos, end_pos = find_gene_blocks_range(content)
        print(f"  Block range: {start_pos} - {end_pos}")
        print(f"  Block size: {end_pos - start_pos} characters")
    except ValueError as e:
        print(f"Error: {e}")
        return False

    # 提取被替换区域的一些内容用于验证
    old_content = content[start_pos:end_pos]
    gene_count = old_content.count('基因简介')
    print(f"  Verified: Found {gene_count} '基因简介' in block")

    # 创建新的 Jinja2 循环模板
    print("Creating Jinja2 loop template...")
    new_loop = create_gene_knowledge_loop_xml()

    # 替换内容
    print("Replacing content...")
    new_content = content[:start_pos] + new_loop + content[end_pos:]

    # 验证替换
    new_gene_count = new_content.count('基因简介')
    print(f"  After replacement: {new_gene_count} '基因简介' (should be 1 in template)")

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

    parser = argparse.ArgumentParser(description='Upgrade template from v15 to v16')
    parser.add_argument('--input', '-i',
                       default='templates/jinja2_template_358_v15.docx',
                       help='Input template path')
    parser.add_argument('--output', '-o',
                       default='templates/jinja2_template_358_v16.docx',
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
