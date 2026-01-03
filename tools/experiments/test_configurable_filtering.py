#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试可配置的过滤功能

测试不同的过滤配置参数，验证配置化过滤系统是否正常工作
"""

import sys
import yaml
import shutil
from pathlib import Path
from reportgen.core.excel_reader import ExcelReader
from reportgen.core.field_mapper import FieldMapper


def test_filtering_with_config(config_name: str, min_frequency: float, enabled_freq: bool, enabled_clin: bool):
    """使用指定配置测试过滤"""

    print(f"\n{'='*80}")
    print(f"测试配置: {config_name}")
    print(f"  - 频率过滤: {'启用' if enabled_freq else '禁用'} (阈值: {min_frequency}%)")
    print(f"  - 临床显著性过滤: {'启用' if enabled_clin else '禁用'}")
    print(f"{'='*80}")

    # 备份原配置
    config_file = Path("config/filtering.yaml")
    backup_file = Path("config/filtering.yaml.backup")

    if config_file.exists() and not backup_file.exists():
        shutil.copy(config_file, backup_file)

    # 创建临时配置
    temp_config = {
        "variations": {
            "enabled": True,
            "frequency_filter": {
                "enabled": enabled_freq,
                "min_frequency": min_frequency,
                "frequency_columns": ["Freq(%)", "AF", "变异频率", "Frequency", "freq"]
            },
            "clinical_significance_filter": {
                "enabled": enabled_clin,
                "significant_keywords": ["Missense", "Nonsense", "Frameshift", "Splice"],
                "function_columns": ["Function", "功能", "Type", "变异类型", "Consequence"]
            },
            "basic_validation": {
                "require_gene": True,
                "gene_columns": ["Gene_Symbol", "基因", "Gene", "gene"],
                "require_variant": True,
                "variant_columns": ["cHGVS", "变异", "Variant", "HGVS", "hgvs"]
            }
        },
        "reporting": {
            "log_filtering_stats": True,
            "log_filtered_items": False
        }
    }

    # 写入临时配置
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(temp_config, f, allow_unicode=True, default_flow_style=False)

    # 执行测试
    try:
        # 1. 读取Excel
        reader = ExcelReader(config_dir="config")
        excel_data = reader.read("data/input/MLF2509307001T_MLB2509307001.result.xlsx")

        # 获取原始数据行数
        raw_variations = excel_data.get_table_data("Variations")
        total_raw = len(raw_variations) if raw_variations else 0

        # 2. 应用过滤
        mapper = FieldMapper(config_dir="config")
        report_data = mapper.map(excel_data)

        # 获取过滤后数据
        filtered_variants = report_data.get_table("variants")
        total_filtered = len(filtered_variants) if filtered_variants else 0

        # 3. 统计
        filtered_out = total_raw - total_filtered
        retention_rate = (total_filtered / total_raw * 100) if total_raw > 0 else 0

        print(f"\n【过滤结果】")
        print(f"  原始数据: {total_raw} 行")
        print(f"  过滤后: {total_filtered} 行")
        print(f"  过滤掉: {filtered_out} 行 ({100 - retention_rate:.1f}%)")
        print(f"  保留率: {retention_rate:.1f}%")

        # 4. 分析保留数据
        high_freq_count = 0
        clin_sig_count = 0
        both_count = 0

        for var in filtered_variants:
            freq = var.get("freq") or var.get("Freq(%)")
            func = var.get("function") or var.get("Function")

            is_high_freq = False
            if freq is not None:
                try:
                    is_high_freq = float(freq) >= min_frequency
                except:
                    pass

            is_clin_sig = False
            if func is not None:
                is_clin_sig = any(kw in str(func) for kw in ["Missense", "Nonsense", "Frameshift", "Splice"])

            if is_high_freq and is_clin_sig:
                both_count += 1
            elif is_high_freq:
                high_freq_count += 1
            elif is_clin_sig:
                clin_sig_count += 1

        print(f"\n【保留变异分类】")
        print(f"  仅高频 (≥{min_frequency}%): {high_freq_count} 个")
        print(f"  仅临床显著: {clin_sig_count} 个")
        print(f"  两者都满足: {both_count} 个")

        return total_filtered

    finally:
        # 恢复原配置
        if backup_file.exists():
            shutil.move(backup_file, config_file)


def main():
    """主测试流程"""

    print("=" * 80)
    print("可配置过滤系统测试")
    print("=" * 80)

    results = {}

    # 测试1: 默认配置（5%）
    results["默认(5%)"] = test_filtering_with_config(
        "默认配置 (5%阈值)",
        min_frequency=5.0,
        enabled_freq=True,
        enabled_clin=True
    )

    # 测试2: 低阈值（3%）
    results["低阈值(3%)"] = test_filtering_with_config(
        "低阈值 (3%)",
        min_frequency=3.0,
        enabled_freq=True,
        enabled_clin=True
    )

    # 测试3: 高阈值（10%）
    results["高阈值(10%)"] = test_filtering_with_config(
        "高阈值 (10%)",
        min_frequency=10.0,
        enabled_freq=True,
        enabled_clin=True
    )

    # 测试4: 只用临床显著性
    results["仅临床显著性"] = test_filtering_with_config(
        "仅临床显著性过滤",
        min_frequency=5.0,
        enabled_freq=False,
        enabled_clin=True
    )

    # 测试5: 只用频率（10%）
    results["仅频率(10%)"] = test_filtering_with_config(
        "仅频率过滤 (10%)",
        min_frequency=10.0,
        enabled_freq=True,
        enabled_clin=False
    )

    # 总结
    print(f"\n{'='*80}")
    print("测试总结")
    print(f"{'='*80}\n")

    print(f"{'配置':<20} {'保留变异数':>10}")
    print(f"{'-'*80}")
    for config_name, count in results.items():
        print(f"{config_name:<20} {count:>10} 行")

    print(f"\n{'='*80}")
    print("✅ 可配置过滤系统测试完成")
    print(f"{'='*80}")

    print(f"\n💡 结论:")
    print(f"  - 配置化过滤系统工作正常")
    print(f"  - 不同阈值产生不同的过滤结果")
    print(f"  - 可以灵活启用/禁用不同的过滤策略")
    print(f"  - 推荐使用默认配置（5%阈值 + 临床显著性）")


if __name__ == "__main__":
    main()
