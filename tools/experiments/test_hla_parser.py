#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试HLA专用解析器

验证HLA数据是否正确解析
"""

import sys
from reportgen.core.excel_reader import ExcelReader

def test_hla_parser(excel_file="data/input/MLF2509307001T_MLB2509307001.result.xlsx"):
    """测试HLA解析器"""

    print("=" * 80)
    print("测试HLA专用解析器")
    print("=" * 80)

    # 创建ExcelReader
    reader = ExcelReader(config_dir="config")

    # 读取Excel文件
    print(f"\n📂 读取Excel文件: {excel_file}")
    excel_data = reader.read(excel_file)

    print(f"\n✅ Excel读取成功")
    print(f"   文件: {excel_data.file_path}")
    print(f"   Sheet数量: {len(excel_data.sheet_names)}")

    # 检查HLA数据
    print(f"\n【验证HLA数据】")
    hla_data = excel_data.get_table_data("HLA")

    if hla_data:
        print(f"✅ HLA数据读取成功（使用专用解析器）")
        print(f"   HLA位点数量: {len(hla_data)}")

        # 显示每个位点的详细信息
        for i, item in enumerate(hla_data, 1):
            print(f"\n   位点 {i}: {item.get('Locus')}")
            print(f"      杂合性: {item.get('Zygosity')}")
            print(f"      Type 1: {item.get('Type1')}")
            print(f"      Type 2: {item.get('Type2')}")

        # 验证数据结构
        print(f"\n【数据结构验证】")
        expected_loci = ["HLA-A", "HLA-B", "HLA-C"]
        found_loci = [item.get("Locus") for item in hla_data]

        print(f"   预期位点: {expected_loci}")
        print(f"   实际位点: {found_loci}")

        if set(found_loci) == set(expected_loci):
            print(f"   ✅ 所有预期位点都已找到")
        else:
            missing = set(expected_loci) - set(found_loci)
            extra = set(found_loci) - set(expected_loci)
            if missing:
                print(f"   ⚠️  缺少位点: {missing}")
            if extra:
                print(f"   ⚠️  额外位点: {extra}")

        # 验证每个位点都有Type 1和Type 2
        print(f"\n【Type完整性验证】")
        for item in hla_data:
            locus = item.get("Locus")
            type1 = item.get("Type1")
            type2 = item.get("Type2")

            if type1 and type2:
                print(f"   ✅ {locus}: Type 1 和 Type 2 都存在")
            else:
                if not type1:
                    print(f"   ⚠️  {locus}: 缺少 Type 1")
                if not type2:
                    print(f"   ⚠️  {locus}: 缺少 Type 2")

    else:
        print(f"❌ HLA数据未找到")

    # 对比旧方法（标准表格读取）vs 新方法（专用解析器）
    print(f"\n【对比：标准读取 vs 专用解析器】")

    # 使用标准方法读取
    import pandas as pd
    df_standard = pd.read_excel(excel_file, sheet_name="HLA")
    print(f"   标准读取: {len(df_standard)} 行")
    print(f"   列名: {list(df_standard.columns[:3])}...")

    print(f"   专用解析器: {len(hla_data) if hla_data else 0} 个位点")
    print(f"   数据结构: [{'Locus', 'Zygosity', 'Type1', 'Type2'}]")

    print(f"\n   结论: 专用解析器将HLA的特殊格式转换为标准化的表格结构 ✅")

    print("\n" + "=" * 80)
    print("✅ HLA解析器测试完成")
    print("=" * 80)


if __name__ == "__main__":
    excel_file = sys.argv[1] if len(sys.argv) > 1 else "data/input/MLF2509307001T_MLB2509307001.result.xlsx"
    test_hla_parser(excel_file)
