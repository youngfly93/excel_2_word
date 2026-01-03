#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查Fusion sheet结构"""

import pandas as pd

excel_file = "data/input/MLF2509307001T_MLB2509307001.result.xlsx"

print("=" * 80)
print("Fusion Sheet 结构分析")
print("=" * 80)

df_raw = pd.read_excel(excel_file, sheet_name='Fusion', header=None)

print(f"\n总行数: {len(df_raw)}")
print("\n所有行内容:")

for i in range(len(df_raw)):
    row_data = df_raw.iloc[i, :5].tolist()
    print(f"Row {i}: {row_data}")

print("\n" + "=" * 80)

# 测试不同的skip_rows值
print("\n测试不同的skip_rows值:")
for skip in [0, 2, 4]:
    print(f"\nskip_rows={skip}:")
    df = pd.read_excel(excel_file, sheet_name='Fusion', skiprows=skip, nrows=3)
    print(f"  Columns: {list(df.columns)[:5]}")
    print(f"  Rows: {len(df)}")
    if len(df) > 0:
        print(f"  First row: {df.iloc[0, :5].tolist()}")
