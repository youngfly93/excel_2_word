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


def migrate_drug_tips(excel_path: str, db: SQLiteKnowledgeProvider) -> int:
    """迁移用药提示数据"""
    print("\n💊 迁移用药提示...")

    try:
        # 尝试不同的 sheet 名称
        for sheet_name in ["靶向药物相关体细胞变异用药提示", "用药提示"]:
            try:
                df = pd.read_excel(excel_path, sheet_name=sheet_name)
                break
            except Exception:
                continue
        else:
            print("   ⚠️  未找到用药提示 sheet")
            return 0
    except Exception as e:
        print(f"   ⚠️  无法读取用药提示: {e}")
        return 0

    conn = db._get_connection()
    count = 0

    for _, row in df.iterrows():
        gene_name = norm_text(row.get("基因名称"))
        if not gene_name:
            continue

        variant_grade = norm_text(row.get("变异等级"))
        c_hgvs = norm_text(row.get("c_point"))
        p_hgvs = norm_text(row.get("p_point"))
        variant_type = norm_text(row.get("扩增/缺失/融合/胚系/未见突变"))

        # 查找获益药物列
        benefit_drugs = ""
        for col in df.columns:
            if "获益" in str(col) and "药物" in str(col):
                benefit_drugs = norm_text(row.get(col))
                break

        # 查找慎用药物列
        caution_drugs = ""
        for col in df.columns:
            if ("耐药" in str(col) or "慎重" in str(col)) and "药物" in str(col):
                caution_drugs = norm_text(row.get(col))
                break

        try:
            conn.execute(
                """INSERT INTO drug_tips
                   (gene_name, variant_grade, c_hgvs, p_hgvs, variant_type, benefit_drugs, caution_drugs)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (gene_name.upper(), variant_grade, c_hgvs, p_hgvs,
                 variant_type, benefit_drugs, caution_drugs)
            )
            count += 1
        except Exception:
            pass

    conn.commit()
    print(f"   共迁移 {count} 条用药提示")
    return count


def migrate_drug_analysis(excel_path: str, db: SQLiteKnowledgeProvider) -> int:
    """迁移药物解析详情"""
    print("\n🔬 迁移药物解析...")

    try:
        df = pd.read_excel(excel_path, sheet_name="用药提示解析")
    except Exception as e:
        print(f"   ⚠️  无法读取 '用药提示解析' sheet: {e}")
        return 0

    count = 0
    current_gene = None
    current_drug = None
    current_type = None

    for _, row in df.iterrows():
        # 尝试找基因名
        for col in df.columns:
            val = norm_text(row.get(col))
            if val and re.match(r'^[A-Z][A-Z0-9]+$', val):
                current_gene = val
                break

        # 尝试找药物解析内容
        for col in df.columns:
            col_str = str(col)
            val = norm_text(row.get(col))

            if "获益" in col_str and val:
                current_type = "benefit"
            elif ("耐药" in col_str or "慎重" in col_str or "负相关" in col_str) and val:
                current_type = "caution"

            if "关联分析" in val or "临床解析" in val:
                continue

            if current_gene and current_type and len(val) > 50:
                # 这可能是一段解析内容
                if "关联" in col_str:
                    db.insert_drug_analysis(
                        current_gene, current_drug or "未知",
                        current_type, val, ""
                    )
                    count += 1
                elif "临床" in col_str:
                    db.insert_drug_analysis(
                        current_gene, current_drug or "未知",
                        current_type, "", val
                    )
                    count += 1

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
