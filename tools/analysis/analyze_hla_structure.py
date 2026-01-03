#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细分析HLA数据结构

理解HLA sheet的特殊格式，为实现专用解析器做准备
"""

import pandas as pd
import json

def analyze_hla_structure(excel_file="data/input/MLF2509307001T_MLB2509307001.result.xlsx"):
    """详细分析HLA sheet结构"""

    print("=" * 80)
    print("HLA数据结构详细分析")
    print("=" * 80)

    # 读取HLA sheet（不跳过任何行）
    print(f"\n📂 读取Excel文件: {excel_file}")
    print(f"   Sheet: HLA")

    # 方式1: 不指定header，查看原始结构
    df_raw = pd.read_excel(excel_file, sheet_name="HLA", header=None)

    print(f"\n【原始数据结构】")
    print(f"   行数: {len(df_raw)}")
    print(f"   列数: {len(df_raw.columns)}")

    print(f"\n【逐行数据】")
    for i in range(len(df_raw)):
        row_values = [str(v) if pd.notna(v) else "NaN" for v in df_raw.iloc[i].values]
        print(f"   Row {i}: {row_values}")

    # 方式2: 使用默认header读取
    df_default = pd.read_excel(excel_file, sheet_name="HLA")

    print(f"\n【默认读取（header=0）】")
    print(f"   行数: {len(df_default)}")
    print(f"   列名: {list(df_default.columns)}")
    print(f"\n   数据:")
    for i in range(min(10, len(df_default))):
        print(f"   Row {i}: {list(df_default.iloc[i].values)}")

    # 分析HLA位点和类型
    print(f"\n【HLA位点识别】")
    loci_found = []

    for i in range(len(df_raw)):
        first_col = str(df_raw.iloc[i, 0]) if pd.notna(df_raw.iloc[i, 0]) else ""

        # 检查是否是HLA位点标识（如"HLA-A", "HLA-B"）
        if first_col.startswith("HLA-"):
            loci_found.append({
                "row": i,
                "locus": first_col,
                "second_col": str(df_raw.iloc[i, 1]) if pd.notna(df_raw.iloc[i, 1]) else "NaN"
            })
            print(f"   Row {i}: {first_col} - {df_raw.iloc[i, 1] if pd.notna(df_raw.iloc[i, 1]) else 'NaN'}")

    # 分析Type标记
    print(f"\n【Type标记识别】")
    for i in range(len(df_raw)):
        first_col = str(df_raw.iloc[i, 0]) if pd.notna(df_raw.iloc[i, 0]) else ""

        if "[Type" in first_col or "Type" in first_col:
            print(f"   Row {i}: {first_col}")
            # 显示该行的所有非NaN值
            row_data = {}
            for j, val in enumerate(df_raw.iloc[i].values):
                if pd.notna(val):
                    row_data[f"Col{j}"] = str(val)
            print(f"      数据: {row_data}")

    # 尝试解析HLA结构
    print(f"\n【HLA结构解析】")
    hla_data = parse_hla_data(df_raw)

    if hla_data:
        print(f"   解析到 {len(hla_data)} 个HLA位点:")
        for item in hla_data:
            print(f"   - {item['locus']}:")
            print(f"       Type 1: {item.get('type1', 'N/A')}")
            print(f"       Type 2: {item.get('type2', 'N/A')}")
            if item.get('extra'):
                print(f"       额外信息: {item['extra']}")

    # 保存分析结果为JSON
    output = {
        "raw_structure": {
            "rows": len(df_raw),
            "columns": len(df_raw.columns),
            "data": []
        },
        "loci_found": loci_found,
        "parsed_hla_data": hla_data
    }

    for i in range(len(df_raw)):
        row_dict = {}
        for j, val in enumerate(df_raw.iloc[i].values):
            if pd.notna(val):
                row_dict[f"col{j}"] = str(val)
        if row_dict:
            output["raw_structure"]["data"].append({"row": i, "values": row_dict})

    with open("hla_structure_analysis.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n💾 分析结果已保存到: hla_structure_analysis.json")

    print("\n" + "=" * 80)
    print("✅ HLA结构分析完成")
    print("=" * 80)


def parse_hla_data(df_raw):
    """
    解析HLA数据的特殊结构

    预期结构：
    Row N: HLA-A, HET
    Row N+1: [Type 1], allele1, extra_info
    Row N+2: [Type 2], allele2, extra_info
    Row N+3: (空行或下一个位点)
    """
    hla_data = []
    current_locus = None
    current_item = None

    for i in range(len(df_raw)):
        first_col = str(df_raw.iloc[i, 0]) if pd.notna(df_raw.iloc[i, 0]) else ""
        second_col = str(df_raw.iloc[i, 1]) if pd.notna(df_raw.iloc[i, 1]) else ""
        third_col = str(df_raw.iloc[i, 2]) if pd.notna(df_raw.iloc[i, 2]) else ""

        # 检测HLA位点开始
        if first_col.startswith("HLA-"):
            # 保存前一个位点（如果有）
            if current_item:
                hla_data.append(current_item)

            # 开始新位点
            current_locus = first_col
            current_item = {
                "locus": current_locus,
                "zygosity": second_col if second_col != "NaN" else None
            }

        # 检测Type 1
        elif "[Type 1]" in first_col or first_col == "[Type 1]":
            if current_item:
                current_item["type1"] = second_col if second_col != "NaN" else None
                if third_col != "NaN":
                    current_item["type1_extra"] = third_col

        # 检测Type 2
        elif "[Type 2]" in first_col or first_col == "[Type 2]":
            if current_item:
                current_item["type2"] = second_col if second_col != "NaN" else None
                if third_col != "NaN":
                    current_item["type2_extra"] = third_col

    # 保存最后一个位点
    if current_item:
        hla_data.append(current_item)

    return hla_data


if __name__ == "__main__":
    analyze_hla_structure()
