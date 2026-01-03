#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析Variations数据

了解变异数据的结构、数量、频率分布，为过滤功能做准备
"""

import pandas as pd
import json

def analyze_variations(excel_file="data/input/MLF2509307001T_MLB2509307001.result.xlsx"):
    """分析Variations数据"""

    print("=" * 80)
    print("Variations数据分析")
    print("=" * 80)

    # 读取Variations sheet
    print(f"\n📂 读取Excel文件: {excel_file}")
    print(f"   Sheet: Variations")

    df = pd.read_excel(excel_file, sheet_name="Variations")

    print(f"\n【基本信息】")
    print(f"   总行数: {len(df)}")
    print(f"   总列数: {len(df.columns)}")
    print(f"   列名: {list(df.columns)}")

    # 分析关键列
    print(f"\n【关键列分析】")

    # 1. 基因列
    gene_cols = [col for col in df.columns if 'gene' in col.lower() or 'symbol' in col.lower()]
    if gene_cols:
        print(f"   基因列: {gene_cols}")
        for col in gene_cols:
            unique_genes = df[col].dropna().unique()
            print(f"      {col}: {len(unique_genes)} 个不同基因")
            if len(unique_genes) <= 10:
                print(f"         基因: {list(unique_genes)}")

    # 2. 频率列
    freq_cols = [col for col in df.columns if 'freq' in col.lower() or 'af' in col.lower() or '频率' in col]
    if freq_cols:
        print(f"\n   频率列: {freq_cols}")
        for col in freq_cols:
            freq_values = pd.to_numeric(df[col], errors='coerce').dropna()
            if len(freq_values) > 0:
                print(f"      {col}:")
                print(f"         有效数值: {len(freq_values)} / {len(df)} 行")
                print(f"         最小值: {freq_values.min():.2f}")
                print(f"         最大值: {freq_values.max():.2f}")
                print(f"         平均值: {freq_values.mean():.2f}")
                print(f"         中位数: {freq_values.median():.2f}")

                # 频率分布
                freq_5 = (freq_values > 5).sum()
                freq_10 = (freq_values > 10).sum()
                freq_20 = (freq_values > 20).sum()
                print(f"         >5%: {freq_5} ({freq_5/len(freq_values)*100:.1f}%)")
                print(f"         >10%: {freq_10} ({freq_10/len(freq_values)*100:.1f}%)")
                print(f"         >20%: {freq_20} ({freq_20/len(freq_values)*100:.1f}%)")

    # 3. 功能/临床显著性列
    func_cols = [col for col in df.columns if 'function' in col.lower() or 'clinical' in col.lower() or 'significance' in col.lower() or 'pathogen' in col.lower()]
    if func_cols:
        print(f"\n   功能/显著性列: {func_cols}")
        for col in func_cols:
            unique_values = df[col].dropna().unique()
            print(f"      {col}: {len(unique_values)} 个不同值")
            if len(unique_values) <= 20:
                print(f"         值: {list(unique_values)}")

    # 4. 变异类型列
    var_type_cols = [col for col in df.columns if 'type' in col.lower() or 'class' in col.lower()]
    if var_type_cols:
        print(f"\n   变异类型列: {var_type_cols}")
        for col in var_type_cols:
            unique_values = df[col].dropna().unique()
            print(f"      {col}: {len(unique_values)} 个不同值")
            if len(unique_values) <= 20:
                value_counts = df[col].value_counts()
                print(f"         分布:")
                for val, count in value_counts.head(10).items():
                    print(f"            {val}: {count}")

    # 显示前10行数据样例
    print(f"\n【数据样例（前10行）】")
    key_cols = []
    if gene_cols:
        key_cols.append(gene_cols[0])
    if freq_cols:
        key_cols.append(freq_cols[0])
    if func_cols:
        key_cols.extend(func_cols[:2])

    if key_cols:
        print(df[key_cols].head(10).to_string(index=False))

    # 分析过滤潜力
    print(f"\n【过滤潜力分析】")

    total_rows = len(df)

    # 按频率过滤
    if freq_cols:
        freq_col = freq_cols[0]
        freq_values = pd.to_numeric(df[freq_col], errors='coerce').dropna()

        for threshold in [1, 3, 5, 10]:
            above_threshold = (freq_values > threshold).sum()
            print(f"   频率 >{threshold}%: {above_threshold} 行 (保留 {above_threshold/total_rows*100:.1f}%)")

    # 按功能过滤
    if func_cols:
        func_col = func_cols[0]
        func_values = df[func_col].dropna()

        # 常见的有害/致病变异标记
        pathogenic_keywords = ['Missense', 'Nonsense', 'Frameshift', 'Splice', 'pathogenic', 'deleterious']

        for keyword in pathogenic_keywords:
            matching = func_values.str.contains(keyword, case=False, na=False).sum()
            if matching > 0:
                print(f"   包含 '{keyword}': {matching} 行 ({matching/total_rows*100:.1f}%)")

    # 保存分析结果
    analysis = {
        "total_rows": int(total_rows),
        "columns": list(df.columns),
        "gene_columns": gene_cols,
        "freq_columns": freq_cols,
        "function_columns": func_cols,
        "var_type_columns": var_type_cols
    }

    if freq_cols:
        freq_col = freq_cols[0]
        freq_values = pd.to_numeric(df[freq_col], errors='coerce').dropna()
        if len(freq_values) > 0:
            analysis["frequency_stats"] = {
                "column": freq_col,
                "valid_values": int(len(freq_values)),
                "total_rows": int(len(df)),
                "min": float(freq_values.min()),
                "max": float(freq_values.max()),
                "mean": float(freq_values.mean()),
                "median": float(freq_values.median()),
                "above_5": int((freq_values > 5).sum()),
                "above_10": int((freq_values > 10).sum())
            }

    with open("variations_analysis.json", "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    print(f"\n💾 分析结果已保存到: variations_analysis.json")

    print("\n" + "=" * 80)
    print("✅ Variations数据分析完成")
    print("=" * 80)


if __name__ == "__main__":
    analyze_variations()
