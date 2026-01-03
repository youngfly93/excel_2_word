#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
颗粒化对齐工具

对比自动生成的报告和参考docx，进行颗粒级别的对齐分析。
确定差异是否都在可变区域（患者信息、样本数据等）。
"""

from docx import Document
from difflib import SequenceMatcher
import re
from typing import List, Dict, Tuple


class GranularAlignmentTool:
    """颗粒化对齐工具"""

    def __init__(self, generated_file: str, reference_file: str):
        """
        初始化

        Args:
            generated_file: 自动生成的报告文件路径
            reference_file: 参考报告文件路径
        """
        self.generated_file = generated_file
        self.reference_file = reference_file
        self.generated_doc = Document(generated_file)
        self.reference_doc = Document(reference_file)

        # 定义可变区域模式（这些内容预期会不同）
        self.variable_patterns = [
            # 患者信息
            r'姓名[：:]\s*\S+',
            r'性别[：:]\s*\S+',
            r'年龄[：:]\s*\d+',
            r'样本编号[：:]\s*\S+',
            r'病理诊断[：:]\s*.+',
            r'送检医院[：:]\s*.+',
            r'检测编号[：:]\s*\S+',
            r'报告日期[：:]\s*\d{4}[-/]\d{1,2}[-/]\d{1,2}',

            # 检测结果
            r'TMB[：:]\s*[\d.]+',
            r'MSI[：:]\s*\S+',
            r'HLA-[ABC][：:]\s*.+',
            r'\d+\.\d+%',  # 百分比
            r'chr\d+[：:]\d+',  # 染色体位置

            # 基因名称（大写字母）
            r'\b[A-Z][A-Z0-9]{2,}\b',  # 如 TP53, KRAS

            # 数值
            r'\d+\.\d+',
            r'\d+',
        ]

        # 固定区域关键词（这些应该相同）
        self.fixed_keywords = [
            '检测方法', '检测平台', '参考文献', '免责声明',
            '技术原理', '检测流程', '质量控制', '结果说明',
            '临床意义', '用药指导', '检测项目', '报告解读',
            '样本类型', '检测基因', '检测位点',
        ]

    def is_variable_content(self, text: str) -> bool:
        """
        判断文本是否为可变内容

        Args:
            text: 文本

        Returns:
            是否为可变内容
        """
        text = text.strip()

        # 空文本不算差异
        if not text:
            return True

        # 匹配可变模式
        for pattern in self.variable_patterns:
            if re.search(pattern, text):
                return True

        # 很短的文本（如单个数字）认为是可变的
        if len(text) < 3:
            return True

        return False

    def is_fixed_content(self, text: str) -> bool:
        """
        判断文本是否为固定内容

        Args:
            text: 文本

        Returns:
            是否为固定内容
        """
        text = text.strip()

        # 检查是否包含固定关键词
        for keyword in self.fixed_keywords:
            if keyword in text:
                return True

        # 长文本（说明性文字）通常是固定的
        if len(text) > 50:
            return True

        return False

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            相似度 (0-1)
        """
        return SequenceMatcher(None, text1, text2).ratio()

    def compare_paragraphs(self) -> Dict:
        """
        对比段落

        Returns:
            对比结果字典
        """
        gen_paras = [p.text.strip() for p in self.generated_doc.paragraphs if p.text.strip()]
        ref_paras = [p.text.strip() for p in self.reference_doc.paragraphs if p.text.strip()]

        results = {
            "total_generated": len(gen_paras),
            "total_reference": len(ref_paras),
            "differences": [],
            "variable_diffs": [],
            "fixed_diffs": [],
        }

        # 逐段落对比（对齐前N个段落）
        max_len = min(len(gen_paras), len(ref_paras))

        for i in range(max_len):
            gen_text = gen_paras[i]
            ref_text = ref_paras[i]

            similarity = self.calculate_similarity(gen_text, ref_text)

            if similarity < 1.0:  # 不完全相同
                diff_info = {
                    "index": i,
                    "generated": gen_text[:100],  # 前100字符
                    "reference": ref_text[:100],
                    "similarity": similarity,
                    "is_variable": self.is_variable_content(gen_text) or self.is_variable_content(ref_text),
                    "is_fixed": self.is_fixed_content(gen_text) and self.is_fixed_content(ref_text),
                }

                results["differences"].append(diff_info)

                # 分类
                if diff_info["is_variable"]:
                    results["variable_diffs"].append(diff_info)
                elif diff_info["is_fixed"]:
                    results["fixed_diffs"].append(diff_info)

        return results

    def compare_tables(self) -> Dict:
        """
        对比表格

        Returns:
            对比结果字典
        """
        gen_tables = self.generated_doc.tables
        ref_tables = self.reference_doc.tables

        results = {
            "total_generated": len(gen_tables),
            "total_reference": len(ref_tables),
            "differences": [],
            "structure_diffs": [],
            "content_diffs": [],
        }

        max_len = min(len(gen_tables), len(ref_tables))

        for i in range(max_len):
            gen_table = gen_tables[i]
            ref_table = ref_tables[i]

            # 对比表格结构
            gen_rows = len(gen_table.rows)
            gen_cols = len(gen_table.columns)
            ref_rows = len(ref_table.rows)
            ref_cols = len(ref_table.columns)

            if gen_rows != ref_rows or gen_cols != ref_cols:
                results["structure_diffs"].append({
                    "table_index": i,
                    "generated": f"{gen_rows}行 × {gen_cols}列",
                    "reference": f"{ref_rows}行 × {ref_cols}列",
                })

            # 对比表格内容（只对比结构相同的表格）
            if gen_rows == ref_rows and gen_cols == ref_cols:
                content_diff_count = 0

                for row_idx in range(min(gen_rows, ref_rows)):
                    for col_idx in range(min(gen_cols, ref_cols)):
                        gen_cell = gen_table.rows[row_idx].cells[col_idx].text.strip()
                        ref_cell = ref_table.rows[row_idx].cells[col_idx].text.strip()

                        if gen_cell != ref_cell:
                            content_diff_count += 1

                if content_diff_count > 0:
                    results["content_diffs"].append({
                        "table_index": i,
                        "diff_cells": content_diff_count,
                        "total_cells": gen_rows * gen_cols,
                        "diff_percentage": content_diff_count / (gen_rows * gen_cols) * 100,
                    })

        return results

    def analyze_alignment(self) -> Dict:
        """
        执行完整的对齐分析

        Returns:
            分析结果
        """
        print("=" * 80)
        print("颗粒化对齐分析")
        print("=" * 80)

        print(f"\n【文件信息】")
        print(f"  自动生成: {self.generated_file}")
        print(f"  参考文件: {self.reference_file}")

        # 1. 段落对比
        print(f"\n【步骤1: 段落对比】")
        para_results = self.compare_paragraphs()

        print(f"  生成报告段落数: {para_results['total_generated']}")
        print(f"  参考报告段落数: {para_results['total_reference']}")
        print(f"  差异段落数: {len(para_results['differences'])}")
        print(f"    - 可变区域差异: {len(para_results['variable_diffs'])} (预期)")
        print(f"    - 固定区域差异: {len(para_results['fixed_diffs'])} (⚠️ 需要检查)")

        # 显示固定区域差异详情
        if para_results['fixed_diffs']:
            print(f"\n  ⚠️  固定区域差异详情:")
            for diff in para_results['fixed_diffs'][:5]:  # 只显示前5个
                print(f"\n    段落 {diff['index']}:")
                print(f"      生成: {diff['generated'][:80]}...")
                print(f"      参考: {diff['reference'][:80]}...")
                print(f"      相似度: {diff['similarity']:.2%}")

        # 2. 表格对比
        print(f"\n【步骤2: 表格对比】")
        table_results = self.compare_tables()

        print(f"  生成报告表格数: {table_results['total_generated']}")
        print(f"  参考报告表格数: {table_results['total_reference']}")
        print(f"  结构差异: {len(table_results['structure_diffs'])} 个表格")
        print(f"  内容差异: {len(table_results['content_diffs'])} 个表格")

        # 显示结构差异
        if table_results['structure_diffs']:
            print(f"\n  ⚠️  表格结构差异:")
            for diff in table_results['structure_diffs'][:5]:
                print(f"    表格 {diff['table_index']}: 生成={diff['generated']}, 参考={diff['reference']}")

        # 显示内容差异
        if table_results['content_diffs']:
            print(f"\n  表格内容差异统计:")
            for diff in table_results['content_diffs'][:10]:
                print(f"    表格 {diff['table_index']}: {diff['diff_cells']}/{diff['total_cells']} 单元格不同 ({diff['diff_percentage']:.1f}%)")

        # 3. 总体评估
        print(f"\n【步骤3: 总体评估】")

        total_para_diffs = len(para_results['differences'])
        variable_para_diffs = len(para_results['variable_diffs'])
        fixed_para_diffs = len(para_results['fixed_diffs'])

        if fixed_para_diffs == 0:
            print(f"  ✅ 段落对齐: 所有差异都在可变区域")
        else:
            print(f"  ⚠️  段落对齐: 存在 {fixed_para_diffs} 个固定区域差异")

        if len(table_results['structure_diffs']) == 0:
            print(f"  ✅ 表格结构: 完全一致")
        else:
            print(f"  ⚠️  表格结构: {len(table_results['structure_diffs'])} 个表格结构不同")

        # 计算对齐率
        alignment_rate = 0
        if total_para_diffs > 0:
            alignment_rate = (variable_para_diffs / total_para_diffs) * 100
        else:
            alignment_rate = 100

        print(f"\n  对齐率: {alignment_rate:.1f}%")

        if alignment_rate >= 95 and len(table_results['structure_diffs']) == 0:
            print(f"  ✅ 结论: 自动生成报告与参考报告高度对齐，差异主要在可变区域")
        elif alignment_rate >= 80:
            print(f"  ⚠️  结论: 自动生成报告基本对齐，存在少量固定区域差异，需要review")
        else:
            print(f"  ❌ 结论: 自动生成报告对齐度较低，存在较多差异，需要详细检查")

        print("\n" + "=" * 80)
        print("✅ 颗粒化对齐分析完成")
        print("=" * 80)

        return {
            "paragraphs": para_results,
            "tables": table_results,
            "alignment_rate": alignment_rate,
        }


def main():
    """主函数"""

    # 文件路径
    generated_file = "data/output/张三---结直肠癌358基因检测-MLB2509307001-终版.docx"
    reference_file = "docs/samples/tempe_test.sanitized.docx"  # 使用sanitized版本

    # 创建对齐工具
    tool = GranularAlignmentTool(generated_file, reference_file)

    # 执行分析
    results = tool.analyze_alignment()

    # 导出详细报告
    print(f"\n💡 提示:")
    print(f"  - 可变区域包括: 患者信息、样本编号、检测结果、基因名称、数值等")
    print(f"  - 固定区域包括: 标题、说明文字、技术原理、免责声明等")
    print(f"  - 如果存在固定区域差异，需要检查模板是否更新或代码逻辑是否正确")


if __name__ == "__main__":
    main()
