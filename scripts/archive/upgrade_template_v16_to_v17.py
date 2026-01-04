#!/usr/bin/env python3
"""
升级模板从 v16 到 v17
将硬编码的药物解析部分替换为 Jinja2 动态渲染

主要变更:
1. 移除硬编码的"潜在获益靶向/免疫药物解析"部分（约8个药物块）
2. 移除硬编码的"潜在负相关靶向/免疫药物解析"部分（约2个药物块）
3. 添加 Jinja2 for 循环，使用 drug_analysis_sections 变量
"""

import zipfile
import os
import re
import shutil
from pathlib import Path


def create_drug_analysis_loop_xml():
    """
    创建药物解析部分的 Jinja2 循环模板

    结构:
    1. 潜在获益靶向/免疫药物解析标题
    2. for循环遍历benefit类型药物
    3. 潜在负相关靶向/免疫药物解析标题
    4. for循环遍历caution类型药物
    """

    # 获益药物标题段落
    benefit_title = '''<w:p w14:paraId="DRUGANA01"><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:rPr><w:rFonts w:hint="eastAsia" w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:cs="微软雅黑"/><w:b/><w:sz w:val="24"/></w:rPr><w:t>潜在获益靶向/免疫药物解析</w:t></w:r></w:p>'''

    # 获益药物循环开始
    benefit_loop_start = '''<w:p w14:paraId="DRUGANA02"><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:t>{%p for drug in drug_analysis_sections %}</w:t></w:r></w:p>'''

    # 获益药物条件判断
    benefit_if_start = '''<w:p w14:paraId="DRUGANA03"><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:t>{%p if drug.drug_type == "benefit" %}</w:t></w:r></w:p>'''

    # 药物标题行（红色加粗）
    drug_header = '''<w:p w14:paraId="DRUGANA04"><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:rPr><w:rFonts w:hint="eastAsia" w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:cs="微软雅黑"/><w:b/><w:color w:val="FF0000"/><w:sz w:val="24"/></w:rPr><w:t>{{ drug.header }}</w:t></w:r></w:p>'''

    # 药物名称
    drug_name = '''<w:p w14:paraId="DRUGANA05"><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:rPr><w:rFonts w:hint="eastAsia" w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:cs="微软雅黑"/><w:b/><w:sz w:val="21"/></w:rPr><w:t>{{ drug.drug_name }}</w:t></w:r></w:p>'''

    # 基因变异与药物关联分析标题
    relation_title = '''<w:p w14:paraId="DRUGANA06"><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:cs="微软雅黑"/><w:b/></w:rPr><w:t>基因变异与药物关联分析：</w:t></w:r></w:p>'''

    # 关联分析内容
    relation_content = '''<w:p w14:paraId="DRUGANA07"><w:pPr><w:spacing w:after="0"/><w:ind w:firstLine="400"/><w:jc w:val="both"/><w:rPr><w:rFonts w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:cs="微软雅黑"/><w:sz w:val="21"/></w:rPr></w:pPr><w:r><w:rPr><w:rFonts w:hint="eastAsia" w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:cs="微软雅黑"/><w:sz w:val="21"/></w:rPr><w:t>{{ drug.relation }}</w:t></w:r></w:p>'''

    # 药物疗效临床解析标题
    clinical_title = '''<w:p w14:paraId="DRUGANA08"><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:cs="微软雅黑"/><w:b/></w:rPr><w:t>药物疗效临床解析：</w:t></w:r></w:p>'''

    # 临床解析内容
    clinical_content = '''<w:p w14:paraId="DRUGANA09"><w:pPr><w:spacing w:after="0"/><w:ind w:firstLine="400"/><w:jc w:val="both"/><w:rPr><w:rFonts w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:cs="微软雅黑"/><w:sz w:val="21"/></w:rPr></w:pPr><w:r><w:rPr><w:rFonts w:hint="eastAsia" w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:cs="微软雅黑"/><w:sz w:val="21"/></w:rPr><w:t>{{ drug.clinical }}</w:t></w:r></w:p>'''

    # 条件判断结束
    benefit_if_end = '''<w:p w14:paraId="DRUGANA10"><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:t>{%p endif %}</w:t></w:r></w:p>'''

    # 循环结束
    benefit_loop_end = '''<w:p w14:paraId="DRUGANA11"><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:t>{%p endfor %}</w:t></w:r></w:p>'''

    # 空行分隔
    empty_para = '''<w:p w14:paraId="DRUGANA12"><w:pPr><w:spacing w:after="0"/></w:pPr></w:p>'''

    # 慎用药物标题段落
    caution_title = '''<w:p w14:paraId="DRUGANA13"><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:rPr><w:rFonts w:hint="eastAsia" w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:cs="微软雅黑"/><w:b/><w:sz w:val="24"/></w:rPr><w:t>潜在负相关靶向/免疫药物解析</w:t></w:r></w:p>'''

    # 慎用药物循环开始
    caution_loop_start = '''<w:p w14:paraId="DRUGANA14"><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:t>{%p for drug in drug_analysis_sections %}</w:t></w:r></w:p>'''

    # 慎用药物条件判断
    caution_if_start = '''<w:p w14:paraId="DRUGANA15"><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:t>{%p if drug.drug_type == "caution" %}</w:t></w:r></w:p>'''

    # 慎用药物标题行（蓝色加粗）
    caution_drug_header = '''<w:p w14:paraId="DRUGANA16"><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:rPr><w:rFonts w:hint="eastAsia" w:ascii="微软雅黑" w:hAnsi="微软雅黑" w:cs="微软雅黑"/><w:b/><w:color w:val="0000FF"/><w:sz w:val="24"/></w:rPr><w:t>{{ drug.header }}</w:t></w:r></w:p>'''

    # 条件判断结束
    caution_if_end = '''<w:p w14:paraId="DRUGANA17"><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:t>{%p endif %}</w:t></w:r></w:p>'''

    # 循环结束
    caution_loop_end = '''<w:p w14:paraId="DRUGANA18"><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:t>{%p endfor %}</w:t></w:r></w:p>'''

    # 组合完整模板
    full_template = (
        # 获益药物部分
        benefit_title +
        benefit_loop_start +
        benefit_if_start +
        drug_header +
        drug_name +
        relation_title +
        relation_content +
        clinical_title +
        clinical_content +
        benefit_if_end +
        benefit_loop_end +
        empty_para +
        # 慎用药物部分
        caution_title +
        caution_loop_start +
        caution_if_start +
        caution_drug_header +
        drug_name.replace('DRUGANA05', 'DRUGANA19') +
        relation_title.replace('DRUGANA06', 'DRUGANA20') +
        relation_content.replace('DRUGANA07', 'DRUGANA21') +
        clinical_title.replace('DRUGANA08', 'DRUGANA22') +
        clinical_content.replace('DRUGANA09', 'DRUGANA23') +
        caution_if_end +
        caution_loop_end
    )

    return full_template


