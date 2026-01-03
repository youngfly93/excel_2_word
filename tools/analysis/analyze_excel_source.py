#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度分析Excel数据源
识别所有Sheet的结构、用途和映射关系
"""

import pandas as pd
import json
import sys
from pathlib import Path

def analyze_excel_structure(excel_path):
    """分析Excel文件的完整结构"""

    print(f"📊 读取Excel文件: {excel_path}")

    # 读取所有Sheets
    all_sheets = pd.read_excel(excel_path, sheet_name=None)

    analysis = {
        "file": excel_path,
        "total_sheets": len(all_sheets),
        "sheets": []
    }

    print(f"✅ 找到 {len(all_sheets)} 个Sheet\n")

    # 分析每个Sheet
    for sheet_name, df in all_sheets.items():
        print(f"{'='*80}")
        print(f"Sheet: {sheet_name}")
        print(f"{'='*80}")

        sheet_info = {
            "name": sheet_name,
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
            "sample_data": [],
            "data_types": {},
            "purpose": "unknown",
            "used_for": []
        }

        # 数据类型统计
        for col in df.columns:
            dtype = str(df[col].dtype)
            non_null = df[col].notna().sum()
            sheet_info["data_types"][col] = {
                "dtype": dtype,
                "non_null_count": int(non_null),
                "null_count": int(len(df) - non_null)
            }

        # 提取前5行作为样本
        sample_rows = df.head(5).to_dict('records')
        for i, row in enumerate(sample_rows):
            # 转换为可序列化格式
            clean_row = {}
            for k, v in row.items():
                if pd.isna(v):
                    clean_row[k] = None
                elif isinstance(v, (int, float, str, bool)):
                    clean_row[k] = v
                else:
                    clean_row[k] = str(v)
            sheet_info["sample_data"].append(clean_row)

        # 推断Sheet用途
        sheet_info["purpose"] = infer_sheet_purpose(sheet_name, df)

        # 显示基本信息
        print(f"  行数: {len(df)}")
        print(f"  列数: {len(df.columns)}")
        print(f"  用途: {sheet_info['purpose']}")
        print(f"  列名: {', '.join([str(c) for c in list(df.columns)[:5]])}{'...' if len(df.columns) > 5 else ''}")

        analysis["sheets"].append(sheet_info)
        print()

    return analysis

def infer_sheet_purpose(sheet_name, df):
    """推断Sheet的用途"""

    sheet_lower = sheet_name.lower()
    columns = [str(col).lower() for col in df.columns]

    # 基因变异相关
    if 'variation' in sheet_lower or 'variant' in sheet_lower:
        return "基因变异明细表（用于报告表格2和表格4）"

    # TMB相关
    if 'tmb' in sheet_lower:
        return "TMB（肿瘤突变负荷）数据（用于报告单值字段）"

    # MSI相关
    if 'msi' in sheet_lower or 'microsatellite' in sheet_lower:
        return "MSI（微卫星不稳定性）数据（用于报告单值字段）"

    # 化疗药物相关
    if 'ctdrug' in sheet_lower or 'chemo' in sheet_lower or 'drug' in sheet_lower:
        return "化疗药物数据（用于报告表格5和详细解析表）"

    # CNV拷贝数变异
    if 'cnv' in sheet_lower or 'copy' in sheet_lower:
        return "CNV拷贝数变异数据"

    # 融合基因
    if 'fusion' in sheet_lower:
        return "基因融合数据"

    # HLA相关
    if 'hla' in sheet_lower:
        return "HLA（人类白细胞抗原）分型数据"

    # 质控相关
    if 'qc' in sheet_lower or 'quality' in sheet_lower:
        return "质量控制数据"

    # 其他
    if any('gene' in col for col in columns):
        return "基因相关数据"

    return "待确认用途"

def map_to_report_fields(analysis):
    """映射到报告字段"""

    field_mapping = {
        "single_values": [],
        "table_data": []
    }

    for sheet in analysis["sheets"]:
        sheet_name = sheet["name"]

        # TMB数据 -> 单值字段
        if 'TMB' in sheet_name:
            field_mapping["single_values"].append({
                "source_sheet": sheet_name,
                "target_field": "tmb_value",
                "description": "TMB值（Muts/Mb）",
                "extraction_method": "从TMB表提取数值",
                "report_location": "报告表格3 - TMB行"
            })

        # MSI数据 -> 单值字段
        if 'Msi' in sheet_name:
            field_mapping["single_values"].append({
                "source_sheet": sheet_name,
                "target_field": "msi_status",
                "description": "MSI状态（MSS/MSI-L/MSI-H）",
                "extraction_method": "从Msisensor表计算",
                "report_location": "报告表格3 - MSI行"
            })

        # Variations -> 表格数据
        if 'Variation' in sheet_name:
            field_mapping["table_data"].append({
                "source_sheet": sheet_name,
                "target_table": "variants（表格2、表格4）",
                "rows": sheet["rows"],
                "key_columns": [col for col in sheet["column_names"] if 'Gene' in col or 'HGVS' in col or 'Freq' in col],
                "description": "基因变异明细数据",
                "report_location": "报告表格2（简表）和表格4（详表）"
            })

        # CtDrug -> 表格数据
        if 'CtDrug' in sheet_name:
            field_mapping["table_data"].append({
                "source_sheet": sheet_name,
                "target_table": "chemotherapy（表格5）",
                "rows": sheet["rows"],
                "key_columns": [col for col in sheet["column_names"] if '药物' in col or 'Drug' in col or '基因' in col],
                "description": "化疗药物数据",
                "report_location": "报告表格5（化疗药物表）"
            })

    return field_mapping

def identify_unused_data(analysis):
    """识别未被使用的Excel数据"""

    unused = []

    # 常见映射的Sheet
    mapped_sheets = ['Variations', 'CtDrug', 'TMB', 'Msisensor']

    for sheet in analysis["sheets"]:
        is_used = any(mapped in sheet["name"] for mapped in mapped_sheets)

        if not is_used and sheet["rows"] > 0:
            unused.append({
                "sheet": sheet["name"],
                "rows": sheet["rows"],
                "columns": sheet["columns"],
                "potential_use": sheet["purpose"]
            })

    return unused

def main():
    if len(sys.argv) < 2:
        print("用法: python analyze_excel_source.py <excel文件路径>")
        sys.exit(1)

    excel_path = sys.argv[1]

    print("=" * 80)
    print("📊 Excel数据源深度分析")
    print("=" * 80)

    # 分析Excel结构
    analysis = analyze_excel_structure(excel_path)

    # 映射到报告字段
    print("\n" + "=" * 80)
    print("🔗 Excel → 报告字段映射")
    print("=" * 80)
    field_mapping = map_to_report_fields(analysis)

    print("\n【单值字段映射】")
    for mapping in field_mapping["single_values"]:
        print(f"  • {mapping['source_sheet']} → {mapping['target_field']}")
        print(f"    描述: {mapping['description']}")
        print(f"    位置: {mapping['report_location']}")
        print()

    print("【表格数据映射】")
    for mapping in field_mapping["table_data"]:
        print(f"  • {mapping['source_sheet']} → {mapping['target_table']}")
        print(f"    行数: {mapping['rows']}")
        print(f"    关键列: {', '.join(mapping['key_columns'][:3])}...")
        print(f"    位置: {mapping['report_location']}")
        print()

    # 识别未使用数据
    unused = identify_unused_data(analysis)
    if unused:
        print("\n" + "=" * 80)
        print("⚠️  未被使用的Excel数据")
        print("=" * 80)
        for item in unused:
            print(f"  • {item['sheet']}: {item['rows']}行 x {item['columns']}列")
            print(f"    潜在用途: {item['potential_use']}")
            print()

    # 保存详细分析结果
    output_file = "excel_source_analysis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "analysis": analysis,
            "field_mapping": field_mapping,
            "unused_data": unused
        }, f, ensure_ascii=False, indent=2)

    print("=" * 80)
    print(f"✅ 详细分析结果已保存到: {output_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
