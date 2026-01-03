#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复mapping.yaml结构

将CNV/Fusion/HLA配置移动到table_data section内
"""

def fix_mapping_structure():
    """修复mapping.yaml结构"""

    print("=" * 80)
    print("修复mapping.yaml结构")
    print("=" * 80)

    mapping_file = "config/mapping.yaml"
    backup_file = "config/mapping.yaml.backup"

    # 读取原文件
    print(f"\n📂 读取文件: {mapping_file}")
    with open(mapping_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    print(f"✅ 文件读取成功: {len(lines)} 行")

    # 备份原文件
    print(f"\n💾 创建备份: {backup_file}")
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"✅ 备份完成")

    # 找到关键位置
    # 1. table_data section最后一个表格的结尾（插入点）
    # 2. CNV/Fusion/HLA section的开始和结束

    # 找到"# VALIDATION RULES"注释的位置（这之前是table_data的结尾）
    insert_line = None
    for i, line in enumerate(lines):
        if "# VALIDATION RULES" in line:
            insert_line = i  # 在VALIDATION注释之前插入
            break

    if insert_line is None:
        print("❌ 未找到插入点（VALIDATION RULES注释）")
        return False

    print(f"\n📍 找到插入点: 第 {insert_line + 1} 行")

    # 找到CNV/Fusion/HLA section (找到注释"# ========== CNV、Fusion、HLA表格映射配置 ==========")
    cnv_start = None
    cnv_end = None

    for i, line in enumerate(lines):
        if "# ========== CNV、Fusion、HLA表格映射配置 ==========" in line:
            cnv_start = i  # 包含注释行
            print(f"\n📍 找到CNV section开始: 第 {cnv_start + 1} 行")
            break

    if cnv_start is None:
        print("❌ 未找到CNV/Fusion/HLA section")
        return False

    # 找到CNV section的结束（下一个top-level section "data_cleaning:"）
    for i in range(cnv_start + 1, len(lines)):
        if lines[i].startswith("data_cleaning:"):
            cnv_end = i  # 不包含data_cleaning行
            print(f"📍 找到CNV section结束: 第 {cnv_end} 行 (data_cleaning前)")
            break

    if cnv_end is None:
        print("❌ 未找到CNV section结束")
        return False

    # 提取CNV/Fusion/HLA section
    cnv_section = lines[cnv_start:cnv_end]
    print(f"\n📦 提取CNV/Fusion/HLA section: {len(cnv_section)} 行")
    print(f"   从第 {cnv_start + 1} 行到第 {cnv_end} 行")

    # 构建新文件
    new_lines = []

    # 1. 添加开头到插入点
    new_lines.extend(lines[:insert_line])

    # 2. 插入CNV/Fusion/HLA section
    new_lines.append("\n")  # 添加空行分隔
    new_lines.extend(cnv_section)

    # 3. 添加validation section之后的内容（跳过原来的CNV section）
    # 从insert_line到cnv_start（validation和其他sections）
    new_lines.extend(lines[insert_line:cnv_start])

    # 从cnv_end到文件结尾（data_cleaning和metadata）
    new_lines.extend(lines[cnv_end:])

    print(f"\n✏️  构建新文件: {len(new_lines)} 行")

    # 写入新文件
    print(f"\n💾 写入修复后的文件: {mapping_file}")
    with open(mapping_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"✅ 文件修复完成!")

    # 验证行数变化
    print(f"\n📊 行数对比:")
    print(f"   原文件: {len(lines)} 行")
    print(f"   新文件: {len(new_lines)} 行")
    print(f"   差异: {len(new_lines) - len(lines)} 行")

    print("\n" + "=" * 80)
    print("✅ mapping.yaml结构修复完成!")
    print("=" * 80)

    return True


if __name__ == "__main__":
    fix_mapping_structure()
