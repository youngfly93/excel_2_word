#!/usr/bin/env python3
"""
Excel 知识库迁移到 SQLite

将现有的 Excel 知识库数据迁移到 SQLite 数据库。

用法：
    python scripts/migrate_excel_to_sqlite.py
    python scripts/migrate_excel_to_sqlite.py --input path/to/knowledge.xlsx --output data/knowledge.db
"""

import sys
import re
import argparse
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from reportgen.knowledge.sqlite_provider import SQLiteKnowledgeProvider


def norm_text(value) -> str:
    """规范化文本值"""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip()
    if s.lower() in ("nan", "none", "*", "-", ""):
        return ""
    return s


def migrate_gene_analysis(excel_path: str, db: SQLiteKnowledgeProvider) -> int:
    """迁移基因变异解析数据"""
    print("\n📊 迁移基因变异解析...")

    try:
        df = pd.read_excel(excel_path, sheet_name="基因变异解析")
    except Exception as e:
        print(f"   ⚠️  无法读取 '基因变异解析' sheet: {e}")
        return 0

    count = 0
    for _, row in df.iterrows():
        gene_name = norm_text(row.get("基因名称"))
        if not gene_name:
            continue

        gene_intro = norm_text(row.get("基因简介"))
        mutation_desc = norm_text(row.get("基因变异说明"))
        mutation_analysis = norm_text(row.get("基因变异解析"))

        if db.insert_gene_analysis(gene_name, gene_intro, mutation_desc, mutation_analysis):
            count += 1
            print(f"   ✅ {gene_name}")

    print(f"   共迁移 {count} 个基因")
    return count


def find_sheet_by_keyword(excel_path: str, keyword: str) -> str:
    """通过关键字模糊匹配 sheet 名称（处理隐藏字符）"""
    xl = pd.ExcelFile(excel_path)
    for name in xl.sheet_names:
        # 移除不可见字符后匹配
        clean_name = ''.join(c for c in name if c.isprintable() or c in '\n\t')
        if keyword in clean_name:
            return name
    return None


def find_column_by_keywords(columns, *keywords) -> str:
    """通过关键字模糊匹配列名（处理换行符等）"""
    for col in columns:
        col_str = str(col).replace('\n', '')
        if all(kw in col_str for kw in keywords):
            return col
    return None


