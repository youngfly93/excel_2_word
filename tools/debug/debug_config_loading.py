#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试mapping.yaml配置加载

检查skip_rows配置是否正确加载
"""

import yaml
import os

def debug_config():
    """调试配置加载"""

    print("=" * 80)
    print("调试mapping.yaml配置加载")
    print("=" * 80)

    mapping_file = "config/mapping.yaml"

    if not os.path.exists(mapping_file):
        print(f"❌ 配置文件不存在: {mapping_file}")
        return

    print(f"\n📂 读取配置文件: {mapping_file}")

    with open(mapping_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    print(f"✅ 配置文件加载成功")

    # 检查top-level keys
    print(f"\n【Top-level配置项】")
    for key in config.keys():
        print(f"   - {key}")

    # 检查table_data
    table_data = config.get('table_data', {})
    print(f"\n【table_data配置】")
    print(f"   表格数量: {len(table_data)}")

    # 列出所有表格名（只显示前10个和最后10个）
    table_names = list(table_data.keys())
    print(f"\n   前10个表格:")
    for name in table_names[:10]:
        print(f"      - {name}")

    print(f"\n   最后10个表格:")
    for name in table_names[-10:]:
        print(f"      - {name}")

    # 检查CNV/Fusion/HLA是否存在
    print(f"\n【检查CNV/Fusion/HLA表格】")
    for table_name in ['cnv', 'fusion', 'hla']:
        if table_name in table_data:
            table_config = table_data[table_name]
            print(f"   ✅ {table_name}:")
            print(f"      sheet_name: {table_config.get('sheet_name')}")
            print(f"      skip_rows: {table_config.get('skip_rows')}")
            print(f"      required: {table_config.get('required')}")
            print(f"      empty_behavior: {table_config.get('empty_behavior')}")
        else:
            print(f"   ❌ {table_name}: 未找到")

    # 检查所有包含skip_rows的表格
    print(f"\n【所有包含skip_rows配置的表格】")
    skip_rows_tables = {
        name: config.get('skip_rows')
        for name, config in table_data.items()
        if config.get('skip_rows') is not None
    }

    if skip_rows_tables:
        for name, skip_count in skip_rows_tables.items():
            print(f"   - {name}: skip {skip_count} rows (sheet: {table_data[name].get('sheet_name')})")
    else:
        print(f"   ⚠️  没有表格配置了skip_rows")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    debug_config()
