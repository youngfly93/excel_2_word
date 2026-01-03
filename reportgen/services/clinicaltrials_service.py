"""
ClinicalTrials.gov 临床试验查询服务（混合模式）

功能：
1. 优先使用本地 JSON 缓存
2. 缺失时通过 ClinicalTrials.gov API 在线查询
3. 自动更新缓存

API 文档：https://clinicaltrials.gov/data-api/api
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


class ClinicalTrialsService:
    """ClinicalTrials.gov 临床试验查询服务"""

    # ClinicalTrials.gov API v2
    API_BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

    # API 限流（建议控制在合理范围）
    REQUEST_INTERVAL = 0.5  # 秒

    def __init__(
        self,
        cache_path: Optional[str] = None,
        auto_save: bool = True,
    ):
        """
        初始化 ClinicalTrials 服务

        Args:
            cache_path: 缓存文件路径（JSON格式）
            auto_save: 是否自动保存缓存
        """
        self.cache_path = Path(cache_path) if cache_path else None
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
                logger.info(f"加载 NCT 缓存成功: {len(self._cache)} 条记录")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"加载 NCT 缓存失败: {e}")
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
            logger.info(f"保存 NCT 缓存成功: {len(self._cache)} 条记录")
        except IOError as e:
            logger.error(f"保存 NCT 缓存失败: {e}")

    def _rate_limit(self) -> None:
        """API 限流控制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.REQUEST_INTERVAL:
            time.sleep(self.REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def get_study(self, nct_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个临床试验信息（优先缓存）

        Args:
            nct_id: NCT ID（如 NCT02576444）

        Returns:
            试验信息字典，包含 nct_id, title, status, phase 等
            如果查询失败返回 None
        """
        nct_id = str(nct_id).strip().upper()

        # 标准化格式
        if not nct_id.startswith("NCT"):
            nct_id = f"NCT{nct_id}"

        # 1. 检查内存缓存
        if nct_id in self._cache:
            logger.debug(f"NCT 缓存命中: {nct_id}")
            return self._cache[nct_id]

        # 2. 在线查询
        result = self._fetch_from_api(nct_id)
        if result:
            # 更新缓存
            self._cache[nct_id] = result
            self._dirty = True
            if self.auto_save:
                self.save_cache()

        return result

    def _fetch_from_api(self, nct_id: str) -> Optional[Dict[str, Any]]:
        """
        从 ClinicalTrials.gov API 获取试验信息

        Args:
            nct_id: NCT ID

        Returns:
            试验信息字典或 None
        """
        if requests is None:
            logger.warning("requests 库未安装，无法进行在线查询")
            return None

        self._rate_limit()

        url = f"{self.API_BASE_URL}/{nct_id}"
        params = {
            "format": "json",
        }

        try:
            response = requests.get(url, params=params, timeout=15)

            if response.status_code == 404:
                logger.warning(f"NCT 未找到试验: {nct_id}")
                return None

            response.raise_for_status()
            data = response.json()

            # 解析试验信息
            protocol = data.get("protocolSection", {})
            id_module = protocol.get("identificationModule", {})
            status_module = protocol.get("statusModule", {})
            design_module = protocol.get("designModule", {})

            # 获取标题（优先官方标题，其次简称）
            title = id_module.get("officialTitle", "")
            if not title:
                title = id_module.get("briefTitle", "")

            # 获取状态
            status = status_module.get("overallStatus", "")

            # 获取阶段
            phases = design_module.get("phases", [])
            phase = ", ".join(phases) if phases else ""

            # 获取赞助商
            sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
            lead_sponsor = sponsor_module.get("leadSponsor", {})
            sponsor = lead_sponsor.get("name", "")

            study_info = {
                "nct_id": nct_id,
                "title": title.strip(),
                "brief_title": id_module.get("briefTitle", "").strip(),
                "status": status,
                "phase": phase,
                "sponsor": sponsor,
                "fetched_at": datetime.now().isoformat(),
            }

            logger.info(f"NCT 获取成功: {nct_id} - {study_info['brief_title'][:50]}...")
            return study_info

        except requests.RequestException as e:
            logger.error(f"NCT API 请求失败: {nct_id} - {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"NCT API 响应解析失败: {nct_id} - {e}")
            return None

    def batch_get(self, nct_ids: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        批量获取试验信息

        Args:
            nct_ids: NCT ID 列表

        Returns:
            {nct_id: study_dict} 字典
        """
        results = {}
        for nct_id in nct_ids:
            results[nct_id] = self.get_study(nct_id)
        return results

    def format_citation(
        self,
        study: Dict[str, Any],
        style: str = "simple"
    ) -> str:
        """
        格式化临床试验引用

        Args:
            study: 试验信息字典
            style: 格式风格 ("simple", "full")

        Returns:
            格式化的引用字符串
        """
        if not study:
            return ""

        nct_id = study.get("nct_id", "")
        title = study.get("title", "") or study.get("brief_title", "")
        status = study.get("status", "")

        if style == "simple":
            # 简单格式: NCT_ID Title
            return f"{nct_id} {title}"

        elif style == "full":
            # 完整格式: NCT_ID Title. Status: XXX
            phase = study.get("phase", "")
            parts = [f"{nct_id} {title}"]
            if phase:
                parts.append(f"Phase: {phase}")
            if status:
                parts.append(f"Status: {status}")
            return ". ".join(parts)

        return f"{nct_id} {title}"

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
