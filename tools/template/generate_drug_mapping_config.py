#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成30个药物详细表格的mapping.yaml配置
"""

import json
import yaml
import re

def sanitize_drug_name(drug_name):
    """将药物名称转换为有效的Jinja2变量名"""
    name_mapping = {
        "顺铂": "shunbo", "卡铂": "kabo", "奥沙利铂": "aoshalibo",
        "铂类化合物": "boleihuahewu", "甲氨蝶呤": "jiaandieling",
        "紫杉醇": "zishanchun", "环磷酰胺": "huanlinyanan",
        "异环磷酰胺": "yihuanlinyanan", "伊立替康": "yilitikang",
        "依托泊苷": "yituopogan", "达卡巴嗪": "dakabazuo",
        "蒽环类": "genhuanlei", "博来霉素": "bolaimeisin",
        "卡培他滨": "kaipeibaibin", "5-Fu、氟嘧啶类": "fluorouracil",
        "吉西他滨": "jixitabin", "多西他赛": "duoxitasai",
        "培美曲塞": "peimeiqusai", "长春碱类": "changchunjianlei",
        "米托蒽醌": "mituogenquan", "三胺硫磷": "sananliulin",
        "马法兰": "mafalan", "替加氟/替吉奥": "tegafur",
        "阿糖胞苷": "atangbaoyin", "来曲唑/阿那曲唑": "letrozole_anastrozole",
        "地塞米松": "disaimisong", "强的松": "qiangdesong",
        "他莫昔芬": "tamoxifen", "依西美坦": "yiximeitang",
        "伊达比星": "yidabixing",
    }
    if drug_name in name_mapping:
        return f"drug_{name_mapping[drug_name]}"
    return f"drug_{re.sub(r'[^a-zA-Z0-9]+', '_', drug_name).strip('_').lower()}"

def generate_drug_table_config(drug_name, drug_var_name, ctdrug_matches):
    """生成单个药物表格的配置"""

    config = {
        'sheet_name': 'CtDrug',
        'required': False,
        'empty_behavior': 'hide_section',
        'table_format': 'detail',
        'filter': {
            'column': '药物',
            'values': ctdrug_matches  # 匹配的CtDrug药物名称列表
        },
        'columns': {
            'gene': {
                'synonyms': ['检测基因', 'Gene'],
                'type': 'string',
                'description': '检测基因'
            },
            'locus': {
                'synonyms': ['检测位点', 'Locus', 'Position'],
                'type': 'string',
                'description': '检测位点'
            },
            'genotype': {
                'synonyms': ['基因型', 'Genotype'],
                'type': 'string',
                'description': '基因型'
            },
            'level': {
                'synonyms': ['等级', 'Level', 'Evidence'],
                'type': 'string',
                'description': '证据等级'
            },
            'result': {
                'synonyms': ['用药提示', '检测结果', 'Result', 'Recommendation'],
                'type': 'string',
                'description': '检测结果/用药提示'
            },
            'reference': {
                'synonyms': ['参考文献', 'Reference', 'PMID'],
                'type': 'string',
                'description': '参考文献'
            }
        }
    }

    return config

def generate_all_drug_configs(drug_mapping_file):
    """生成所有药物的配置"""

    # 读取药物映射分析结果
    with open(drug_mapping_file, 'r', encoding='utf-8') as f:
        mapping_data = json.load(f)

    all_configs = {}

    for drug_info in mapping_data['mapping']:
        if drug_info['match_found']:
            drug_name = drug_info['report_drug']
            var_name = sanitize_drug_name(drug_name)
            ctdrug_matches = drug_info['ctdrug_matches']

            config = generate_drug_table_config(drug_name, var_name, ctdrug_matches)
            all_configs[var_name] = config

    return all_configs

def create_yaml_string(configs):
    """创建YAML格式的配置字符串"""

    yaml_str = "\n# ========== 化疗药物详细解析表（自动生成） ==========\n"
    yaml_str += "# 30个药物详细表格，每个药物一个表格\n"
    yaml_str += "# 格式：基因、检测位点、基因型、等级、检测结果、参考文献\n\n"

    for var_name, config in configs.items():
        yaml_str += f"  {var_name}:\n"
        yaml_str += f"    sheet_name: \"{config['sheet_name']}\"\n"
        yaml_str += f"    required: {str(config['required']).lower()}\n"
        yaml_str += f"    empty_behavior: \"{config['empty_behavior']}\"\n"
        yaml_str += f"    table_format: \"{config['table_format']}\"\n"

        # 添加filter配置
        yaml_str += f"    filter:\n"
        yaml_str += f"      column: \"{config['filter']['column']}\"\n"
        yaml_str += f"      values:\n"
        for value in config['filter']['values']:
            yaml_str += f"        - \"{value}\"\n"

        # 添加columns配置
        yaml_str += f"    columns:\n"
        for col_name, col_config in config['columns'].items():
            yaml_str += f"      {col_name}:\n"
            yaml_str += f"        synonyms: {col_config['synonyms']}\n"
            yaml_str += f"        type: {col_config['type']}\n"
            yaml_str += f"        description: \"{col_config['description']}\"\n"

        yaml_str += "\n"

    return yaml_str

def main():
    drug_mapping_file = 'drug_mapping_analysis.json'
    mapping_file = 'config/mapping.yaml'
    output_file = 'config/drug_tables_config.yaml'

    print("=" * 80)
    print("🔧 生成药物详细表格的mapping配置")
    print("=" * 80)
    print()

    # 生成所有配置
    print("📖 读取药物映射分析结果...")
    configs = generate_all_drug_configs(drug_mapping_file)
    print(f"✅ 生成了 {len(configs)} 个药物表格配置")

    # 创建YAML字符串
    print("\n🔧 生成YAML配置...")
    yaml_config = create_yaml_string(configs)

    # 保存到独立文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(yaml_config)
    print(f"✅ 配置已保存到: {output_file}")

    # 显示配置的药物列表
    print("\n📋 配置的药物列表:")
    for i, var_name in enumerate(configs.keys(), 1):
        drug_name = var_name.replace('drug_', '')
        filter_values = configs[var_name]['filter']['values']
        print(f"  {i}. {drug_name}: 匹配 {len(filter_values)} 个CtDrug变体")

    print("\n💡 提示:")
    print(f"  1. 独立配置文件: {output_file}")
    print(f"  2. 将此配置添加到 {mapping_file} 的 table_data 部分")
    print(f"  3. 添加位置：在现有表格配置之后")

    # 提供合并指令
    print("\n📝 合并到mapping.yaml的命令:")
    print(f"  cat {output_file} >> {mapping_file}")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
