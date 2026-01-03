#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析额外表格

专门分析自动生成报告中的额外表格（表格29-61）
"""

from docx import Document


def analyze_extra_tables():
    """分析额外表格"""

    print("=" * 80)
    print("分析自动生成报告的额外表格")
    print("=" * 80)

    generated_file = "data/output/张三---结直肠癌358基因检测-MLB2509307001-终版.docx"
    gen_doc = Document(generated_file)

    # 参考报告有29个表格，所以表格29及以后是额外的
    extra_table_start = 29

    print(f"\n参考报告表格数: 29")
    print(f"自动生成报告表格数: {len(gen_doc.tables)}")
    print(f"额外表格数: {len(gen_doc.tables) - extra_table_start}")

    print(f"\n{'='*80}")
    print(f"【额外表格详情】")
    print(f"{'='*80}")

    for i in range(extra_table_start, len(gen_doc.tables)):
        table = gen_doc.tables[i]
        rows = len(table.rows)
        cols = len(table.columns)

        print(f"\n表格 {i} ({rows}行 × {cols}列):")

        # 显示所有内容（因为这些表格都很小）
        for row_idx in range(min(5, rows)):  # 最多显示5行
            row_data = []
            for cell in table.rows[row_idx].cells:
                text = cell.text.strip()
                if len(text) > 40:
                    text = text[:40] + "..."
                row_data.append(text)

            print(f"  Row {row_idx}: {row_data}")

    # 统计分类
    print(f"\n{'='*80}")
    print(f"【额外表格分类统计】")
    print(f"{'='*80}")

    # 分类计数
    variant_detail_tables = 0
    cnv_tables = 0
    fusion_tables = 0
    hla_tables = 0
    other_tables = 0

    for i in range(extra_table_start, len(gen_doc.tables)):
        table = gen_doc.tables[i]
        first_row = [cell.text.strip() for cell in table.rows[0].cells]

        # 判断表格类型
        if len(table.rows) == 1 and "基因" in first_row[0]:
            if "检测位点" in str(first_row):
                variant_detail_tables += 1
            elif "染色体" in str(first_row):
                cnv_tables += 1
        elif "基因1" in str(first_row) or "基因2" in str(first_row):
            fusion_tables += 1
        elif "HLA" in str(first_row) or "Type 1" in str(first_row):
            hla_tables += 1
        else:
            other_tables += 1

    print(f"\n表格类型统计:")
    print(f"  变异详情表 (单行表): {variant_detail_tables} 个")
    print(f"  CNV表: {cnv_tables} 个")
    print(f"  Fusion表: {fusion_tables} 个")
    print(f"  HLA表: {hla_tables} 个")
    print(f"  其他: {other_tables} 个")

    total_extra = variant_detail_tables + cnv_tables + fusion_tables + hla_tables + other_tables
    print(f"  总计: {total_extra} 个")

    # 分析原因
    print(f"\n{'='*80}")
    print(f"【原因分析】")
    print(f"{'='*80}")

    print(f"\n💡 这些额外表格的来源:")
    print(f"\n  1. 变异详情表 ({variant_detail_tables}个):")
    print(f"     - 这些是每个变异的详细信息表（单行表格）")
    print(f"     - 参考报告可能将这些信息合并到一个大表中")
    print(f"     - 当前生成逻辑: 每个变异生成一个单独的表格")

    print(f"\n  2. CNV表 ({cnv_tables}个):")
    print(f"     - 拷贝数变异表")
    print(f"     - 参考报告可能没有CNV数据或使用不同格式")

    print(f"\n  3. Fusion表 ({fusion_tables}个):")
    print(f"     - 基因融合表")
    print(f"     - 参考报告可能没有Fusion数据或使用不同格式")

    print(f"\n  4. HLA表 ({hla_tables}个):")
    print(f"     - HLA分型表")
    print(f"     - 参考报告可能没有HLA数据或使用不同格式")

    print(f"\n⚠️  问题:")
    print(f"  - 如果参考报告确实有这些数据（CNV/Fusion/HLA），")
    print(f"    则表格数量差异是正常的（数据来源不同）")
    print(f"  - 如果参考报告也有同样的数据但格式不同，")
    print(f"    可能需要调整生成模板以匹配参考格式")

    print(f"\n✅ 建议:")
    print(f"  1. 检查参考报告是否包含CNV/Fusion/HLA数据")
    print(f"  2. 如果有，对比其呈现格式")
    print(f"  3. 如果变异详情表需要合并，修改模板逻辑")

    print(f"\n{'='*80}")
    print(f"✅ 额外表格分析完成")
    print(f"{'='*80}")


if __name__ == "__main__":
    analyze_extra_tables()