def migrate_drug_tips(excel_path: str, db: SQLiteKnowledgeProvider) -> int:
    """迁移用药提示数据"""
    print("\n💊 迁移用药提示...")

    # 通过关键字查找 sheet（处理隐藏字符）
    sheet_name = find_sheet_by_keyword(excel_path, "靶向药物相关体细胞变异用药提示")
    if not sheet_name:
        sheet_name = find_sheet_by_keyword(excel_path, "用药提示")

    if not sheet_name:
        print("   ⚠️  未找到用药提示 sheet")
        return 0

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        print(f"   📄 读取 sheet: {repr(sheet_name)}")
    except Exception as e:
        print(f"   ⚠️  无法读取用药提示: {e}")
        return 0

    conn = db._get_connection()
    count = 0

    # 预先查找列名（处理换行符）
    benefit_col = find_column_by_keywords(df.columns, "获益", "药物")
    caution_col = find_column_by_keywords(df.columns, "耐药", "药物") or \
                  find_column_by_keywords(df.columns, "慎重", "药物")

    for _, row in df.iterrows():
        gene_name = norm_text(row.get("基因名称"))
        if not gene_name:
            continue

        variant_grade = norm_text(row.get("变异等级"))
        c_hgvs = norm_text(row.get("c_point"))
        p_hgvs = norm_text(row.get("p_point"))
        variant_type = norm_text(row.get("扩增/缺失/融合/胚系/未见突变"))

        benefit_drugs = norm_text(row.get(benefit_col)) if benefit_col else ""
        caution_drugs = norm_text(row.get(caution_col)) if caution_col else ""

        try:
            conn.execute(
                """INSERT INTO drug_tips
                   (gene_name, variant_grade, c_hgvs, p_hgvs, variant_type, benefit_drugs, caution_drugs)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (gene_name.upper(), variant_grade, c_hgvs, p_hgvs,
                 variant_type, benefit_drugs, caution_drugs)
            )
            count += 1
        except Exception as e:
            print(f"   ⚠️  插入失败 {gene_name}: {e}")

    conn.commit()
    print(f"   共迁移 {count} 条用药提示")
    return count


def migrate_drug_analysis(excel_path: str, db: SQLiteKnowledgeProvider) -> int:
    """
    迁移药物解析详情

    用药提示解析 sheet 结构（合并表头）:
    Row 0: 合并标题行 - 列5: "潜在获益靶向/免疫药物解析", 列9: "潜在负相关靶向/免疫药物解析"
    Row 1: 子标题行 - 列0-4: 基因信息, 列5-8: 获益药物解析, 列9-12: 负相关药物解析
    Row 2+: 数据

    列索引:
      0: 基因名称, 1: 变异等级, 2: c_point, 3: p_point, 4: 扩增/缺失/融合/胚系/未见突变
      5: 药物(获益), 6: 基因变异与药物关联分析(获益), 8: 药物疗效临床解析(获益)
      9: 药物(负相关), 10: 基因变异与药物关联分析(负相关), 12: 药物疗效临床解析(负相关)
    """
    print("\n🔬 迁移药物解析...")

    try:
        # 读取原始数据，不使用 header
        df = pd.read_excel(excel_path, sheet_name="用药提示解析", header=None)
    except Exception as e:
        print(f"   ⚠️  无法读取 '用药提示解析' sheet: {e}")
        return 0

    # 跳过前两行标题，从第3行开始是数据
    data_df = df.iloc[2:].reset_index(drop=True)
    print(f"   📄 数据行数: {len(data_df)}")

    count = 0
    conn = db._get_connection()

    for _, row in data_df.iterrows():
        gene_name = norm_text(row.iloc[0] if len(row) > 0 else None)
        if not gene_name or not re.match(r'^[A-Z][A-Z0-9/()]+', gene_name, re.IGNORECASE):
            continue

        gene_name = gene_name.upper()
        variant_grade = norm_text(row.iloc[1] if len(row) > 1 else None)
        c_point = norm_text(row.iloc[2] if len(row) > 2 else None)
        p_point = norm_text(row.iloc[3] if len(row) > 3 else None)

        # 获益药物解析 (列 5, 6, 8)
        benefit_drug = norm_text(row.iloc[5] if len(row) > 5 else None)
        benefit_relation = norm_text(row.iloc[6] if len(row) > 6 else None)
        benefit_clinical = norm_text(row.iloc[8] if len(row) > 8 else None)

        if benefit_drug and (benefit_relation or benefit_clinical):
            try:
                conn.execute(
                    """INSERT INTO drug_analysis
                       (gene_name, drug_name, drug_type, relation, clinical)
                       VALUES (?, ?, ?, ?, ?)""",
                    (gene_name, benefit_drug, "benefit", benefit_relation, benefit_clinical)
                )
                count += 1
            except Exception as e:
                print(f"   ⚠️  插入获益药物失败 {gene_name}/{benefit_drug}: {e}")

        # 负相关药物解析 (列 9, 10, 12)
        caution_drug = norm_text(row.iloc[9] if len(row) > 9 else None)
        caution_relation = norm_text(row.iloc[10] if len(row) > 10 else None)
        caution_clinical = norm_text(row.iloc[12] if len(row) > 12 else None)

        if caution_drug and (caution_relation or caution_clinical):
            try:
                conn.execute(
                    """INSERT INTO drug_analysis
                       (gene_name, drug_name, drug_type, relation, clinical)
                       VALUES (?, ?, ?, ?, ?)""",
                    (gene_name, caution_drug, "caution", caution_relation, caution_clinical)
                )
                count += 1
            except Exception as e:
                print(f"   ⚠️  插入负相关药物失败 {gene_name}/{caution_drug}: {e}")

    conn.commit()
    print(f"   共迁移 {count} 条药物解析")
    return count


def migrate_references(excel_path: str, db: SQLiteKnowledgeProvider) -> int:
    """迁移参考文献"""
    print("\n📚 迁移参考文献...")

    try:
        df = pd.read_excel(excel_path, sheet_name="参考文献")
    except Exception as e:
        print(f"   ⚠️  无法读取 '参考文献' sheet: {e}")
        return 0

    count = 0
    current_gene = None

    for _, row in df.iterrows():
        # 查找基因名称列
        for col in df.columns:
            if "基因" in str(col):
                val = norm_text(row.get(col))
                if val:
                    current_gene = val.upper()
                break

        # 查找参考文献列
        for col in df.columns:
            if "参考文献" in str(col):
                content = norm_text(row.get(col))
                if content:
                    # 提取 PMID
                    pmid_match = re.search(r'PMID[:\s]*(\d+)', content, re.IGNORECASE)
                    pmid = pmid_match.group(1) if pmid_match else None

                    # 提取 NCT
                    nct_match = re.search(r'NCT\d+', content, re.IGNORECASE)
                    nct_id = nct_match.group(0) if nct_match else None

                    db.insert_reference(
                        pmid=pmid,
                        nct_id=nct_id,
                        content=content,
                        related_genes=current_gene
                    )
                    count += 1
                break

    print(f"   共迁移 {count} 条参考文献")
    return count


def main():
    parser = argparse.ArgumentParser(
        description='Excel 知识库迁移到 SQLite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--input', '-i',
        default='2025.12.10/示例：+++自建肠癌基因数据库.xlsx',
        help='Excel 知识库文件路径'
    )
    parser.add_argument(
        '--output', '-o',
        default='data/knowledge.db',
        help='SQLite 数据库输出路径'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='覆盖已存在的数据库文件'
    )

    args = parser.parse_args()

    # 转换为绝对路径
    excel_path = project_root / args.input
    db_path = project_root / args.output

    print("=" * 60)
    print("Excel → SQLite 知识库迁移工具")
    print("=" * 60)

    if not excel_path.exists():
        print(f"❌ Excel 文件不存在: {excel_path}")
        return 1

    if db_path.exists():
        if args.force:
            db_path.unlink()
            print(f"🗑️  已删除旧数据库: {db_path}")
        else:
            print(f"⚠️  数据库已存在: {db_path}")
            print("   使用 --force 参数覆盖")
            return 1

    print(f"\n📂 输入: {excel_path}")
    print(f"💾 输出: {db_path}")

    # 创建数据库并迁移数据
    with SQLiteKnowledgeProvider(str(db_path)) as db:
        total = 0

        # 迁移各类数据
        total += migrate_gene_analysis(str(excel_path), db)
        total += migrate_drug_tips(str(excel_path), db)
        total += migrate_drug_analysis(str(excel_path), db)
        total += migrate_references(str(excel_path), db)

        # 显示统计
        print("\n" + "=" * 60)
        print("📊 迁移完成统计")
        print("=" * 60)
        stats = db.get_stats()
        for table, count in stats.items():
            print(f"   {table}: {count} 条")

    print(f"\n✅ 迁移完成！数据库保存至: {db_path}")
    print(f"   文件大小: {db_path.stat().st_size / 1024:.1f} KB")

    return 0


if __name__ == '__main__':
    sys.exit(main())
