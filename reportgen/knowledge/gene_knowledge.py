"""
基因知识库加载器

从Excel数据库加载基因诊疗知识，包括：
- 基因简介
- 基因变异解析
- 药物疗效临床解析

Python 3.9 compatible.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from .mutation_description import MutationDescriptionGenerator


class GeneKnowledgeProvider:
    """
    基因知识库提供者

    从Excel文件加载基因诊疗知识，并提供查询接口。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化基因知识库

        Args:
            config: 配置字典，包含知识库路径和列名映射
        """
        self.config = config or {}
        self._loaded = False

        # 数据缓存
        self._gene_analysis_df: Optional[pd.DataFrame] = None
        self._drug_analysis_df: Optional[pd.DataFrame] = None
        self._gene_transcript_df: Optional[pd.DataFrame] = None
        self._references_df: Optional[pd.DataFrame] = None

        # 索引缓存（基因名 -> 数据行）
        self._gene_intro_cache: Dict[str, str] = {}
        self._gene_analysis_cache: Dict[str, str] = {}
        self._drug_analysis_cache: Dict[str, Dict[str, str]] = {}
        self._drug_full_cache: Dict[str, List[Dict[str, str]]] = {}  # 完整药物信息
        self._gene_transcript_cache: Dict[str, Dict[str, str]] = {}
        self._references_cache: Dict[str, List[str]] = {}  # 基因 -> 参考文献列表

        # 位点描述生成器
        self._mutation_desc_gen = MutationDescriptionGenerator()

    def load(self, base_path: Optional[str] = None) -> bool:
        """
        加载知识库数据

        Args:
            base_path: 基础路径，配置中的相对路径将相对于此

        Returns:
            是否加载成功
        """
        if self._loaded:
            return True

        if not self.config.get("enabled", False):
            return False

        base = Path(base_path) if base_path else Path(".")

        # 加载基因知识库
        gene_kb_config = self.config.get("gene_knowledge_db", {})
        if gene_kb_config.get("enabled", False):
            db_path = base / gene_kb_config.get("path", "")
            if db_path.exists():
                self._load_gene_knowledge_db(db_path, gene_kb_config)

        # 加载基因-转录本-染色体信息
        transcript_config = self.config.get("gene_transcript_db", {})
        if transcript_config.get("enabled", False):
            db_path = base / transcript_config.get("path", "")
            if db_path.exists():
                self._load_gene_transcript_db(db_path, transcript_config)

        self._loaded = True
        return True

    def _load_gene_knowledge_db(self, path: Path, config: Dict) -> None:
        """加载基因知识库Excel文件"""
        try:
            sheets = config.get("sheets", {})
            columns = config.get("columns", {})

            # 确定Excel引擎
            engine = "openpyxl" if str(path).endswith(".xlsx") else "xlrd"

            # 加载基因变异解析sheet
            gene_sheet = sheets.get("gene_analysis", "基因变异解析")
            try:
                self._gene_analysis_df = pd.read_excel(
                    str(path), sheet_name=gene_sheet, engine=engine
                )
                self._build_gene_analysis_cache(columns)
            except Exception:
                pass

            # 加载用药提示解析sheet
            drug_sheet = sheets.get("drug_analysis", "用药提示解析")
            try:
                self._drug_analysis_df = pd.read_excel(
                    str(path), sheet_name=drug_sheet, engine=engine
                )
                self._build_drug_analysis_cache(columns)
            except Exception:
                pass

            # 加载参考文献sheet
            ref_sheet = sheets.get("references", "参考文献")
            try:
                self._references_df = pd.read_excel(
                    str(path), sheet_name=ref_sheet, engine=engine
                )
                self._build_references_cache(columns)
            except Exception:
                pass

        except Exception as e:
            # 静默失败，不阻断主流程
            pass

    def _load_gene_transcript_db(self, path: Path, config: Dict) -> None:
        """加载基因-转录本-染色体信息"""
        try:
            columns = config.get("columns", {})
            engine = "openpyxl" if str(path).endswith(".xlsx") else "xlrd"

            self._gene_transcript_df = pd.read_excel(str(path), engine=engine)
            self._build_gene_transcript_cache(columns)
        except Exception:
            pass

    def _norm_text(self, value: Any) -> str:
        """规范化文本值"""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return ""
        s = str(value).strip()
        if s.lower() in ("nan", "none", "*", "-"):
            return ""
        return s

    def _build_gene_analysis_cache(self, columns: Dict) -> None:
        """构建基因分析缓存"""
        if self._gene_analysis_df is None:
            return

        gene_col = columns.get("gene_name", "基因名称")
        intro_col = columns.get("gene_intro", "基因简介")
        analysis_col = columns.get("mutation_analysis", "基因变异解析")

        df = self._gene_analysis_df

        # 检查列是否存在
        if gene_col not in df.columns:
            return

        for _, row in df.iterrows():
            gene = self._norm_text(row.get(gene_col))
            if not gene:
                continue

            gene_upper = gene.upper()

            # 缓存基因简介
            intro = self._norm_text(row.get(intro_col))
            if intro and gene_upper not in self._gene_intro_cache:
                self._gene_intro_cache[gene_upper] = intro

            # 缓存基因变异解析
            analysis = self._norm_text(row.get(analysis_col))
            if analysis and gene_upper not in self._gene_analysis_cache:
                self._gene_analysis_cache[gene_upper] = analysis

    def _build_drug_analysis_cache(self, columns: Dict) -> None:
        """构建药物分析缓存"""
        if self._drug_analysis_df is None:
            return

        df = self._drug_analysis_df

        # 查找相关列（列名可能带有Unnamed前缀）
        # 用药提示解析表结构:
        # Unnamed: 0=基因名称, Unnamed: 1=变异等级, Unnamed: 2=c_point, Unnamed: 3=p_point,
        # Unnamed: 4=扩增/缺失/融合/胚系/未见突变
        # 潜在获益靶向/免疫药物解析=药物, Unnamed: 6=基因变异与药物关联分析, Unnamed: 7=..., Unnamed: 8=药物疗效临床解析
        # 潜在负相关靶向/免疫药物解析=药物, Unnamed: 10=基因变异与药物关联分析, Unnamed: 11=..., Unnamed: 12=药物疗效临床解析

        gene_col = None
        level_col = None
        c_point_col = None
        p_point_col = None
        benefit_drug_col = None
        benefit_relation_col = None
        benefit_clinical_col = None
        negative_drug_col = None
        negative_relation_col = None
        negative_clinical_col = None

        # 解析列位置
        cols = list(df.columns)
        for i, col in enumerate(cols):
            col_str = str(col)
            if "基因名称" in col_str or col == "Unnamed: 0":
                gene_col = col
            elif col == "Unnamed: 1":
                level_col = col
            elif col == "Unnamed: 2":
                c_point_col = col
            elif col == "Unnamed: 3":
                p_point_col = col
            elif "潜在获益靶向/免疫药物解析" in col_str:
                benefit_drug_col = col
                # 后续列
                if i + 1 < len(cols):
                    benefit_relation_col = cols[i + 1]
                if i + 3 < len(cols):
                    benefit_clinical_col = cols[i + 3]
            elif "潜在负相关靶向/免疫药物解析" in col_str:
                negative_drug_col = col
                if i + 1 < len(cols):
                    negative_relation_col = cols[i + 1]
                if i + 3 < len(cols):
                    negative_clinical_col = cols[i + 3]

        # 尝试从第一行获取列名（如果第一行是标题）
        if gene_col is None and len(df) > 0:
            first_row = df.iloc[0]
            for col in df.columns:
                val = str(first_row.get(col, "")).strip()
                if val == "基因名称":
                    gene_col = col
                elif val == "变异等级":
                    level_col = col
                elif val == "c_point":
                    c_point_col = col
                elif val == "p_point":
                    p_point_col = col

        if gene_col is None:
            return

        current_gene = None
        current_level = None
        current_c_point = None
        current_p_point = None

        for _, row in df.iterrows():
            # 获取基因信息（可能在多行中只有第一行有基因名）
            gene = self._norm_text(row.get(gene_col))
            if gene and gene != "基因名称":
                current_gene = gene.upper()
                current_level = self._norm_text(row.get(level_col)) if level_col else ""
                current_c_point = self._norm_text(row.get(c_point_col)) if c_point_col else ""
                current_p_point = self._norm_text(row.get(p_point_col)) if p_point_col else ""

            if not current_gene:
                continue

            # 获取获益药物信息
            benefit_drug = self._norm_text(row.get(benefit_drug_col)) if benefit_drug_col else ""
            benefit_relation = self._norm_text(row.get(benefit_relation_col)) if benefit_relation_col else ""
            benefit_clinical = self._norm_text(row.get(benefit_clinical_col)) if benefit_clinical_col else ""

            # 获取负相关药物信息
            negative_drug = self._norm_text(row.get(negative_drug_col)) if negative_drug_col else ""
            negative_relation = self._norm_text(row.get(negative_relation_col)) if negative_relation_col else ""
            negative_clinical = self._norm_text(row.get(negative_clinical_col)) if negative_clinical_col else ""

            # 初始化缓存
            if current_gene not in self._drug_analysis_cache:
                self._drug_analysis_cache[current_gene] = {}
            if current_gene not in self._drug_full_cache:
                self._drug_full_cache[current_gene] = []

            # 存储获益药物
            if benefit_drug:
                self._drug_analysis_cache[current_gene][benefit_drug] = benefit_clinical
                self._drug_full_cache[current_gene].append({
                    "type": "benefit",
                    "drug": benefit_drug,
                    "level": current_level,
                    "c_point": current_c_point,
                    "p_point": current_p_point,
                    "relation": benefit_relation,
                    "clinical": benefit_clinical,
                })

            # 存储负相关药物
            if negative_drug:
                self._drug_analysis_cache[current_gene][f"慎用:{negative_drug}"] = negative_clinical
                self._drug_full_cache[current_gene].append({
                    "type": "caution",
                    "drug": negative_drug,
                    "level": current_level,
                    "c_point": current_c_point,
                    "p_point": current_p_point,
                    "relation": negative_relation,
                    "clinical": negative_clinical,
                })

    def _build_references_cache(self, columns: Dict) -> None:
        """构建参考文献缓存"""
        if self._references_df is None:
            return

        df = self._references_df

        # 参考文献表结构: 基因名称, 变异等级, c_point, p_point, 扩增/缺失/融合/胚系/未见突变, 参考文献
        gene_col = None
        ref_col = None

        for col in df.columns:
            col_str = str(col)
            if "基因名称" in col_str:
                gene_col = col
            elif "参考文献" in col_str:
                ref_col = col

        if gene_col is None or ref_col is None:
            return

        current_gene = None

        for _, row in df.iterrows():
            gene = self._norm_text(row.get(gene_col))
            if gene:
                current_gene = gene.upper()

            if not current_gene:
                continue

            ref = self._norm_text(row.get(ref_col))
            if ref:
                if current_gene not in self._references_cache:
                    self._references_cache[current_gene] = []
                # 避免重复
                if ref not in self._references_cache[current_gene]:
                    self._references_cache[current_gene].append(ref)

    def _build_gene_transcript_cache(self, columns: Dict) -> None:
        """构建基因-转录本缓存"""
        if self._gene_transcript_df is None:
            return

        gene_col = columns.get("gene_name", "Genename")
        transcript_col = columns.get("transcript", "Transcriptid")
        chr_col = columns.get("chromosome", "Chr")

        df = self._gene_transcript_df

        for _, row in df.iterrows():
            gene = self._norm_text(row.get(gene_col))
            if not gene:
                continue

            gene_upper = gene.upper()
            if gene_upper in self._gene_transcript_cache:
                continue  # 只保留第一个（避免重复）

            self._gene_transcript_cache[gene_upper] = {
                "name": gene,
                "transcript": self._norm_text(row.get(transcript_col)),
                "chromosome": self._norm_text(row.get(chr_col)).replace("chr", ""),
            }

    def get_gene_intro(self, gene: str) -> str:
        """
        获取基因简介

        Args:
            gene: 基因名称

        Returns:
            基因简介文本，未找到返回空字符串
        """
        if not self._loaded:
            self.load()
        return self._gene_intro_cache.get(gene.upper(), "")

    def get_gene_analysis(self, gene: str) -> str:
        """
        获取基因变异解析

        Args:
            gene: 基因名称

        Returns:
            基因变异解析文本，未找到返回空字符串
        """
        if not self._loaded:
            self.load()
        return self._gene_analysis_cache.get(gene.upper(), "")

    def get_drug_analysis(self, gene: str, drug: Optional[str] = None) -> str:
        """
        获取药物疗效临床解析

        Args:
            gene: 基因名称
            drug: 药物名称（可选，不指定则返回该基因相关的所有药物分析）

        Returns:
            药物疗效临床解析文本
        """
        if not self._loaded:
            self.load()

        gene_drugs = self._drug_analysis_cache.get(gene.upper(), {})
        if not gene_drugs:
            return ""

        if drug:
            return gene_drugs.get(drug, "")

        # 返回所有药物分析（合并）
        return "\n\n".join(gene_drugs.values())

    def get_drug_full_info(self, gene: str) -> List[Dict[str, str]]:
        """
        获取基因的完整药物信息列表

        Args:
            gene: 基因名称

        Returns:
            药物信息列表，每个元素包含 type, drug, level, c_point, p_point, relation, clinical
        """
        if not self._loaded:
            self.load()
        return self._drug_full_cache.get(gene.upper(), [])

    def get_references(self, gene: str) -> List[str]:
        """
        获取基因的参考文献列表

        Args:
            gene: 基因名称

        Returns:
            参考文献列表
        """
        if not self._loaded:
            self.load()
        return self._references_cache.get(gene.upper(), [])

    def get_gene_transcript_info(self, gene: str) -> Dict[str, str]:
        """
        获取基因的转录本和染色体信息

        Args:
            gene: 基因名称

        Returns:
            包含 name, transcript, chromosome 的字典
        """
        if not self._loaded:
            self.load()
        return self._gene_transcript_cache.get(gene.upper(), {})

    def generate_mutation_description(
        self,
        gene: str,
        c_hgvs: str,
        p_hgvs: str,
        frequency: float,
        mutation_type: Optional[str] = None
    ) -> str:
        """
        生成基因变异说明

        Args:
            gene: 基因名称
            c_hgvs: cDNA变异描述
            p_hgvs: 蛋白变异描述
            frequency: 突变频率
            mutation_type: 突变类型

        Returns:
            基因变异说明文本
        """
        return self._mutation_desc_gen.generate(
            gene, c_hgvs, p_hgvs, frequency, mutation_type
        )

    def build_gene_knowledge_section(
        self,
        gene: str,
        c_hgvs: str,
        p_hgvs: str,
        frequency: float,
        mutation_type: Optional[str] = None,
        has_drug: bool = False,
        cancer_type: str = "结直肠癌"
    ) -> Dict[str, str]:
        """
        构建完整的基因诊疗知识章节

        Args:
            gene: 基因名称
            c_hgvs: cDNA变异描述
            p_hgvs: 蛋白变异描述
            frequency: 突变频率
            mutation_type: 突变类型
            has_drug: 是否有相关药物（用于确定标题颜色）
            cancer_type: 癌症类型

        Returns:
            包含 header, intro, mutation_desc, mutation_analysis 等字段的字典
        """
        if not self._loaded:
            self.load()

        # 构建标题
        p_display = p_hgvs if p_hgvs and p_hgvs != "--" else ""
        if p_display:
            header = f"{gene}：{c_hgvs}，{p_display}；{frequency:.2f}%"
        else:
            header = f"{gene}：{c_hgvs}；{frequency:.2f}%"

        # 标题颜色（有药物的用红色，否则用蓝色）
        header_color = "FF0000" if has_drug else "0000FF"

        # 获取基因简介
        intro = self.get_gene_intro(gene)

        # 生成变异说明
        mutation_desc = self.generate_mutation_description(
            gene, c_hgvs, p_hgvs, frequency, mutation_type
        )

        # 获取变异解析
        mutation_analysis = self.get_gene_analysis(gene)

        return {
            "gene": gene,
            "header": header,
            "header_color": header_color,
            "intro": intro,
            "mutation_desc": mutation_desc,
            "mutation_analysis": mutation_analysis,
            "has_drug": has_drug,
        }

    def build_all_gene_knowledge_sections(
        self,
        variants: List[Dict[str, Any]],
        cancer_type: str = "结直肠癌"
    ) -> List[Dict[str, str]]:
        """
        为所有变异构建基因诊疗知识章节

        Args:
            variants: 变异列表，每个元素包含 gene, cHGVS, pHGVS, frequency 等字段
            cancer_type: 癌症类型

        Returns:
            基因诊疗知识章节列表
        """
        sections = []
        seen_variants = set()  # 避免重复（同一基因同一位点）

        for v in variants:
            gene = v.get("gene", "")
            c_hgvs = v.get("cHGVS", "")
            p_hgvs = v.get("pHGVS", "")

            # 去重
            variant_key = f"{gene}:{c_hgvs}:{p_hgvs}"
            if variant_key in seen_variants:
                continue
            seen_variants.add(variant_key)

            # 解析频率
            freq_str = v.get("frequency", "0")
            try:
                frequency = float(freq_str.replace("%", "")) if freq_str else 0.0
            except (ValueError, TypeError):
                frequency = 0.0

            # 判断是否有药物
            benefit_drugs = v.get("benefit_drugs", "")
            caution_drugs = v.get("caution_drugs", "")
            has_drug = (
                benefit_drugs and benefit_drugs != "--" and benefit_drugs != "无"
            ) or (
                caution_drugs and caution_drugs != "--" and caution_drugs != "无"
            )

            section = self.build_gene_knowledge_section(
                gene=gene,
                c_hgvs=c_hgvs,
                p_hgvs=p_hgvs,
                frequency=frequency,
                mutation_type=v.get("mutation_type"),
                has_drug=has_drug,
                cancer_type=cancer_type,
            )
            sections.append(section)

        return sections

    def build_drug_analysis_sections(
        self,
        variants: List[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        """
        构建用药提示解析章节

        Args:
            variants: 变异列表，每个元素包含 gene, cHGVS, pHGVS, benefit_drugs, caution_drugs 等字段

        Returns:
            用药提示解析章节列表，每个元素包含:
            - gene: 基因名称
            - mutation_info: 突变信息 (如 "c.844C>T，p.R282W")
            - header: 完整标题 (如 "TP53：c.844C>T，p.R282W突变相应靶向药物")
            - drug_name: 药物名称
            - drug_type: 药物类型 (benefit/caution)
            - drug_type_cn: 药物类型中文
            - relation: 基因变异与药物关联分析
            - clinical: 药物疗效临床解析
        """
        if not self._loaded:
            self.load()

        sections = []
        seen_drugs = set()  # 避免重复

        for v in variants:
            gene = v.get("gene", "").upper()
            c_hgvs = v.get("cHGVS", "")
            p_hgvs = v.get("pHGVS", "")
            benefit_drugs = v.get("benefit_drugs", "")
            caution_drugs = v.get("caution_drugs", "")

            # 构建突变信息 (如 "c.844C>T，p.R282W")
            if p_hgvs and p_hgvs != "--":
                mutation_info = f"{c_hgvs}，{p_hgvs}"
            else:
                mutation_info = c_hgvs

            # 获取该基因的所有药物信息
            drug_infos = self.get_drug_full_info(gene)

            # 匹配获益药物
            if benefit_drugs and benefit_drugs != "--":
                for drug_info in drug_infos:
                    if drug_info["type"] == "benefit":
                        drug_name = drug_info["drug"]
                        # 检查药物是否在当前变异的获益药物列表中
                        if drug_name and drug_name in benefit_drugs:
                            key = f"{gene}:{drug_name}:benefit"
                            if key not in seen_drugs:
                                seen_drugs.add(key)
                                # 构建标题 (如 "TP53：c.844C>T，p.R282W突变相应靶向药物")
                                header = f"{gene}：{mutation_info}突变相应靶向药物"
                                sections.append({
                                    "gene": gene,
                                    "mutation_info": mutation_info,
                                    "header": header,
                                    "drug_name": drug_name,
                                    "drug_type": "benefit",
                                    "drug_type_cn": "潜在获益药物",
                                    "relation": drug_info.get("relation", ""),
                                    "clinical": drug_info.get("clinical", ""),
                                })

            # 匹配慎用药物
            if caution_drugs and caution_drugs != "--":
                for drug_info in drug_infos:
                    if drug_info["type"] == "caution":
                        drug_name = drug_info["drug"]
                        if drug_name and drug_name in caution_drugs:
                            key = f"{gene}:{drug_name}:caution"
                            if key not in seen_drugs:
                                seen_drugs.add(key)
                                # 构建标题 (如 "KRAS：c.34G>A，p.G12S突变相应负相关药物")
                                header = f"{gene}：{mutation_info}突变相应负相关药物"
                                sections.append({
                                    "gene": gene,
                                    "mutation_info": mutation_info,
                                    "header": header,
                                    "drug_name": drug_name,
                                    "drug_type": "caution",
                                    "drug_type_cn": "慎用药物",
                                    "relation": drug_info.get("relation", ""),
                                    "clinical": drug_info.get("clinical", ""),
                                })

        return sections

    def build_references(
        self,
        variants: List[Dict[str, Any]],
        max_per_gene: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        构建参考文献列表

        Args:
            variants: 变异列表
            max_per_gene: 每个基因最多返回的参考文献数量

        Returns:
            参考文献列表，每个元素包含:
            - gene: 基因名称
            - references: 该基因的参考文献列表
        """
        if not self._loaded:
            self.load()

        result = []
        seen_genes = set()

        for v in variants:
            gene = v.get("gene", "").upper()
            if gene in seen_genes:
                continue
            seen_genes.add(gene)

            refs = self.get_references(gene)
            if refs:
                result.append({
                    "gene": gene,
                    "references": refs[:max_per_gene],
                })

        return result

    def build_all_references_flat(
        self,
        variants: List[Dict[str, Any]],
        max_per_gene: int = 5,
    ) -> List[str]:
        """
        构建扁平化的参考文献列表（去重）

        Args:
            variants: 变异列表
            max_per_gene: 每个基因最多返回的参考文献数量

        Returns:
            参考文献字符串列表（已去重）
        """
        if not self._loaded:
            self.load()

        all_refs = []
        seen_refs = set()
        seen_genes = set()

        for v in variants:
            gene = v.get("gene", "").upper()
            if gene in seen_genes:
                continue
            seen_genes.add(gene)

            refs = self.get_references(gene)
            for ref in refs[:max_per_gene]:
                if ref not in seen_refs:
                    seen_refs.add(ref)
                    all_refs.append(ref)

        return all_refs

    def build_numbered_references(
        self,
        variants: List[Dict[str, Any]],
        max_per_gene: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        构建编号参考文献列表（用于模板渲染）

        Args:
            variants: 变异列表
            max_per_gene: 每个基因最多返回的参考文献数量

        Returns:
            参考文献列表，每项包含 {"number": int, "text": str}
        """
        flat_refs = self.build_all_references_flat(variants, max_per_gene)
        return [
            {"number": i, "text": ref.strip()}
            for i, ref in enumerate(flat_refs, 1)
        ]
