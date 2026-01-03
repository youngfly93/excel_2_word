"""
PubMed 文献查询服务（混合模式）

功能：
1. 优先使用本地 JSON 缓存
2. 缺失时通过 NCBI E-utilities API 在线查询
3. 自动更新缓存

API 文档：https://www.ncbi.nlm.nih.gov/books/NBK25499/
"""

import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)


class PubMedService:
    """PubMed 文献查询服务"""

    # NCBI E-utilities API
    ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    # API 限流：无 API Key 时 3次/秒
    REQUEST_INTERVAL = 0.35  # 秒

    def __init__(
        self,
        cache_path: Optional[str] = None,
        api_key: Optional[str] = None,
        auto_save: bool = True,
    ):
        """
        初始化 PubMed 服务

        Args:
            cache_path: 缓存文件路径（JSON格式）
            api_key: NCBI API Key（可选，有则提高限流）
            auto_save: 是否自动保存缓存
        """
        self.cache_path = Path(cache_path) if cache_path else None
        self.api_key = api_key
        self.auto_save = auto_save
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._last_request_time = 0.0
        self._dirty = False  # 缓存是否有未保存的更改

        # 加载缓存
        if self.cache_path:
            self._load_cache()

    def _load_cache(self) -> None:
        """从文件加载缓存"""
        if self.cache_path and self.cache_path.exists():
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
                logger.info(f"加载 PubMed 缓存成功: {len(self._cache)} 条记录")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"加载 PubMed 缓存失败: {e}")
                self._cache = {}

    def save_cache(self) -> None:
        """保存缓存到文件"""
        if not self.cache_path or not self._dirty:
            return

        try:
            # 确保目录存在
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
            self._dirty = False
            logger.info(f"保存 PubMed 缓存成功: {len(self._cache)} 条记录")
        except IOError as e:
            logger.error(f"保存 PubMed 缓存失败: {e}")

    def _rate_limit(self) -> None:
        """API 限流控制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.REQUEST_INTERVAL:
            time.sleep(self.REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def get_citation(self, pmid: str) -> Optional[Dict[str, Any]]:
        """
        获取单条文献信息（优先缓存）

        Args:
            pmid: PubMed ID（纯数字字符串）

        Returns:
            文献信息字典，包含 pmid, title, authors, journal, year 等
            如果查询失败返回 None
        """
        pmid = str(pmid).strip()

        # 1. 检查内存缓存
        if pmid in self._cache:
            logger.debug(f"PubMed 缓存命中: {pmid}")
            return self._cache[pmid]

        # 2. 在线查询
        result = self._fetch_from_api(pmid)
        if result:
            # 更新缓存
            self._cache[pmid] = result
            self._dirty = True
            if self.auto_save:
                self.save_cache()

        return result

    def _fetch_from_api(self, pmid: str) -> Optional[Dict[str, Any]]:
        """
        从 PubMed API 获取文献信息

        Args:
            pmid: PubMed ID

        Returns:
            文献信息字典或 None
        """
        if requests is None:
            logger.warning("requests 库未安装，无法进行在线查询")
            return None

        self._rate_limit()

        params = {
            "db": "pubmed",
            "id": pmid,
            "retmode": "json",
        }
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            response = requests.get(self.ESUMMARY_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            result = data.get("result", {})
            doc = result.get(pmid, {})

            if not doc or "error" in doc:
                logger.warning(f"PubMed 未找到文献: {pmid}")
                return None

            # 解析作者列表
            authors = []
            for author in doc.get("authors", []):
                name = author.get("name", "")
                if name:
                    authors.append(name)

            citation = {
                "pmid": pmid,
                "title": doc.get("title", "").strip(),
                "authors": authors,
                "journal": doc.get("source", ""),
                "year": doc.get("pubdate", "")[:4] if doc.get("pubdate") else "",
                "volume": doc.get("volume", ""),
                "issue": doc.get("issue", ""),
                "pages": doc.get("pages", ""),
                "doi": doc.get("elocationid", ""),
                "fetched_at": datetime.now().isoformat(),
            }

            logger.info(f"PubMed 获取成功: {pmid} - {citation['title'][:50]}...")
            return citation

        except requests.RequestException as e:
            logger.error(f"PubMed API 请求失败: {pmid} - {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"PubMed API 响应解析失败: {pmid} - {e}")
            return None

    def batch_get(self, pmids: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        批量获取文献信息

        Args:
            pmids: PubMed ID 列表

        Returns:
            {pmid: citation_dict} 字典
        """
        results = {}
        for pmid in pmids:
            results[pmid] = self.get_citation(pmid)
        return results

    def format_citation(
        self,
        citation: Dict[str, Any],
        style: str = "simple"
    ) -> str:
        """
        格式化文献引用

        Args:
            citation: 文献信息字典
            style: 格式风格 ("simple", "full", "vancouver")

        Returns:
            格式化的引用字符串
        """
        if not citation:
            return ""

        pmid = citation.get("pmid", "")
        title = citation.get("title", "")
        authors = citation.get("authors", [])
        journal = citation.get("journal", "")
        year = citation.get("year", "")

        if style == "simple":
            # 简单格式: PMID:xxx Title
            return f"PMID:{pmid} {title}"

        elif style == "full":
            # 完整格式: Authors. Title. Journal Year.
            author_str = ", ".join(authors[:3])
            if len(authors) > 3:
                author_str += " et al."
            return f"{author_str}. {title} {journal}. {year}."

        elif style == "vancouver":
            # Vancouver 格式
            author_str = ", ".join(authors[:6])
            if len(authors) > 6:
                author_str += ", et al"
            volume = citation.get("volume", "")
            pages = citation.get("pages", "")
            return f"{author_str}. {title} {journal}. {year};{volume}:{pages}."

        return f"PMID:{pmid} {title}"

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "total_entries": len(self._cache),
            "cache_path": str(self.cache_path) if self.cache_path else None,
            "dirty": self._dirty,
        }

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache = {}
        self._dirty = True
        if self.auto_save:
            self.save_cache()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._dirty:
            self.save_cache()
