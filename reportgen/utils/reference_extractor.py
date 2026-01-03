"""
参考文献提取工具

功能：
1. 从文本中提取 PMID 引用
2. 从文本中提取 NCT 临床试验号
3. 支持多种格式识别
"""

import re
from typing import List, Set, Tuple


def extract_pmids(text: str) -> List[str]:
    """
    从文本中提取 PubMed ID

    支持格式：
    - [19407794]
    - PMID:19407794
    - PMID: 19407794
    - (PMID 19407794)

    Args:
        text: 输入文本

    Returns:
        去重后的 PMID 列表（保持顺序）
    """
    if not text:
        return []

    pmids: List[str] = []
    seen: Set[str] = set()

    # 模式1: [数字] 格式（7-8位数字，典型PMID长度）
    pattern1 = r'\[(\d{7,8})\]'
    for match in re.finditer(pattern1, text):
        pmid = match.group(1)
        if pmid not in seen:
            pmids.append(pmid)
            seen.add(pmid)

    # 模式2: PMID:数字 或 PMID: 数字 格式
    pattern2 = r'PMID[:\s]+(\d{7,8})'
    for match in re.finditer(pattern2, text, re.IGNORECASE):
        pmid = match.group(1)
        if pmid not in seen:
            pmids.append(pmid)
            seen.add(pmid)

    # 模式3: (PMID 数字) 格式
    pattern3 = r'\(PMID\s+(\d{7,8})\)'
    for match in re.finditer(pattern3, text, re.IGNORECASE):
        pmid = match.group(1)
        if pmid not in seen:
            pmids.append(pmid)
            seen.add(pmid)

    return pmids


def extract_nct_ids(text: str) -> List[str]:
    """
    从文本中提取 NCT 临床试验号

    支持格式：
    - NCT02576444
    - NCT 02576444
    - (NCT02576444)

    Args:
        text: 输入文本

    Returns:
        去重后的 NCT ID 列表（保持顺序），格式统一为 NCTxxxxxxxx
    """
    if not text:
        return []

    nct_ids: List[str] = []
    seen: Set[str] = set()

    # 模式: NCT 后跟8位数字（允许中间有空格）
    pattern = r'NCT\s*(\d{8})'
    for match in re.finditer(pattern, text, re.IGNORECASE):
        nct_num = match.group(1)
        nct_id = f"NCT{nct_num}"
        if nct_id not in seen:
            nct_ids.append(nct_id)
            seen.add(nct_id)

    return nct_ids


def extract_all_references(text: str) -> Tuple[List[str], List[str]]:
    """
    提取文本中的所有参考文献标识

    Args:
        text: 输入文本

    Returns:
        (pmids, nct_ids) 元组
    """
    return extract_pmids(text), extract_nct_ids(text)


def extract_from_knowledge_base(knowledge_data: dict) -> Tuple[List[str], List[str]]:
    """
    从知识库数据中提取所有参考文献

    Args:
        knowledge_data: 知识库数据字典，包含:
            - gene_intro: 基因简介文本
            - mutation_desc: 变异说明
            - mutation_analysis: 变异解析
            - drug_info: 药物信息等

    Returns:
        (pmids, nct_ids) 元组
    """
    all_pmids: List[str] = []
    all_nct_ids: List[str] = []
    seen_pmids: Set[str] = set()
    seen_ncts: Set[str] = set()

    def collect_from_text(text: str):
        """从单个文本中收集引用"""
        if not text:
            return

        pmids, nct_ids = extract_all_references(text)

        for pmid in pmids:
            if pmid not in seen_pmids:
                all_pmids.append(pmid)
                seen_pmids.add(pmid)

        for nct_id in nct_ids:
            if nct_id not in seen_ncts:
                all_nct_ids.append(nct_id)
                seen_ncts.add(nct_id)

    # 递归遍历字典/列表中的所有字符串
    def traverse(obj):
        if isinstance(obj, str):
            collect_from_text(obj)
        elif isinstance(obj, dict):
            for value in obj.values():
                traverse(value)
        elif isinstance(obj, list):
            for item in obj:
                traverse(item)

    traverse(knowledge_data)

    return all_pmids, all_nct_ids


def format_reference_list(
    pmid_citations: dict,
    nct_citations: dict,
    style: str = "numbered"
) -> str:
    """
    格式化参考文献列表

    Args:
        pmid_citations: {pmid: citation_dict} 字典
        nct_citations: {nct_id: study_dict} 字典
        style: 格式风格 ("numbered", "plain")

    Returns:
        格式化的参考文献列表字符串
    """
    lines = []
    ref_num = 1

    # PMID 文献
    for pmid, citation in pmid_citations.items():
        if citation:
            if style == "numbered":
                title = citation.get("title", "")
                authors = citation.get("authors", [])
                journal = citation.get("journal", "")
                year = citation.get("year", "")

                author_str = ", ".join(authors[:3])
                if len(authors) > 3:
                    author_str += " et al."

                line = f"[{ref_num}] {author_str}. {title} {journal}. {year}. PMID:{pmid}"
                lines.append(line)
                ref_num += 1
            else:
                lines.append(f"PMID:{pmid} {citation.get('title', '')}")

    # NCT 试验
    for nct_id, study in nct_citations.items():
        if study:
            if style == "numbered":
                title = study.get("title", "") or study.get("brief_title", "")
                line = f"[{ref_num}] {title}. {nct_id}"
                lines.append(line)
                ref_num += 1
            else:
                title = study.get("brief_title", "") or study.get("title", "")
                lines.append(f"{nct_id} {title}")

    return "\n".join(lines)


def create_reference_mapping(
    pmid_citations: dict,
    nct_citations: dict
) -> dict:
    """
    创建引用编号映射表

    Args:
        pmid_citations: {pmid: citation_dict} 字典
        nct_citations: {nct_id: study_dict} 字典

    Returns:
        {原始ID: 编号} 映射字典
    """
    mapping = {}
    ref_num = 1

    for pmid in pmid_citations:
        mapping[pmid] = ref_num
        mapping[f"PMID:{pmid}"] = ref_num
        ref_num += 1

    for nct_id in nct_citations:
        mapping[nct_id] = ref_num
        ref_num += 1

    return mapping
