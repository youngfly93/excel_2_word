#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析CNV、Fusion、HLA三个Sheet的数据结构
"""

import pandas as pd
import json
import sys

def analyze_sheet(excel_path, sheet_name):
    """分析单个Sheet的结构"""

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
    except Exception as e:
        return {
            "sheet_name": sheet_name,
            "error": str(e),
            "exists": False
        }

    # 基本信息
    info = {
        "sheet_name": sheet_name,
        "exists": True,
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": list(df.columns),
        "column_types": {},
        "sample_data": [],
        "non_null_counts": {}
    }

    # 列类型和非空统计
    for col in df.columns:
        info["column_types"][col] = str(df[col].dtype)
        info["non_null_counts"][col] = int(df[col].notna().sum())

    # 前5行样本数据
    for i, row in df.head(5).iterrows():
        sample_row = {}
        for col in df.columns:
            val = row[col]
            if pd.isna(val):
                sample_row[col] = None
            elif isinstance(val, (int, float, str, bool)):
                sample_row[col] = val
            else:
                sample_row[col] = str(val)
        info["sample_data"].append(sample_row)

    return info

def analyze_all_sheets(excel_path):
    """分析CNV、Fusion、HLA三个Sheet"""

    sheets_to_analyze = ["Cnv", "Fusion", "HLA"]
    results = {}

    print("=" * 80)
    print("📊 分析CNV、Fusion、HLA数据结构")
    print("=" * 80)
    print()

    for sheet_name in sheets_to_analyze:
        print(f"🔍 分析 {sheet_name} Sheet...")
        info = analyze_sheet(excel_path, sheet_name)
        results[sheet_name] = info

        if info.get("exists"):
            print(f"✅ {sheet_name}: {info['rows']}行 x {info['columns']}列")
            print(f"   列: {', '.join(list(info['column_names'])[:5])}{'...' if len(info['column_names']) > 5 else ''}")
        else:
            print(f"❌ {sheet_name}: {info.get('error', '不存在')}")
        print()

    return results

def print_detailed_analysis(results):
    """打印详细分析结果"""

    print("\n" + "=" * 80)
    print("📋 详细分析结果")
    print("=" * 80)

    for sheet_name, info in results.items():
        if not info.get("exists"):
            continue

        print(f"\n### {sheet_name} Sheet")
        print(f"行数: {info['rows']}")
        print(f"列数: {info['columns']}")
        print()

        print("列名和类型:")
        for col in info['column_names']:
            dtype = info['column_types'][col]
            non_null = info['non_null_counts'][col]
            null_count = info['rows'] - non_null
            print(f"  - {col}: {dtype} ({non_null}非空, {null_count}空值)")
        print()

        if info['sample_data']:
            print("前3行样本数据:")
            for i, row in enumerate(info['sample_data'][:3], 1):
                print(f"  行{i}:")
                for col, val in list(row.items())[:5]:
                    val_str = str(val)[:50] if val is not None else "NULL"
                    print(f"    {col}: {val_str}")
                print()

def recommend_table_structure(results):
    """推荐报告表格结构"""

    print("\n" + "=" * 80)
    print("💡 报告表格结构建议")
    print("=" * 80)

    recommendations = {}

    # CNV表格建议
    if results.get("Cnv", {}).get("exists"):
        cnv_cols = results["Cnv"]["column_names"]
        recommendations["CNV"] = {
            "description": "拷贝数变异（Copy Number Variation）",
            "suggested_columns": [
                "Gene_Symbol",
                "Chr",
                "Start",
                "End",
                "Copy_Number",
                "Log2_Ratio",
                "Status"
            ],
            "available_columns": cnv_cols
        }

        print("\n### CNV表格（拷贝数变异）")
        print("建议列:")
        for col in recommendations["CNV"]["suggested_columns"]:
            if col in cnv_cols:
                print(f"  ✅ {col}")
            else:
                # 查找相似列名
                similar = [c for c in cnv_cols if col.lower() in c.lower() or c.lower() in col.lower()]
                if similar:
                    print(f"  🔄 {col} -> {similar[0]}")
                else:
                    print(f"  ❌ {col} (未找到)")

    # Fusion表格建议
    if results.get("Fusion", {}).get("exists"):
        fusion_cols = results["Fusion"]["column_names"]
        recommendations["Fusion"] = {
            "description": "基因融合（Gene Fusion）",
            "suggested_columns": [
                "Gene1",
                "Gene2",
                "Fusion_Type",
                "Breakpoint1",
                "Breakpoint2",
                "Read_Count",
                "Clinical_Significance"
            ],
            "available_columns": fusion_cols
        }

        print("\n### Fusion表格（基因融合）")
        print("建议列:")
        for col in recommendations["Fusion"]["suggested_columns"]:
            if col in fusion_cols:
                print(f"  ✅ {col}")
            else:
                similar = [c for c in fusion_cols if col.lower() in c.lower() or c.lower() in col.lower()]
                if similar:
                    print(f"  🔄 {col} -> {similar[0]}")
                else:
                    print(f"  ❌ {col} (未找到)")

    # HLA表格建议
    if results.get("HLA", {}).get("exists"):
        hla_cols = results["HLA"]["column_names"]
        recommendations["HLA"] = {
            "description": "HLA分型（Human Leukocyte Antigen）",
            "suggested_columns": [
                "Locus",
                "Allele1",
                "Allele2",
                "Genotype"
            ],
            "available_columns": hla_cols
        }

        print("\n### HLA表格（HLA分型）")
        print("建议列:")
        for col in recommendations["HLA"]["suggested_columns"]:
            if col in hla_cols:
                print(f"  ✅ {col}")
            else:
                similar = [c for c in hla_cols if col.lower() in c.lower() or c.lower() in col.lower()]
                if similar:
                    print(f"  🔄 {col} -> {similar[0]}")
                else:
                    print(f"  ❌ {col} (未找到)")

    return recommendations

def main():
    if len(sys.argv) < 2:
        print("用法: python analyze_cnv_fusion_hla.py <excel文件>")
        sys.exit(1)

    excel_path = sys.argv[1]

    # 分析所有Sheet
    results = analyze_all_sheets(excel_path)

    # 打印详细分析
    print_detailed_analysis(results)

    # 推荐表格结构
    recommendations = recommend_table_structure(results)

    # 保存结果
    output = {
        "analysis": results,
        "recommendations": recommendations
    }

    output_file = "cnv_fusion_hla_analysis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print(f"✅ 分析结果已保存到: {output_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
