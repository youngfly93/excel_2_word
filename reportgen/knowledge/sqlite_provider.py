"""
SQLite 知识库提供者

从 SQLite 数据库加载基因诊疗知识，提供与 GeneKnowledgeProvider 相同的接口。
优点：查询更快、支持并发、便于管理。

Python 3.9 compatible.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# 数据库 Schema 定义
SCHEMA_SQL = """
-- 基因基本信息和解析
CREATE TABLE IF NOT EXISTS gene_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gene_name TEXT NOT NULL UNIQUE,
    gene_intro TEXT,           -- 基因简介
    mutation_desc TEXT,        -- 基因变异说明模板
    mutation_analysis TEXT,    -- 基因变异解析
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用药提示（变异级别）
CREATE TABLE IF NOT EXISTS drug_tips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gene_name TEXT NOT NULL,
    variant_grade TEXT,        -- 变异等级 (Ⅰ类, Ⅱ类, etc.)
    c_hgvs TEXT,              -- c.点位
    p_hgvs TEXT,              -- p.点位
    variant_type TEXT,         -- 扩增/缺失/融合/胚系/未见突变
    benefit_drugs TEXT,        -- 潜在获益靶向药物
    caution_drugs TEXT,        -- 可能耐药或慎重药物
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 药物解析详情
CREATE TABLE IF NOT EXISTS drug_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gene_name TEXT NOT NULL,
    drug_name TEXT NOT NULL,
    drug_type TEXT,            -- benefit / caution
    relation TEXT,             -- 基因变异与药物关联分析
    clinical TEXT,             -- 药物疗效临床解析
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 参考文献
CREATE TABLE IF NOT EXISTS citations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pmid TEXT,                 -- PubMed ID
    nct_id TEXT,              -- NCT 临床试验号
    title TEXT,
    authors TEXT,
    journal TEXT,
    year TEXT,
    content TEXT,              -- 完整引用文本
    related_genes TEXT,        -- 关联基因（逗号分隔）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 基因-转录本信息
