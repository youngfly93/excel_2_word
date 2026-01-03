#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试HLA质量控制数据提取

验证EX2/EX3/EX4/EX5覆盖度数据是否正确提取
"""

import json
from reportgen.core.excel_reader import ExcelReader


def test_hla_qc_extraction(excel_file="data/input/MLF2509307001T_MLB2509307001.result.xlsx"):
    """测试HLA QC数据提取"""

    print("=" * 80)
    print("HLA质量控制数据提取测试")
    print("=" * 80)

    print(f"\n📂 测试文件: {excel_file}")

    # 读取Excel
    print(f"\n【步骤1: 读取Excel（包含HLA QC数据）】")

    reader = ExcelReader(config_dir="config")
    excel_data = reader.read(excel_file)

    print(f"   ✅ 读取成功")

    # 获取HLA数据
    print(f"\n【步骤2: 检查HLA数据结构】")

    hla_data = excel_data.get_table_data("HLA")

    if not hla_data:
        print(f"   ❌ HLA数据未找到")
        return

    print(f"   ✅ HLA数据已找到")
    print(f"   位点数量: {len(hla_data)}")

    # 验证QC数据
    print(f"\n【步骤3: 验证QC数据】")

    all_qc_valid = True

    for i, locus_data in enumerate(hla_data, 1):
        locus = locus_data.get("Locus", "Unknown")
        zygosity = locus_data.get("Zygosity", "Unknown")
        type1 = locus_data.get("Type1", "Unknown")
        type2 = locus_data.get("Type2", "Unknown")
        qc_data = locus_data.get("QC")

        print(f"\n   位点 {i}: {locus}")
        print(f"      Zygosity: {zygosity}")
        print(f"      Type 1: {type1}")
        print(f"      Type 2: {type2}")

        if qc_data:
            print(f"      ✅ QC数据已提取")

            # Type 1 QC
            type1_qc = qc_data.get("Type1", {})
            if type1_qc:
                print(f"\n      Type 1 QC:")
                for exon in ["EX2", "EX3", "EX4", "EX5"]:
                    if exon in type1_qc:
                        coverage = type1_qc[exon]["coverage"]
                        percentage = type1_qc[exon]["percentage"]
                        print(f"         {exon}: Coverage={coverage:.2f}, Percentage={percentage:.1f}%")
                    else:
                        print(f"         {exon}: ⚠️  缺失")
            else:
                print(f"      ⚠️  Type 1 QC数据为空")
                all_qc_valid = False

            # Type 2 QC
            type2_qc = qc_data.get("Type2", {})
            if type2_qc:
                print(f"\n      Type 2 QC:")
                for exon in ["EX2", "EX3", "EX4", "EX5"]:
                    if exon in type2_qc:
                        coverage = type2_qc[exon]["coverage"]
                        percentage = type2_qc[exon]["percentage"]
                        print(f"         {exon}: Coverage={coverage:.2f}, Percentage={percentage:.1f}%")
                    else:
                        print(f"         {exon}: ⚠️  缺失")
            else:
                print(f"      ⚠️  Type 2 QC数据为空")
                all_qc_valid = False

        else:
            print(f"      ❌ QC数据未提取")
            all_qc_valid = False

    # 总结
    print(f"\n【步骤4: 数据完整性验证】")

    expected_loci = 3  # HLA-A, HLA-B, HLA-C
    expected_exons = 4  # EX2, EX3, EX4, EX5

    actual_loci = len(hla_data)

    if actual_loci == expected_loci:
        print(f"   ✅ 位点数量正确: {actual_loci} / {expected_loci}")
    else:
        print(f"   ⚠️  位点数量不符: {actual_loci} / {expected_loci} (expected)")

    # 统计exon数据
    total_exons_expected = expected_loci * 2 * expected_exons  # 3 loci * 2 types * 4 exons = 24
    total_exons_extracted = 0

    for locus_data in hla_data:
        qc_data = locus_data.get("QC", {})
        type1_qc = qc_data.get("Type1", {})
        type2_qc = qc_data.get("Type2", {})
        total_exons_extracted += len(type1_qc) + len(type2_qc)

    if total_exons_extracted == total_exons_expected:
        print(f"   ✅ Exon数据完整: {total_exons_extracted} / {total_exons_expected}")
    else:
        print(f"   ⚠️  Exon数据不完整: {total_exons_extracted} / {total_exons_expected} (expected)")

    # 导出JSON验证
    print(f"\n【步骤5: 导出数据结构（用于验证）】")

    output_file = "hla_qc_data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(hla_data, f, ensure_ascii=False, indent=2)

    print(f"   💾 已导出到: {output_file}")

    # 总结
    print("\n" + "=" * 80)
    if all_qc_valid and actual_loci == expected_loci and total_exons_extracted == total_exons_expected:
        print("✅ HLA质量控制数据提取完全成功")
    else:
        print("⚠️  HLA质量控制数据提取部分成功（存在缺失或错误）")
    print("=" * 80)

    print(f"\n💡 数据结构:")
    print(f"  Locus")
    print(f"  ├── Type1")
    print(f"  ├── Type2")
    print(f"  ├── Zygosity")
    print(f"  └── QC")
    print(f"      ├── Type1")
    print(f"      │   ├── EX2 (coverage, percentage)")
    print(f"      │   ├── EX3 (coverage, percentage)")
    print(f"      │   ├── EX4 (coverage, percentage)")
    print(f"      │   └── EX5 (coverage, percentage)")
    print(f"      └── Type2")
    print(f"          ├── EX2 (coverage, percentage)")
    print(f"          ├── EX3 (coverage, percentage)")
    print(f"          ├── EX4 (coverage, percentage)")
    print(f"          └── EX5 (coverage, percentage)")


if __name__ == "__main__":
    test_hla_qc_extraction()
