#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细检查CNV和Fusion sheet的结构
"""

import pandas as pd

def inspect_sheets(excel_file="data/input/MLF2509307001T_MLB2509307001.result.xlsx"):
    """检查sheet结构"""

    print("=" * 80)
    print("检查CNV和Fusion sheet结构")
    print("=" * 80)

    for sheet_name in ["Cnv", "Fusion"]:
        print(f"\n{'=' * 80}")
        print(f"Sheet: {sheet_name}")
        print(f"{'=' * 80}")

        # 不跳过任何行，查看原始数据
        print(f"\n【原始数据（不跳过行）】")
        df_original = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
        print(f"行数: {len(df_original)}")
        print(f"列数: {len(df_original.columns)}")
        print(f"\n前5行:")
        for i in range(min(5, len(df_original))):
            print(f"  Row {i}: {list(df_original.iloc[i].values[:10])}")  # 显示前10列

        # 跳过1行
        print(f"\n【跳过第1行后（skiprows=1）】")
        df_skip1 = pd.read_excel(excel_file, sheet_name=sheet_name, skiprows=1)
        print(f"行数: {len(df_skip1)}")
        print(f"列数: {len(df_skip1.columns)}")
        print(f"列名: {list(df_skip1.columns[:10])}")  # 显示前10列名
        if len(df_skip1) > 0:
            print(f"\n前3行数据:")
            for i in range(min(3, len(df_skip1))):
                print(f"  Row {i}: {list(df_skip1.iloc[i].values[:10])}")

        # 跳过1行并手动指定header=0
        print(f"\n【跳过第1行，header=0】")
        df_skip1_h0 = pd.read_excel(excel_file, sheet_name=sheet_name, skiprows=[0], header=0)
        print(f"行数: {len(df_skip1_h0)}")
        print(f"列数: {len(df_skip1_h0.columns)}")
        print(f"列名: {list(df_skip1_h0.columns[:10])}")
        if len(df_skip1_h0) > 0:
            print(f"\n前3行数据:")
            for i in range(min(3, len(df_skip1_h0))):
                print(f"  Row {i}: {list(df_skip1_h0.iloc[i].values[:10])}")


if __name__ == "__main__":
    inspect_sheets()
