#!/usr/bin/env python3
"""
参考文献预加载脚本

功能：
1. 从知识库 Excel 文件中提取所有 PMID 和 NCT ID
2. 批量从 PubMed 和 ClinicalTrials.gov 获取文献信息
3. 保存到本地缓存文件

用法：
    python scripts/prefetch_references.py
    python scripts/prefetch_references.py --input data/gene_knowledge.xlsx
    python scripts/prefetch_references.py --dry-run  # 仅显示要获取的ID，不实际请求
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from reportgen.services.pubmed_service import PubMedService
from reportgen.services.clinicaltrials_service import ClinicalTrialsService
from reportgen.utils.reference_extractor import extract_pmids, extract_nct_ids


def extract_ids_from_excel(excel_path: str) -> tuple:
    """从 Excel 文件中提取所有 PMID 和 NCT ID"""
    import pandas as pd

    all_pmids = set()
    all_ncts = set()

    try:
        # 读取所有 sheet
        xls = pd.ExcelFile(excel_path)

        for sheet_name in xls.sheet_names:
            print(f"  扫描 sheet: {sheet_name}")
            df = pd.read_excel(xls, sheet_name=sheet_name)

            # 遍历所有单元格
            for col in df.columns:
                for value in df[col].dropna():
                    text = str(value)
                    pmids = extract_pmids(text)
                    ncts = extract_nct_ids(text)
                    all_pmids.update(pmids)
                    all_ncts.update(ncts)

    except Exception as e:
        print(f"  ⚠️  读取 Excel 失败: {e}")

    return sorted(all_pmids), sorted(all_ncts)


def extract_ids_from_text_file(file_path: str) -> tuple:
    """从文本文件中提取所有 PMID 和 NCT ID"""
    all_pmids = set()
    all_ncts = set()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
            pmids = extract_pmids(text)
            ncts = extract_nct_ids(text)
            all_pmids.update(pmids)
            all_ncts.update(ncts)
    except Exception as e:
        print(f"  ⚠️  读取文件失败: {e}")

    return sorted(all_pmids), sorted(all_ncts)


def main():
    parser = argparse.ArgumentParser(
        description='预加载参考文献到本地缓存',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--input', '-i',
        default=None,
        help='输入文件路径（Excel或文本文件）'
    )
    parser.add_argument(
        '--pubmed-cache',
        default='data/cache/pubmed_cache.json',
        help='PubMed 缓存文件路径'
    )
    parser.add_argument(
        '--nct-cache',
        default='data/cache/nct_cache.json',
        help='NCT 缓存文件路径'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅显示要获取的ID，不实际请求API'
    )
    parser.add_argument(
        '--pmids',
        nargs='+',
        default=[],
        help='直接指定 PMID 列表'
    )
    parser.add_argument(
        '--ncts',
        nargs='+',
        default=[],
        help='直接指定 NCT ID 列表'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("参考文献预加载工具")
    print("=" * 60)

    # 收集所有需要的 ID
    all_pmids = set(args.pmids)
    all_ncts = set(args.ncts)

    # 从输入文件提取
    if args.input:
        input_path = project_root / args.input
        if input_path.exists():
            print(f"\n📂 从文件提取: {input_path}")
            if input_path.suffix in ('.xlsx', '.xls'):
                pmids, ncts = extract_ids_from_excel(str(input_path))
            else:
                pmids, ncts = extract_ids_from_text_file(str(input_path))
            all_pmids.update(pmids)
            all_ncts.update(ncts)
        else:
            print(f"⚠️  文件不存在: {input_path}")

    # 默认扫描知识库目录
    if not args.input and not args.pmids and not args.ncts:
        # 扫描常见位置
        kb_paths = [
            project_root / 'data' / '基因知识库.xlsx',
            project_root / 'data' / 'gene_knowledge.xlsx',
            project_root / 'config' / 'knowledge_base.xlsx',
        ]

        for kb_path in kb_paths:
            if kb_path.exists():
                print(f"\n📂 从知识库提取: {kb_path}")
                pmids, ncts = extract_ids_from_excel(str(kb_path))
                all_pmids.update(pmids)
                all_ncts.update(ncts)

    print(f"\n📊 提取结果:")
    print(f"   PMID: {len(all_pmids)} 个")
    print(f"   NCT:  {len(all_ncts)} 个")

    if args.dry_run:
        print(f"\n📋 PMID 列表:")
        for pmid in sorted(all_pmids):
            print(f"   {pmid}")

        print(f"\n📋 NCT 列表:")
        for nct in sorted(all_ncts):
            print(f"   {nct}")

        print(f"\n⏹️  Dry-run 模式，未实际请求 API")
        return 0

    # 初始化服务
    pubmed_cache_path = project_root / args.pubmed_cache
    nct_cache_path = project_root / args.nct_cache

    pubmed_service = PubMedService(
        cache_path=str(pubmed_cache_path),
        auto_save=False  # 手动保存，提高效率
    )
    nct_service = ClinicalTrialsService(
        cache_path=str(nct_cache_path),
        auto_save=False
    )

    # 检查已缓存的数量
    cached_pmids = set(pubmed_service._cache.keys())
    cached_ncts = set(nct_service._cache.keys())

    new_pmids = all_pmids - cached_pmids
    new_ncts = all_ncts - cached_ncts

    print(f"\n📦 缓存状态:")
    print(f"   PMID: {len(cached_pmids)} 已缓存, {len(new_pmids)} 需获取")
    print(f"   NCT:  {len(cached_ncts)} 已缓存, {len(new_ncts)} 需获取")

    # 获取 PubMed 文献
    if new_pmids:
        print(f"\n🔄 正在获取 PubMed 文献...")
        success_count = 0
        fail_count = 0

        for i, pmid in enumerate(sorted(new_pmids), 1):
            print(f"   [{i}/{len(new_pmids)}] PMID:{pmid}", end=" ")
            result = pubmed_service.get_citation(pmid)
            if result:
                print(f"✅ {result.get('title', '')[:40]}...")
                success_count += 1
            else:
                print("❌ 获取失败")
                fail_count += 1

        print(f"\n   完成: {success_count} 成功, {fail_count} 失败")
        pubmed_service.save_cache()
        print(f"   💾 缓存已保存: {pubmed_cache_path}")

    # 获取 NCT 临床试验
    if new_ncts:
        print(f"\n🔄 正在获取 NCT 临床试验...")
        success_count = 0
        fail_count = 0

        for i, nct_id in enumerate(sorted(new_ncts), 1):
            print(f"   [{i}/{len(new_ncts)}] {nct_id}", end=" ")
            result = nct_service.get_study(nct_id)
            if result:
                title = result.get('brief_title', '') or result.get('title', '')
                print(f"✅ {title[:40]}...")
                success_count += 1
            else:
                print("❌ 获取失败")
                fail_count += 1

        print(f"\n   完成: {success_count} 成功, {fail_count} 失败")
        nct_service.save_cache()
        print(f"   💾 缓存已保存: {nct_cache_path}")

    print(f"\n✅ 预加载完成!")
    print(f"   PubMed 缓存: {len(pubmed_service._cache)} 条")
    print(f"   NCT 缓存:    {len(nct_service._cache)} 条")

    return 0


if __name__ == '__main__':
    sys.exit(main())
