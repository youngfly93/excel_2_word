#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析CtDrug表与手工报告药物表格的映射关系
"""

import pandas as pd
import json

def analyze_ctdrug(excel_path, drug_list_file):
    """分析CtDrug表的药物分布"""

    # 读取CtDrug表
    print("📊 读取CtDrug表...")
    ctdrug_df = pd.read_excel(excel_path, sheet_name='CtDrug')
    print(f"✅ CtDrug表: {len(ctdrug_df)}行 x {len(ctdrug_df.columns)}列\n")

    # 读取药物列表
    with open(drug_list_file, 'r', encoding='utf-8') as f:
        drug_data = json.load(f)

    drug_list = drug_data['drug_list']
    print(f"📋 手工报告药物列表: {len(drug_list)}个药物\n")

    # 统计CtDrug表中的药物分布
    print("🔍 分析CtDrug表中的药物分布...")
    drug_column = '药物'
    unique_drugs = ctdrug_df[drug_column].unique()
    print(f"✅ CtDrug表中唯一药物数: {len(unique_drugs)}\n")

    # 药物匹配
    mapping = []

    for drug_info in drug_list:
        drug_name = drug_info['name']

        # 在CtDrug表中查找匹配的药物
        matched_rows = []
        for ct_drug in unique_drugs:
            # 模糊匹配：检查是否包含关键词
            if match_drug_name(drug_name, str(ct_drug)):
                matched_rows.append(ct_drug)

        # 统计该药物的行数
        total_rows = 0
        for matched_drug in matched_rows:
            total_rows += len(ctdrug_df[ctdrug_df[drug_column] == matched_drug])

        mapping.append({
            "report_drug": drug_name,
            "report_table": drug_info['table_index'],
            "report_rows": drug_info['rows'],
            "ctdrug_matches": matched_rows,
            "ctdrug_total_rows": total_rows,
            "match_found": len(matched_rows) > 0
        })

        print(f"📋 {drug_name}:")
        print(f"   手工报告: 表格{drug_info['table_index']}, {drug_info['rows']}行")
        if matched_rows:
            print(f"   CtDrug匹配: {len(matched_rows)}个变体, 共{total_rows}行")
            for m in matched_rows[:3]:
                print(f"      - {m}")
            if len(matched_rows) > 3:
                print(f"      ... 还有{len(matched_rows)-3}个")
        else:
            print(f"   ⚠️  CtDrug未找到匹配")
        print()

    # 保存映射结果
    output = {
        "ctdrug_total_rows": len(ctdrug_df),
        "ctdrug_unique_drugs": len(unique_drugs),
        "report_drug_count": len(drug_list),
        "mapping": mapping
    }

    output_file = "drug_mapping_analysis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("=" * 80)
    print(f"✅ 映射分析已保存到: {output_file}")
    print("=" * 80)

    # 统计
    matched_count = sum(1 for m in mapping if m['match_found'])
    print(f"\n📊 统计:")
    print(f"   报告药物数: {len(drug_list)}")
    print(f"   匹配成功: {matched_count}")
    print(f"   匹配失败: {len(drug_list) - matched_count}")

def match_drug_name(report_drug, ctdrug_name):
    """药物名称模糊匹配"""

    # 移除空格和特殊字符
    report_clean = report_drug.replace(' ', '').replace('、', '').replace('/', '').lower()
    ct_clean = ctdrug_name.replace(' ', '').replace('（', '(').replace('）', ')').lower()

    # 提取关键词
    keywords = []

    # 从手工报告药物名提取关键词
    if '顺铂' in report_drug:
        keywords.append('顺铂')
        keywords.append('cisplatin')
    elif '卡铂' in report_drug:
        keywords.append('卡铂')
        keywords.append('carboplatin')
    elif '奥沙利铂' in report_drug:
        keywords.append('奥沙利铂')
        keywords.append('oxaliplatin')
    elif '铂类' in report_drug:
        keywords.append('铂')
        keywords.append('platin')
    elif '甲氨蝶呤' in report_drug:
        keywords.append('甲氨蝶呤')
        keywords.append('methotrexate')
    elif '紫杉醇' in report_drug:
        keywords.append('紫杉醇')
        keywords.append('paclitaxel')
    elif '环磷酰胺' in report_drug and '异环' not in report_drug:
        keywords.append('环磷酰胺')
        keywords.append('cyclophosphamide')
    elif '异环磷酰胺' in report_drug:
        keywords.append('异环磷酰胺')
        keywords.append('ifosfamide')
    elif '伊立替康' in report_drug:
        keywords.append('伊立替康')
        keywords.append('irinotecan')
    elif '依托泊苷' in report_drug:
        keywords.append('依托泊苷')
        keywords.append('etoposide')
    elif '达卡巴嗪' in report_drug:
        keywords.append('达卡巴嗪')
        keywords.append('dacarbazine')
    elif '蒽环类' in report_drug:
        keywords.append('蒽环')
        keywords.append('anthracycline')
    elif '博来霉素' in report_drug:
        keywords.append('博来霉素')
        keywords.append('bleomycin')
    elif '卡培他滨' in report_drug:
        keywords.append('卡培他滨')
        keywords.append('capecitabine')
    elif '5-fu' in report_clean or '氟尿嘧啶' in report_drug or '氟嘧啶' in report_drug:
        keywords.append('5-fu')
        keywords.append('氟尿嘧啶')
        keywords.append('fluorouracil')
    elif '曲氟尿苷' in report_drug or '替吡嘧啶' in report_drug:
        keywords.append('曲氟尿苷')
        keywords.append('trifluridine')
        keywords.append('替吡嘧啶')
        keywords.append('tipiracil')
    elif '替莫唑胺' in report_drug:
        keywords.append('替莫唑胺')
        keywords.append('temozolomide')
    elif '吉西他滨' in report_drug:
        keywords.append('吉西他滨')
        keywords.append('gemcitabine')
    elif '多西他赛' in report_drug:
        keywords.append('多西他赛')
        keywords.append('docetaxel')
    elif '培美曲塞' in report_drug:
        keywords.append('培美曲塞')
        keywords.append('pemetrexed')
    elif '长春碱' in report_drug or '长春' in report_drug:
        keywords.append('长春')
        keywords.append('vinc')
    elif '米托蒽醌' in report_drug:
        keywords.append('米托蒽醌')
        keywords.append('mitoxantrone')
    elif '三胺硫磷' in report_drug:
        keywords.append('三胺硫磷')
        keywords.append('thiotepa')
    elif '马法兰' in report_drug:
        keywords.append('马法兰')
        keywords.append('melphalan')
    elif '替加氟' in report_drug or '替吉奥' in report_drug:
        keywords.append('替加氟')
        keywords.append('tegafur')
        keywords.append('替吉奥')
    elif '阿糖胞苷' in report_drug:
        keywords.append('阿糖胞苷')
        keywords.append('cytarabine')
    elif '来曲唑' in report_drug or '阿那曲唑' in report_drug:
        keywords.append('曲唑')
        keywords.append('letrozole')
        keywords.append('anastrozole')
    elif '地塞米松' in report_drug:
        keywords.append('地塞米松')
        keywords.append('dexamethasone')
    elif '强的松' in report_drug:
        keywords.append('强的松')
        keywords.append('prednisone')
    elif '他莫昔芬' in report_drug:
        keywords.append('他莫昔芬')
        keywords.append('tamoxifen')
    elif '依西美坦' in report_drug:
        keywords.append('依西美坦')
        keywords.append('exemestane')
    elif '伊达比星' in report_drug:
        keywords.append('伊达比星')
        keywords.append('idarubicin')
    else:
        # 使用原始名称
        keywords.append(report_clean)

    # 检查是否匹配
    for keyword in keywords:
        if keyword.lower() in ct_clean:
            return True

    return False

def main():
    import sys

    if len(sys.argv) < 3:
        print("用法: python analyze_ctdrug_mapping.py <excel文件> <drug_tables_analysis.json>")
        sys.exit(1)

    excel_path = sys.argv[1]
    drug_list_file = sys.argv[2]

    print("=" * 80)
    print("🔗 分析CtDrug表与药物表格的映射关系")
    print("=" * 80)
    print()

    analyze_ctdrug(excel_path, drug_list_file)

if __name__ == "__main__":
    main()
