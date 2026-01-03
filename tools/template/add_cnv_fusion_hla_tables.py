#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在模板中添加CNV、Fusion、HLA三个表格
"""

from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def set_cell_background(cell, color_hex):
    """设置单元格背景色"""
    shading_elm = OxmlElement('w:shd')
    shading_elm.set(qn('w:fill'), color_hex)
    cell._element.get_or_add_tcPr().append(shading_elm)

def create_cnv_table(doc):
    """创建CNV拷贝数变异表格"""

    # 添加标题
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = title.add_run('拷贝数变异（CNV）检测结果')
    run.font.name = '微软雅黑'
    run.font.size = Pt(12)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0, 196, 216)

    # 创建表格：1行表头 + 3行Jinja2循环 = 4行，6列
    table = doc.add_table(rows=4, cols=6)
    table.style = 'Table Grid'
    table.autofit = False

    # 设置列宽
    col_widths = [Inches(1.2), Inches(0.8), Inches(1.0), Inches(1.0), Inches(1.0), Inches(1.0)]
    for i, width in enumerate(col_widths):
        for cell in table.columns[i].cells:
            cell.width = width

    # 表头
    headers = ['基因', '染色体', '起始位置', '终止位置', '状态', '拷贝数']
    header_row = table.rows[0]
    for i, header_text in enumerate(headers):
        cell = header_row.cells[i]
        set_cell_background(cell, '00C4D8')
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = para.add_run(header_text)
        run.font.name = '微软雅黑'
        run.font.size = Pt(11)
        run.font.bold = True
        run.font.color.rgb = RGBColor(249, 251, 250)

    # Jinja2循环
    table.rows[1].cells[0].paragraphs[0].text = '{% for row in cnv %}'

    # 数据行
    data_row = table.rows[2]
    columns_mapping = [
        '{{ row.Gene or "" }}',
        '{{ row.Chr or row["#Chr"] or "" }}',
        '{{ row.Start or "" }}',
        '{{ row.End or "" }}',
        '{{ row.Status or "" }}',
        '{{ row["CopyNum(X)"] or row.CopyNum or "" }}'
    ]
    for i, col_template in enumerate(columns_mapping):
        cell = data_row.cells[i]
        para = cell.paragraphs[0]
        para.text = col_template
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if para.runs:
            para.runs[0].font.name = '微软雅黑'
            para.runs[0].font.size = Pt(10)

    # 结束循环
    table.rows[3].cells[0].paragraphs[0].text = '{% endfor %}'

    doc.add_paragraph()  # 空行

def create_fusion_table(doc):
    """创建基因融合表格"""

    # 添加标题
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = title.add_run('基因融合（Fusion）检测结果')
    run.font.name = '微软雅黑'
    run.font.size = Pt(12)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0, 196, 216)

    # 创建表格：4行，8列
    table = doc.add_table(rows=4, cols=8)
    table.style = 'Table Grid'
    table.autofit = False

    # 设置列宽
    col_widths = [Inches(0.8), Inches(0.8), Inches(0.7), Inches(0.9), Inches(0.7), Inches(0.9), Inches(0.9), Inches(0.8)]
    for i, width in enumerate(col_widths):
        for cell in table.columns[i].cells:
            cell.width = width

    # 表头
    headers = ['基因1', '基因2', '染色体1', '断点1', '染色体2', '断点2', '频率', '类型']
    header_row = table.rows[0]
    for i, header_text in enumerate(headers):
        cell = header_row.cells[i]
        set_cell_background(cell, '00C4D8')
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = para.add_run(header_text)
        run.font.name = '微软雅黑'
        run.font.size = Pt(11)
        run.font.bold = True
        run.font.color.rgb = RGBColor(249, 251, 250)

    # Jinja2循环
    table.rows[1].cells[0].paragraphs[0].text = '{% for row in fusion %}'

    # 数据行
    data_row = table.rows[2]
    columns_mapping = [
        '{{ row.Gene1 or row.chr1 or "" }}',
        '{{ row.Gene2 or row.gene1 or "" }}',
        '{{ row.Chr1 or row.pos1 or "" }}',
        '{{ row.Break1 or row.annotation1 or "" }}',
        '{{ row.Chr2 or row.chr2 or "" }}',
        '{{ row.Break2 or row.pos2 or "" }}',
        '{{ row.FinalFreq or row.Freq1 or "" }}',
        '{{ row.Sv_type or row["#Est_Type"] or row.Est_Type or "" }}'
    ]
    for i, col_template in enumerate(columns_mapping):
        cell = data_row.cells[i]
        para = cell.paragraphs[0]
        para.text = col_template
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if para.runs:
            para.runs[0].font.name = '微软雅黑'
            para.runs[0].font.size = Pt(10)

    # 结束循环
    table.rows[3].cells[0].paragraphs[0].text = '{% endfor %}'

    doc.add_paragraph()  # 空行

def create_hla_table(doc):
    """创建HLA分型表格"""

    # 添加标题
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = title.add_run('HLA分型检测结果')
    run.font.name = '微软雅黑'
    run.font.size = Pt(12)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0, 196, 216)

    # 创建表格：4行，3列
    table = doc.add_table(rows=4, cols=3)
    table.style = 'Table Grid'
    table.autofit = False

    # 设置列宽
    col_widths = [Inches(1.5), Inches(2.5), Inches(2.5)]
    for i, width in enumerate(col_widths):
        for cell in table.columns[i].cells:
            cell.width = width

    # 表头
    headers = ['HLA位点', 'Type 1', 'Type 2']
    header_row = table.rows[0]
    for i, header_text in enumerate(headers):
        cell = header_row.cells[i]
        set_cell_background(cell, '00C4D8')
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = para.add_run(header_text)
        run.font.name = '微软雅黑'
        run.font.size = Pt(11)
        run.font.bold = True
        run.font.color.rgb = RGBColor(249, 251, 250)

    # Jinja2循环
    table.rows[1].cells[0].paragraphs[0].text = '{% for row in hla %}'

    # 数据行
    data_row = table.rows[2]
    columns_mapping = [
        '{{ row.Locus or row["HLA-A"] or "" }}',
        '{{ row.Type1 or row.HET or "" }}',
        '{{ row.Type2 or row.Allele2 or "" }}'
    ]
    for i, col_template in enumerate(columns_mapping):
        cell = data_row.cells[i]
        para = cell.paragraphs[0]
        para.text = col_template
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if para.runs:
            para.runs[0].font.name = '微软雅黑'
            para.runs[0].font.size = Pt(10)

    # 结束循环
    table.rows[3].cells[0].paragraphs[0].text = '{% endfor %}'

    doc.add_paragraph()  # 空行

def add_all_tables(template_path, output_path):
    """添加三个表格到模板"""

    print("=" * 80)
    print("🔧 添加CNV、Fusion、HLA表格到模板")
    print("=" * 80)
    print()

    # 加载模板
    print(f"📖 读取模板: {template_path}")
    doc = Document(template_path)
    print(f"✅ 原模板: {len(doc.paragraphs)}段落, {len(doc.tables)}表格")

    # 添加分节标记
    doc.add_page_break()
    p = doc.add_paragraph()
    run = p.add_run('=== CNV、Fusion、HLA检测结果（自动生成） ===')
    run.font.name = '微软雅黑'
    run.font.size = Pt(14)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0, 196, 216)
    doc.add_paragraph()

    # 添加三个表格
    print("\n🔧 添加表格...")
    print("  1/3: CNV（拷贝数变异）表格")
    create_cnv_table(doc)

    print("  2/3: Fusion（基因融合）表格")
    create_fusion_table(doc)

    print("  3/3: HLA（HLA分型）表格")
    create_hla_table(doc)

    # 保存
    print(f"\n💾 保存模板: {output_path}")
    doc.save(output_path)

    # 检查
    doc_check = Document(output_path)
    print(f"✅ 新模板: {len(doc_check.paragraphs)}段落, {len(doc_check.tables)}表格")
    print(f"   增加了 {len(doc_check.tables) - len(doc.tables) + 3} 个表格")

    print("\n" + "=" * 80)
    print("✅ 成功添加3个表格（CNV、Fusion、HLA）")
    print("=" * 80)

def main():
    template_path = 'templates/aligned_template_with_drugs.docx'
    output_path = 'templates/aligned_template_with_cnv_fusion_hla.docx'

    add_all_tables(template_path, output_path)

    print(f"\n💡 新模板已保存到: {output_path}")
    print("⚠️  注意: 表格添加在文档末尾")

if __name__ == '__main__':
    main()
