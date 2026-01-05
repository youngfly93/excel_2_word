"""
药物商品名服务

提供药物通用名到商品名的映射功能，用于在报告中显示药物商品名。

Python 3.9 compatible.
"""

import os
import re
from typing import Any, Dict, List, Optional, Tuple

import yaml


class DrugBrandService:
    """药物商品名服务类"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化服务。

        Args:
            config_path: 配置文件路径（默认使用 config/drug_brand_names.yaml）
        """
        self._config_path = config_path
        self._loaded = False
        self._loaded_from: Optional[str] = None
        self._drug_mappings: Dict[str, Dict[str, Any]] = {}

    def load(self, base_path: Optional[str] = None) -> None:
        """
        加载药物配置。

        Args:
            base_path: 基础路径（用于定位配置文件）
        """
        config_path = self._config_path
        if not config_path:
            if base_path:
                config_path = os.path.join(base_path, "config", "drug_brand_names.yaml")
            else:
                config_path = os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "..",
                    "config",
                    "drug_brand_names.yaml",
                )

        config_path = os.path.abspath(config_path)

        # Allow re-loading when callers pass different base_path/config_path.
        if self._loaded and self._loaded_from == config_path:
            return

        if not os.path.exists(config_path):
            # 配置文件不存在时静默返回（不覆盖既有映射，避免单例被“空路径”污染）
            if not self._drug_mappings:
                self._loaded = True
                self._loaded_from = config_path
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            # 合并所有药物类别
            merged: Dict[str, Dict[str, Any]] = {}
            for category in [
                "targeted_drugs",
                "immunotherapy_drugs",
                "chemotherapy_drugs",
            ]:
                if category in data:
                    merged.update(data[category] or {})

            self._loaded = True
            self._loaded_from = config_path
            if merged:
                self._drug_mappings = merged
        except Exception:
            self._loaded = True
            self._loaded_from = config_path

    def get_brand_info(self, generic_name: str) -> Optional[Dict[str, Any]]:
        """
        获取药物商品名信息。

        Args:
            generic_name: 药物通用名（中文）

        Returns:
            药物信息字典，包含 generic_en, brands, target 等，或 None
        """
        if not self._loaded:
            self.load()

        # 精确匹配
        if generic_name in self._drug_mappings:
            return self._drug_mappings[generic_name]

        # 模糊匹配（去除空格、括号内容等）
        normalized = re.sub(r"[（()）\s]", "", generic_name)
        for name, info in self._drug_mappings.items():
            if re.sub(r"[（()）\s]", "", name) == normalized:
                return info

        return None

    def get_brand_name(self, generic_name: str, prefer_chinese: bool = True) -> str:
        """
        获取药物商品名。

        Args:
            generic_name: 药物通用名（中文）
            prefer_chinese: 是否优先返回中文商品名

        Returns:
            商品名字符串，未找到则返回原通用名
        """
        info = self.get_brand_info(generic_name)
        if not info or not info.get("brands"):
            return generic_name

        brands = info["brands"]
        if prefer_chinese:
            # 尝试找中文商品名（包含中文字符的）
            for brand in brands:
                if re.search(r"[\u4e00-\u9fff]", brand):
                    return brand
        # 返回第一个商品名
        return brands[0] if brands else generic_name

    def format_drug_with_brand(
        self, drug_str: str, include_generic: bool = True, separator: str = "/"
    ) -> str:
        """
        格式化药物名称，添加商品名。

        Args:
            drug_str: 药物字符串（可能包含多个药物，以逗号/换行分隔）
            include_generic: 是否保留通用名
            separator: 通用名与商品名的分隔符

        Returns:
            格式化后的药物字符串
        """
        if not self._loaded:
            self.load()

        # 分割多个药物（支持逗号、顿号、换行、分号）
        drugs = re.split(r"[,，、;\n\r]+", drug_str)
        formatted = []

        for drug in drugs:
            drug = drug.strip()
            if not drug or drug in ("--", "-", "*"):
                continue

            # 提取药物名和证据等级（如 "西妥昔单抗（A）"）
            match = re.match(r"^(.+?)(?:[（(]([A-D])[)）])?$", drug)
            if match:
                name = match.group(1).strip()
                level = match.group(2)

                brand = self.get_brand_name(name)
                if brand != name:
                    if include_generic:
                        formatted_name = f"{name}{separator}{brand}"
                    else:
                        formatted_name = brand
                else:
                    formatted_name = name

                if level:
                    formatted_name += f"（{level}）"
                formatted.append(formatted_name)
            else:
                formatted.append(drug)

        return "\n".join(formatted) if formatted else drug_str

    def build_drug_summary_table(
        self,
        variants: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        从变异列表构建药物汇总表。

        Args:
            variants: 变异列表（包含 benefit_drugs 和 caution_drugs 字段）

        Returns:
            药物汇总列表，每项包含：
            - generic_name: 通用名
            - brand_name: 商品名
            - generic_en: 英文名
            - evidence_level: 证据等级
            - drug_type: 药物类型（获益/慎用）
            - related_genes: 相关基因列表
        """
        if not self._loaded:
            self.load()

        drug_summary: Dict[str, Dict[str, Any]] = {}

        for variant in variants:
            gene = variant.get("gene", "")

            # 处理获益药物
            benefit_drugs = variant.get("benefit_drugs", "") or variant.get(
                "获益药物", ""
            )
            self._extract_drugs_to_summary(benefit_drugs, "获益", gene, drug_summary)

            # 处理慎用药物
            caution_drugs = variant.get("caution_drugs", "") or variant.get(
                "慎用药物", ""
            )
            self._extract_drugs_to_summary(caution_drugs, "慎用", gene, drug_summary)

        # 转换为列表
        result = []
        for key, info in drug_summary.items():
            result.append(
                {
                    "generic_name": info["generic_name"],
                    "brand_name": info["brand_name"],
                    "generic_en": info.get("generic_en", ""),
                    "evidence_level": info.get("evidence_level", ""),
                    "drug_type": info["drug_type"],
                    "related_genes": sorted(info["related_genes"]),
                    "target": info.get("target", ""),
                }
            )

        # 按药物类型和通用名排序
        result.sort(key=lambda x: (x["drug_type"], x["generic_name"]))
        return result

    def _extract_drugs_to_summary(
        self,
        drug_str: str,
        drug_type: str,
        gene: str,
        summary: Dict[str, Dict[str, Any]],
    ) -> None:
        """从药物字符串提取药物信息到汇总字典"""
        if not drug_str or drug_str in ("--", "-", "*"):
            return

        drugs = re.split(r"[\n\r]+", drug_str)

        for drug in drugs:
            drug = drug.strip()
            if not drug or drug in ("--", "-", "*"):
                continue

            # 提取药物名和证据等级
            match = re.match(r"^(.+?)(?:[（(]([A-D])[)）])?$", drug)
            if match:
                name = match.group(1).strip()
                level = match.group(2) or ""

                # 生成唯一键
                key = f"{name}_{drug_type}"

                if key not in summary:
                    brand_info = self.get_brand_info(name)
                    summary[key] = {
                        "generic_name": name,
                        "brand_name": self.get_brand_name(name),
                        "generic_en": (
                            brand_info.get("generic_en", "") if brand_info else ""
                        ),
                        "evidence_level": level,
                        "drug_type": drug_type,
                        "related_genes": {gene} if gene else set(),
                        "target": brand_info.get("target", "") if brand_info else "",
                    }
                else:
                    # 更新证据等级（取最高）
                    if level and (
                        not summary[key]["evidence_level"]
                        or level < summary[key]["evidence_level"]
                    ):
                        summary[key]["evidence_level"] = level
                    # 添加相关基因
                    if gene:
                        summary[key]["related_genes"].add(gene)


# 全局单例
_drug_brand_service: Optional[DrugBrandService] = None


def get_drug_brand_service(config_path: Optional[str] = None) -> DrugBrandService:
    """获取药物商品名服务单例"""
    global _drug_brand_service
    if _drug_brand_service is None:
        _drug_brand_service = DrugBrandService(config_path)
    return _drug_brand_service