CREATE TABLE IF NOT EXISTS gene_transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gene_name TEXT NOT NULL UNIQUE,
    transcript_id TEXT,        -- 转录本ID
    chromosome TEXT,           -- 染色体
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_gene_analysis_name ON gene_analysis(gene_name);
CREATE INDEX IF NOT EXISTS idx_drug_tips_gene ON drug_tips(gene_name);
CREATE INDEX IF NOT EXISTS idx_drug_analysis_gene ON drug_analysis(gene_name);
CREATE INDEX IF NOT EXISTS idx_citations_pmid ON citations(pmid);
CREATE INDEX IF NOT EXISTS idx_citations_genes ON citations(related_genes);
"""


class SQLiteKnowledgeProvider:
    """
    SQLite 知识库提供者

    提供与 GeneKnowledgeProvider 兼容的接口，但使用 SQLite 作为后端。
    """

    def __init__(self, db_path: str, config: Optional[Dict[str, Any]] = None):
        """
        初始化 SQLite 知识库

        Args:
            db_path: SQLite 数据库文件路径
            config: 配置字典（可选，用于兼容性）
        """
        self.db_path = Path(db_path)
        self.config = config or {}
        self._conn: Optional[sqlite3.Connection] = None
        self._loaded = False

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def load(self, base_path: Optional[str] = None) -> bool:
        """
        加载/初始化数据库

        Args:
            base_path: 基础路径（用于兼容性，SQLite 使用 db_path）

        Returns:
            是否加载成功
        """
        if self._loaded:
            return True

        try:
            # 确保目录存在
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # 初始化数据库 schema
            conn = self._get_connection()
            conn.executescript(SCHEMA_SQL)
            conn.commit()

            self._loaded = True
            logger.info(f"SQLite 知识库加载成功: {self.db_path}")
            return True

        except Exception as e:
            logger.error(f"SQLite 知识库加载失败: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ===== 基因知识查询 =====

    def get_gene_intro(self, gene: str) -> str:
        """获取基因简介"""
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT gene_intro FROM gene_analysis WHERE gene_name = ? COLLATE NOCASE",
            (gene.upper(),)
        )
        row = cursor.fetchone()
        return row["gene_intro"] if row and row["gene_intro"] else ""

    def get_gene_analysis(self, gene: str) -> str:
        """获取基因变异解析"""
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT mutation_analysis FROM gene_analysis WHERE gene_name = ? COLLATE NOCASE",
            (gene.upper(),)
        )
        row = cursor.fetchone()
        return row["mutation_analysis"] if row and row["mutation_analysis"] else ""

    def get_mutation_desc_template(self, gene: str) -> str:
        """获取基因变异说明模板"""
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT mutation_desc FROM gene_analysis WHERE gene_name = ? COLLATE NOCASE",
            (gene.upper(),)
        )
        row = cursor.fetchone()
        return row["mutation_desc"] if row and row["mutation_desc"] else ""

    # ===== 药物信息查询 =====

    def get_drug_info(self, gene: str) -> Dict[str, str]:
        """
        获取基因的药物信息

        Returns:
            包含 benefit_drugs, caution_drugs, relation, clinical 的字典
        """
        conn = self._get_connection()

        # 获取用药提示
        cursor = conn.execute(
            "SELECT benefit_drugs, caution_drugs FROM drug_tips WHERE gene_name = ? COLLATE NOCASE LIMIT 1",
            (gene.upper(),)
        )
        tip_row = cursor.fetchone()

        # 获取药物解析
        cursor = conn.execute(
            "SELECT drug_type, relation, clinical FROM drug_analysis WHERE gene_name = ? COLLATE NOCASE",
            (gene.upper(),)
        )
        analysis_rows = cursor.fetchall()

        result = {
            "benefit_drugs": tip_row["benefit_drugs"] if tip_row and tip_row["benefit_drugs"] else "",
            "caution_drugs": tip_row["caution_drugs"] if tip_row and tip_row["caution_drugs"] else "",
        }

        # 合并药物解析
        for row in analysis_rows:
            if row["drug_type"] == "benefit":
                result["positive_relation"] = row["relation"] or ""
                result["positive_clinical"] = row["clinical"] or ""
            elif row["drug_type"] == "caution":
                result["negative_relation"] = row["relation"] or ""
                result["negative_clinical"] = row["clinical"] or ""

        return result

    def get_full_drug_info(self, gene: str) -> List[Dict[str, str]]:
        """获取基因的完整药物信息列表"""
        conn = self._get_connection()
        cursor = conn.execute(
            """SELECT drug_name, drug_type, relation, clinical
               FROM drug_analysis WHERE gene_name = ? COLLATE NOCASE""",
            (gene.upper(),)
        )

        return [
            {
                "drug_name": row["drug_name"],
                "drug_type": row["drug_type"],
                "relation": row["relation"] or "",
                "clinical": row["clinical"] or "",
            }
            for row in cursor.fetchall()
        ]

    # ===== 参考文献查询 =====

    def get_references(self, gene: str) -> List[str]:
        """获取基因的参考文献列表"""
        conn = self._get_connection()
        cursor = conn.execute(
            """SELECT content FROM citations
               WHERE related_genes LIKE ? COLLATE NOCASE
               ORDER BY id""",
            (f"%{gene.upper()}%",)
        )
        return [row["content"] for row in cursor.fetchall() if row["content"]]

    def get_reference_by_pmid(self, pmid: str) -> Optional[Dict[str, Any]]:
        """根据 PMID 获取参考文献"""
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM citations WHERE pmid = ?",
            (pmid,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    # ===== 转录本信息 =====

    def get_gene_transcript_info(self, gene: str) -> Dict[str, str]:
        """获取基因的转录本和染色体信息"""
        conn = self._get_connection()
        cursor = conn.execute(
            """SELECT gene_name, transcript_id, chromosome
               FROM gene_transcripts WHERE gene_name = ? COLLATE NOCASE""",
            (gene.upper(),)
        )
        row = cursor.fetchone()
        if row:
            return {
                "name": row["gene_name"],
                "transcript": row["transcript_id"] or "",
                "chromosome": row["chromosome"] or "",
            }
        return {}

    # ===== 数据写入 =====

    def insert_gene_analysis(self, gene_name: str, intro: str,
                            mutation_desc: str, mutation_analysis: str) -> bool:
        """插入或更新基因分析数据"""
        conn = self._get_connection()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO gene_analysis
                   (gene_name, gene_intro, mutation_desc, mutation_analysis, updated_at)
                   VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (gene_name.upper(), intro, mutation_desc, mutation_analysis)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"插入基因分析数据失败: {e}")
            return False

    def insert_drug_analysis(self, gene_name: str, drug_name: str,
                            drug_type: str, relation: str, clinical: str) -> bool:
        """插入药物分析数据"""
        conn = self._get_connection()
        try:
            conn.execute(
                """INSERT INTO drug_analysis
                   (gene_name, drug_name, drug_type, relation, clinical)
                   VALUES (?, ?, ?, ?, ?)""",
                (gene_name.upper(), drug_name, drug_type, relation, clinical)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"插入药物分析数据失败: {e}")
            return False

    def insert_reference(self, pmid: str = None, nct_id: str = None,
                        title: str = None, content: str = None,
                        related_genes: str = None) -> bool:
        """插入参考文献"""
        conn = self._get_connection()
        try:
            conn.execute(
                """INSERT INTO citations
                   (pmid, nct_id, title, content, related_genes)
                   VALUES (?, ?, ?, ?, ?)""",
                (pmid, nct_id, title, content, related_genes)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"插入参考文献失败: {e}")
            return False

    # ===== 统计信息 =====

    def get_stats(self) -> Dict[str, int]:
        """获取数据库统计信息"""
        conn = self._get_connection()
        stats = {}

        for table in ["gene_analysis", "drug_tips", "drug_analysis",
                      "citations", "gene_transcripts"]:
            cursor = conn.execute(f"SELECT COUNT(*) as cnt FROM {table}")
            row = cursor.fetchone()
            stats[table] = row["cnt"] if row else 0

        return stats

    def __enter__(self):
        self.load()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
