"""
癌种重要基因列表提供者

从Excel数据库加载各癌种的重要基因列表，用于动态生成基因检测列表。
解决批注#33：基因检测列表应根据癌种动态生成（301/358区分）

Python 3.9 compatible.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd


class CancerTypeGeneProvider:
    """
    癌种重要基因列表提供者

    从Excel文件加载各癌种的重要基因列表，并提供查询接口。
    Excel文件结构：每个Sheet对应一个癌种，Sheet名即癌种名称。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化癌种基因列表提供者

        Args:
            config: 配置字典，包含知识库路径和列名映射
        """
        self.config = config or {}
        self._loaded = False

        # 数据缓存：Sheet名 -> 基因列表
        self._genes_cache: Dict[str, List[str]] = {}

        # 癌种名称映射（报告中的癌种名 -> Sheet名）
        self._cancer_type_mapping: Dict[str, str] = {}

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
        db_path = base / self.config.get("path", "")

        if not db_path.exists():
            return False

        try:
            self._load_excel(db_path)
            self._build_cancer_type_mapping()
            self._loaded = True
            return True
        except Exception:
            return False

    def _load_excel(self, path: Path) -> None:
        """加载Excel文件中的所有Sheet"""
        try:
            xl = pd.ExcelFile(str(path))
            gene_col = self.config.get("columns", {}).get("gene_name", "汇总基因")

            for sheet_name in xl.sheet_names:
                try:
                    df = pd.read_excel(str(path), sheet_name=sheet_name)
                    if gene_col in df.columns:
                        genes = []
                        for val in df[gene_col]:
                            if pd.notna(val):
                                gene = str(val).strip().upper()
                                if gene:
                                    genes.append(gene)
                        self._genes_cache[sheet_name] = genes
                except Exception:
                    continue
        except Exception:
            pass

    def _build_cancer_type_mapping(self) -> None:
        """构建癌种名称映射"""
        mapping_config = self.config.get("cancer_type_mapping", {})

        # 构建反向映射：报告中的癌种名 -> Sheet名
        for sheet_name, aliases in mapping_config.items():
            # Sheet名本身也是一个别名
            self._cancer_type_mapping[sheet_name] = sheet_name
            self._cancer_type_mapping[sheet_name.upper()] = sheet_name

            # 处理别名列表
            if isinstance(aliases, list):
                for alias in aliases:
                    self._cancer_type_mapping[alias] = sheet_name
                    self._cancer_type_mapping[alias.upper()] = sheet_name

    def _normalize_cancer_type(self, cancer_type: str) -> Optional[str]:
        """
        规范化癌种名称，返回对应的Sheet名

        Args:
            cancer_type: 报告中的癌种名称

        Returns:
            对应的Sheet名，未找到返回None
        """
        if not cancer_type:
            return None

        cancer_type = cancer_type.strip()

        # 直接匹配
        if cancer_type in self._cancer_type_mapping:
            return self._cancer_type_mapping[cancer_type]

        # 大写匹配
        if cancer_type.upper() in self._cancer_type_mapping:
            return self._cancer_type_mapping[cancer_type.upper()]

        # 模糊匹配：检查癌种名是否包含在某个Sheet名中
        for sheet_name in self._genes_cache.keys():
            if sheet_name in cancer_type or cancer_type in sheet_name:
                return sheet_name

        # 关键词匹配
        cancer_keywords = {
            "肠": "肠癌",
            "结肠": "肠癌",
            "直肠": "肠癌",
            "乙状结肠": "肠癌",
            "回盲": "肠癌",
            "盲肠": "肠癌",
            "肺": "肺癌",
            "胃": "胃癌",
            "肝": "肝癌",
            "乳腺": "乳腺癌",
            "子宫": "子宫",
            "宫颈": "宫颈癌",
        }

        for keyword, sheet_name in cancer_keywords.items():
            if keyword in cancer_type:
                if sheet_name in self._genes_cache:
                    return sheet_name

        return None

    def get_genes_for_cancer(self, cancer_type: str) -> List[str]:
        """
        根据癌种返回重要基因列表

        Args:
            cancer_type: 癌种名称

        Returns:
            基因列表，未找到返回空列表
        """
        if not self._loaded:
            self.load()

        sheet_name = self._normalize_cancer_type(cancer_type)
        if sheet_name and sheet_name in self._genes_cache:
            return self._genes_cache[sheet_name]

        return []

    def get_available_cancer_types(self) -> List[str]:
        """
        获取所有可用的癌种类型（Sheet名）

        Returns:
            癌种类型列表
        """
        if not self._loaded:
            self.load()

        return list(self._genes_cache.keys())

    def is_gene_important_for_cancer(self, gene: str, cancer_type: str) -> bool:
        """
        判断某个基因是否是该癌种的重要基因

        Args:
            gene: 基因名称
            cancer_type: 癌种名称

        Returns:
            是否是重要基因
        """
        genes = self.get_genes_for_cancer(cancer_type)
        return gene.upper() in [g.upper() for g in genes]

    def get_undetected_important_genes(
        self,
        detected_genes: List[str],
        cancer_type: str
    ) -> List[str]:
        """
        获取未检出的重要基因列表

        Args:
            detected_genes: 已检出的基因列表
            cancer_type: 癌种名称

        Returns:
            未检出的重要基因列表
        """
        important_genes = self.get_genes_for_cancer(cancer_type)
        detected_upper = [g.upper() for g in detected_genes]

        return [g for g in important_genes if g.upper() not in detected_upper]
