#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在模板文件中添加33个化疗药物详细解析表
"""

from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import json
import re

def sanitize_drug_name(drug_name):
    """将药物名称转换为有效的Jinja2变量名"""
    name_mapping = {
        "顺铂": "shunbo", "卡铂": "kabo", "奥沙利铂": "aoshalibo",
        "铂类化合物": "boleihuahewu", "甲氨蝶呤": "jiaandieling",
        "紫杉醇": "zishanchun", "环磷酰胺": "huanlinyanan",
        "异环磷酰胺": "yihuanlinyanan", "伊立替康": "yilitikang",
        "依托泊苷": "yituopogan", "达卡巴嗪": "dakabazuo",
        "蒽环类": "genhuanlei", "博来霉素": "bolaimeisin",
        "卡培他滨": "kaipeibaibin", "5-Fu、氟嘧啶类": "fluorouracil",
        "吉西他滨": "jixitabin", "多西他赛": "duoxitasai",
        "培美曲塞": "peimeiqusai", "长春碱类": "changchunjianlei",
        "米托蒽醌": "mituogenquan", "三胺硫磷": "sananliulin",
        "马法兰": "mafalan", "替加氟/替吉奥": "tegafur",
        "阿糖胞苷": "atangbaoyin", "来曲唑/阿那曲唑": "letrozole_anastrozole",
        "地塞米松": "disaimisong", "强的松": "qiangdesong",
        "他莫昔芬": "tamoxifen", "依西美坦": "yiximeitang",
        "伊达比星": "yidabixing",
    }
    if drug_name in name_mapping:
        return f"drug_{name_mapping[drug_name]}"
    return f"drug_{re.sub(r'[^a-zA-Z0-9]+', '_', drug_name).strip('_').lower()}"

def create_drug_detail_table(doc, drug_name, drug_var_name):
    """创建单个药物详细解析表"""

    # 添加标题段落
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = title.add_run(f'表格{drug_name}：{drug_name}详细解析')
    run.font.name = '微软雅黑'
    run.font.size = Pt(10.5)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0, 196, 216)  # #00C4D8

    # 创建表格：1行表头 + 3行(for循环结构) = 4行，6列
    table = doc.add_table(rows=4, cols=6)
    table.style = 'Table Grid'

    # 设置表格属性
    table.autofit = False
    table.allow_autofit = False

    # 设置列宽（根据手工报告的6列表格）
    col_widths = [Inches(1.0), Inches(1.2), Inches(1.0), Inches(0.8), Inches(2.0), Inches(1.5)]
    for i, width in enumerate(col_widths):
        for cell in table.columns[i].cells:
            cell.width = width

    # 第一行：表头
    headers = ['基因', '检测位点', '基因型', '等级', '检测结果', '参考文献']
    header_row = table.rows[0]
    for i, header_text in enumerate(headers):
        cell = header_row.cells[i]
        # 设置单元格背景色
        shading_elm = OxmlElement('w:shd')
        shading_elm.set(qn('w:fill'), '00C4D8')
        cell._element.get_or_add_tcPr().append(shading_elm)

        # 设置文字
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = para.add_run(header_text)
        run.font.name = '微软雅黑'
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.color.rgb = RGBColor(249, 251, 250)  # #F9FBFA

    # 第二行：{% for row in drug_xxx %}
    cell = table.rows[1].cells[0]
    para = cell.paragraphs[0]
    para.text = f'{{% for row in {drug_var_name} %}}'

    # 第三行：数据行模板
    data_row = table.rows[2]
    columns_mapping = [
        '{{ row.检测基因 or row.Gene or "" }}',
        '{{ row.检测位点 or row.Locus or "" }}',
        '{{ row.基因型 or row.Genotype or "" }}',
        '{{ row.等级 or row.Level or "" }}',
        '{{ row.用药提示 or row.检测结果 or row.Result or "" }}',
        '{{ row.参考文献 or row.Reference or "" }}'
    ]
    for i, col_template in enumerate(columns_mapping):
        cell = data_row.cells[i]
        para = cell.paragraphs[0]
        para.text = col_template
        run = para.runs[0] if para.runs else para.add_run()
        run.font.name = '微软雅黑'
        run.font.size = Pt(10.5)

    # 第四行：{% endfor %}
    cell = table.rows[3].cells[0]
    para = cell.paragraphs[0]
    para.text = '{% endfor %}'

    # 添加空行
    doc.add_paragraph()

def add_all_drug_tables(template_path, output_path, drug_mapping_file):
    """在模板中添加所有药物详细表格"""

    # 读取药物映射信息
    with open(drug_mapping_file, 'r', encoding='utf-8') as f:
        mapping_data = json.load(f)

    # 加载模板
    print(f"📖 读取模板: {template_path}")
    doc = Document(template_path)
    print(f"✅ 原模板: {len(doc.paragraphs)}段落, {len(doc.tables)}表格")

    # 找到表格5的位置（索引4）
    table5_index = 4

    # 统计需要添加的药物表格
    drugs_to_add = []
    for drug_info in mapping_data['mapping']:
        if drug_info['match_found']:
            drug_name = drug_info['report_drug']
            # 生成变量名：使用规范化函数
            var_name = sanitize_drug_name(drug_name)
            drugs_to_add.append({
                'name': drug_name,
                'var_name': var_name,
                'table_index': drug_info['report_table']
            })

    print(f"\n🔧 将添加 {len(drugs_to_add)} 个药物详细表格...")

    # 由于python-docx不支持在指定位置插入表格
    # 我们需要在文档末尾添加，然后手动移动XML节点
    # 或者重新生成整个文档
    # 这里我们采用在末尾添加的方式，后续可以手动调整位置

    # 添加一个分节标记
    doc.add_page_break()
    p = doc.add_paragraph()
    run = p.add_run('=== 化疗药物详细解析表（自动生成） ===')
    run.font.name = '微软雅黑'
    run.font.size = Pt(14)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0, 196, 216)

    # 添加每个药物的详细表格
    for i, drug in enumerate(drugs_to_add, 1):
        print(f"  {i}/{len(drugs_to_add)}: {drug['name']} -> {drug['var_name']}")
        create_drug_detail_table(doc, drug['name'], drug['var_name'])

    # 保存修改后的模板
    print(f"\n💾 保存模板: {output_path}")
    doc.save(output_path)

    # 重新读取检查
    doc_check = Document(output_path)
    print(f"✅ 新模板: {len(doc_check.paragraphs)}段落, {len(doc_check.tables)}表格")
    print(f"   增加了 {len(doc_check.tables) - len(doc.tables) + len(drugs_to_add)} 个表格")

    return drugs_to_add

def main():
    template_path = 'templates/aligned_template_final.docx'
    output_path = 'templates/aligned_template_with_drugs.docx'
    drug_mapping_file = 'drug_mapping_analysis.json'

    print("=" * 80)
    print("🔧 添加化疗药物详细解析表到模板")
    print("=" * 80)
    print()

    drugs_added = add_all_drug_tables(template_path, output_path, drug_mapping_file)

    print("\n" + "=" * 80)
    print(f"✅ 成功添加 {len(drugs_added)} 个药物详细表格")
    print("=" * 80)
    print("\n📋 添加的药物列表:")
    for drug in drugs_added:
        print(f"  - {drug['name']} ({drug['var_name']})")

    print(f"\n💡 新模板已保存到: {output_path}")
    print("⚠️  注意: 表格添加在文档末尾，可能需要手动调整位置")

if __name__ == '__main__':
    main()
