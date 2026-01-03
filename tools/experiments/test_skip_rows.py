#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试skip_rows功能

验证CNV和Fusion sheet是否正确跳过第一行空行
"""

import sys
from reportgen.core.excel_reader import ExcelReader

def test_skip_rows(excel_file="data/input/MLF2509307001T_MLB2509307001.result.xlsx"):
    """测试skip_rows功能"""

    print("=" * 80)
    print("测试skip_rows功能")
    print("=" * 80)

    # 创建ExcelReader（会自动加载skip_rows配置）
    reader = ExcelReader(config_dir="config")

    print(f"\n✅ skip_rows配置加载结果:")
    for sheet, skip_count in reader.skip_rows_config.items():
        print(f"   {sheet}: skip {skip_count} rows")

    # 读取Excel文件
    print(f"\n📂 读取Excel文件: {excel_file}")
    excel_data = reader.read(excel_file)

    print(f"\n✅ Excel读取成功")
    print(f"   文件: {excel_data.file_path}")
    print(f"   Sheet数量: {len(excel_data.sheet_names)}")

    # 验证CNV Sheet
    print(f"\n【验证CNV Sheet】")
    cnv_data = excel_data.get_table_data("Cnv")
    if cnv_data:
        print(f"✅ CNV数据读取成功")
        print(f"   数据行数: {len(cnv_data)}")
        if cnv_data:
            print(f"   列名: {list(cnv_data[0].keys())[:5]}...")  # 只显示前5列

            # 检查是否跳过了空行（第一行数据应该是表头或真实数据）
            first_row = cnv_data[0]
            gene_col = first_row.get('Gene') or first_row.get('#Chr')
            if gene_col:
                print(f"   第一行Gene/#Chr值: {gene_col}")
                if gene_col == "Gene" or str(gene_col).startswith("#"):
                    print(f"   ⚠️  第一行可能是表头，skip_rows可能未生效")
                else:
                    print(f"   ✅ 第一行是数据行，skip_rows生效")
        else:
            print(f"   ℹ️  CNV数据为空（可能样本无CNV）")
    else:
        print(f"❌ CNV数据未找到")

    # 验证Fusion Sheet
    print(f"\n【验证Fusion Sheet】")
    fusion_data = excel_data.get_table_data("Fusion")
    if fusion_data:
        print(f"✅ Fusion数据读取成功")
        print(f"   数据行数: {len(fusion_data)}")
        if fusion_data:
            print(f"   列名: {list(fusion_data[0].keys())[:5]}...")  # 只显示前5列

            # 检查是否跳过了空行
            first_row = fusion_data[0]
            gene1 = first_row.get('Gene1') or first_row.get('#Est_Type')
            if gene1:
                print(f"   第一行Gene1/#Est_Type值: {gene1}")
                if gene1 == "Gene1" or str(gene1).startswith("#"):
                    print(f"   ⚠️  第一行可能是表头，skip_rows可能未生效")
                else:
                    print(f"   ✅ 第一行是数据行，skip_rows生效")
        else:
            print(f"   ℹ️  Fusion数据为空（可能样本无Fusion）")
    else:
        print(f"❌ Fusion数据未找到")

    # 验证HLA Sheet（不应该跳过行）
    print(f"\n【验证HLA Sheet】")
    hla_data = excel_data.get_table_data("HLA")
    if hla_data:
        print(f"✅ HLA数据读取成功")
        print(f"   数据行数: {len(hla_data)}")
        if hla_data:
            print(f"   列名: {list(hla_data[0].keys())[:3]}...")
            # 显示前3行数据（用于验证HLA格式）
            for i, row in enumerate(hla_data[:3]):
                print(f"   Row {i+1}: {list(row.values())[:3]}...")
    else:
        print(f"❌ HLA数据未找到")

    print("\n" + "=" * 80)
    print("✅ skip_rows功能测试完成")
    print("=" * 80)


if __name__ == "__main__":
    excel_file = sys.argv[1] if len(sys.argv) > 1 else "data/input/MLF2509307001T_MLB2509307001.result.xlsx"
    test_skip_rows(excel_file)
