#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试变异数据过滤功能

验证智能过滤是否正确工作
"""

import sys
from reportgen.core.excel_reader import ExcelReader
from reportgen.core.field_mapper import FieldMapper

def test_variations_filtering(excel_file="data/input/MLF2509307001T_MLB2509307001.result.xlsx"):
    """测试变异过滤功能"""

    print("=" * 80)
    print("测试变异数据智能过滤")
    print("=" * 80)

    # 1. 读取Excel
    print(f"\n【步骤1: 读取Excel】")
    print(f"   文件: {excel_file}")

    reader = ExcelReader(config_dir="config")
    excel_data = reader.read(excel_file)

    print(f"   ✅ 读取成功")

    # 获取原始Variations数据
    variations_raw = excel_data.get_table_data("Variations")

    if not variations_raw:
        print("   ❌ 未找到Variations数据")
        return

    print(f"   原始数据: {len(variations_raw)} 行")

    # 2. 应用字段映射（包含过滤）
    print(f"\n【步骤2: 应用字段映射（包含智能过滤）】")

    mapper = FieldMapper(config_dir="config")
    report_data = mapper.map(excel_data)

    print(f"   ✅ 映射成功")

    # 获取过滤后的数据
    variants_filtered = report_data.get_table("variants")

    if not variants_filtered:
        print("   ❌ 过滤后未找到variants数据")
        return

    print(f"   过滤后数据: {len(variants_filtered)} 行")

    # 3. 对比统计
    print(f"\n【步骤3: 过滤效果统计】")

    total_before = len(variations_raw)
    total_after = len(variants_filtered)
    filtered_out = total_before - total_after
    retention_rate = (total_after / total_before * 100) if total_before > 0 else 0

    print(f"   原始数据: {total_before} 行")
    print(f"   过滤后: {total_after} 行")
    print(f"   过滤掉: {filtered_out} 行 ({filtered_out/total_before*100:.1f}%)")
    print(f"   保留率: {retention_rate:.1f}%")

    # 4. 分析保留的变异
    print(f"\n【步骤4: 分析保留的变异】")

    # 统计频率分布
    high_freq_count = 0
    freq_values = []

    for var in variants_filtered:
        freq = var.get("freq") or var.get("Freq(%)") or var.get("AF")
        if freq is not None:
            try:
                freq_value = float(freq)
                freq_values.append(freq_value)
                if freq_value >= 5.0:
                    high_freq_count += 1
            except (ValueError, TypeError):
                pass

    print(f"   高频变异 (≥5%): {high_freq_count} 个")

    if freq_values:
        print(f"   频率范围: {min(freq_values):.2f}% - {max(freq_values):.2f}%")
        print(f"   平均频率: {sum(freq_values)/len(freq_values):.2f}%")

    # 统计变异类型分布
    function_stats = {}
    for var in variants_filtered:
        func = var.get("function") or var.get("Function") or var.get("Type")
        if func:
            function_str = str(func)
            for keyword in ['Missense', 'Nonsense', 'Frameshift', 'Splice']:
                if keyword in function_str:
                    function_stats[keyword] = function_stats.get(keyword, 0) + 1

    if function_stats:
        print(f"\n   变异类型分布:")
        for func_type, count in sorted(function_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"      {func_type}: {count} 个 ({count/total_after*100:.1f}%)")

    # 5. 显示保留的变异样例
    print(f"\n【步骤5: 保留的变异样例（前10个）】")

    for i, var in enumerate(variants_filtered[:10], 1):
        gene = var.get("gene") or var.get("Gene_Symbol")
        freq = var.get("freq") or var.get("Freq(%)")
        func = var.get("function") or var.get("Function")

        print(f"   {i}. {gene}: {freq}% - {func}")

    # 6. 验证过滤逻辑
    print(f"\n【步骤6: 验证过滤逻辑】")

    # 检查所有保留的变异是否符合过滤条件
    compliant_count = 0

    for var in variants_filtered:
        freq = var.get("freq") or var.get("Freq(%)")
        func = var.get("function") or var.get("Function")

        is_high_freq = False
        if freq is not None:
            try:
                is_high_freq = float(freq) >= 5.0
            except:
                pass

        is_clinical = False
        if func:
            clinical_keywords = ['Missense', 'Nonsense', 'Frameshift', 'Splice']
            is_clinical = any(kw in str(func) for kw in clinical_keywords)

        if is_high_freq or is_clinical:
            compliant_count += 1

    print(f"   符合过滤条件的变异: {compliant_count} / {total_after}")

    if compliant_count == total_after:
        print(f"   ✅ 所有保留的变异都符合过滤条件")
    else:
        print(f"   ⚠️  {total_after - compliant_count} 个变异不符合过滤条件")

    print("\n" + "=" * 80)
    print("✅ 变异过滤测试完成")
    print("=" * 80)


if __name__ == "__main__":
    excel_file = sys.argv[1] if len(sys.argv) > 1 else "data/input/MLF2509307001T_MLB2509307001.result.xlsx"
    test_variations_filtering(excel_file)