def find_drug_analysis_range(content: str) -> tuple:
    """
    找到药物解析部分的起始和结束位置

    Returns:
        (start_pos, end_pos) - 需要替换的范围
    """
    # 找到"潜在获益靶向/免疫药物解析"标题
    # 注意：这个标题在文档中出现多次，我们需要找到解析部分的那个
    # 解析部分在"AZD1775"药物之前

    # 方法：找到第一个"AZD1775"，然后往前找"潜在获益靶向"
    azd_match = re.search(r'AZD1775', content)
    if not azd_match:
        raise ValueError("Could not find 'AZD1775' in template")

    first_azd = azd_match.start()

    # 在AZD1775之前找"潜在获益靶向"
    before_azd = content[:first_azd]
    benefit_pos = before_azd.rfind('潜在获益靶向')
    if benefit_pos == -1:
        raise ValueError("Could not find '潜在获益靶向' before AZD1775")

    # 找到包含"潜在获益靶向"的段落开始
    p_start = content.rfind('<w:p ', max(0, benefit_pos - 500), benefit_pos)
    if p_start == -1:
        raise ValueError("Could not find paragraph start for benefit title")

    start_pos = p_start

    # 找到最后一个"药物疗效临床解析"的内容段落结束
    clinical_matches = list(re.finditer(r'药物疗效临床解析', content))
    if not clinical_matches:
        raise ValueError("Could not find '药物疗效临床解析' in template")

    last_clinical = clinical_matches[-1].end()

    # 找到这个段落结束，然后找下一个内容段落结束
    clinical_p_end = content.find('</w:p>', last_clinical)
    next_p_start = content.find('<w:p ', clinical_p_end)
    next_p_end = content.find('</w:p>', next_p_start)

    end_pos = next_p_end + 6  # +6 for </w:p>

    return start_pos, end_pos


def upgrade_template(input_path: str, output_path: str):
    """
    升级模板从 v16 到 v17
    """
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")

    # 创建临时工作目录
    work_dir = Path('/tmp/template_v17_work')
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

    print("Finding drug analysis blocks...")
    try:
        start_pos, end_pos = find_drug_analysis_range(content)
        print(f"  Block range: {start_pos} - {end_pos}")
        print(f"  Block size: {end_pos - start_pos} characters")
    except ValueError as e:
        print(f"Error: {e}")
        return False

    # 验证：检查区域内的药物关联分析数量
    old_content = content[start_pos:end_pos]
    relation_count = old_content.count('基因变异与药物关联分析')
    print(f"  Verified: Found {relation_count} '基因变异与药物关联分析' in block")

    # 创建新的 Jinja2 循环模板
    print("Creating Jinja2 loop template...")
    new_loop = create_drug_analysis_loop_xml()

    # 替换内容
    print("Replacing content...")
    new_content = content[:start_pos] + new_loop + content[end_pos:]

    # 验证替换
    new_relation_count = new_content.count('基因变异与药物关联分析')
    print(f"  After replacement: {new_relation_count} '基因变异与药物关联分析' (should be 2 in template)")

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

    parser = argparse.ArgumentParser(description='Upgrade template from v16 to v17')
    parser.add_argument('--input', '-i',
                       default='templates/jinja2_template_358_v16.docx',
                       help='Input template path')
    parser.add_argument('--output', '-o',
                       default='templates/jinja2_template_358_v17.docx',
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
