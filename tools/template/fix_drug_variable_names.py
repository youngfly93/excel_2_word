#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正药物变量名，使其符合Jinja2规范
"""

import json
import re

def sanitize_drug_name(drug_name):
    """
    将药物名称转换为有效的Jinja2变量名

    规则:
    - 移除所有中文标点和特殊字符
    - 仅保留英文字母、数字、下划线
    - 转换为小写
    """
    # 定义药物名称到变量名的映射
    name_mapping = {
        "顺铂": "shunbo",
        "卡铂": "kabo",
        "奥沙利铂": "aoshalibo",
        "铂类化合物": "boleihuahewu",
        "甲氨蝶呤": "jiaandieling",
        "紫杉醇": "zishanchun",
        "环磷酰胺": "huanlinyanan",
        "异环磷酰胺": "yihuanlinyanan",
        "伊立替康": "yilitikang",
        "依托泊苷": "yituopogan",
        "达卡巴嗪": "dakabazuo",
        "蒽环类": "genhuanlei",
        "博来霉素": "bolaimei素",
        "卡培他滨": "kaipeibaibin",
        "5-Fu、氟嘧啶类": "fluorouracil",
        "曲氟尿苷盐酸/替吡嘧啶": "trifluridine_tipiracil",
        "替莫唑胺": "timozuo胺",
        "吉西他滨": "jixitabin",
        "多西他赛": "duoxitasai",
        "培美曲塞": "peimeiqusai",
        "长春碱类": "changchunjianl类",
        "米托蒽醌": "mituogenquan",
        "三胺硫磷": "sananliulin",
        "马法兰": "mafalan",
        "替加氟/替吉奥": "tegafur",
        "阿糖胞苷": "atangbaoyin",
        "来曲唑/阿那曲唑": "letrozole_anastrozole",
        "地塞米松": "disaimisong",
        "强的松": "qiangdesong",
        "他莫昔芬": "tamoxifen",
        "依西美坦": "yiximeitang",
        "伊达比星": "yidabixing",
    }

    # 使用预定义映射或自动转换
    if drug_name in name_mapping:
        clean_name = name_mapping[drug_name]
    else:
        # 移除所有非英文字母数字的字符
        clean_name = re.sub(r'[^a-zA-Z0-9]+', '_', drug_name).strip('_').lower()

    return f"drug_{clean_name}"

def update_drug_mapping_config(mapping_file, output_file):
    """更新药物映射配置中的变量名"""

    with open(mapping_file, 'r', encoding='utf-8') as f:
        mapping_data = json.load(f)

    # 创建新旧变量名映射表
    name_changes = {}

    for drug_info in mapping_data['mapping']:
        if drug_info['match_found']:
            drug_name = drug_info['report_drug']
            old_var_name = f"drug_{drug_name}"
            new_var_name = sanitize_drug_name(drug_name)

            if old_var_name != new_var_name:
                name_changes[old_var_name] = {
                    'new_name': new_var_name,
                    'drug_name': drug_name
                }

    # 保存映射表
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(name_changes, f, ensure_ascii=False, indent=2)

    return name_changes

def main():
    mapping_file = 'drug_mapping_analysis.json'
    output_file = 'drug_variable_name_mapping.json'

    print("=" * 80)
    print("🔧 修正药物变量名")
    print("=" * 80)
    print()

    # 生成变量名映射
    name_changes = update_drug_mapping_config(mapping_file, output_file)

    print(f"✅ 找到 {len(name_changes)} 个需要修正的变量名")
    print(f"📋 映射表已保存到: {output_file}")
    print()

    # 显示修改列表
    print("🔄 变量名修改列表:")
    for old_name, info in name_changes.items():
        print(f"  {old_name} -> {info['new_name']}")
        print(f"    ({info['drug_name']})")

    print()
    print("⚠️  下一步需要:")
    print("  1. 重新生成模板文件（使用新的变量名）")
    print("  2. 重新生成mapping.yaml配置（使用新的变量名）")
    print("=" * 80)

if __name__ == '__main__':
    main()
