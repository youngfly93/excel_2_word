"""
HGVS-related helpers.

This module contains small, dependency-free utilities used across the project
to format HGVS loci and infer simplified variant types for reporting.
"""

from __future__ import annotations

from typing import Any


def _norm_text(value: Any) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if s.lower() in {"nan", "none"}:
        return ""
    if s in {"", "-", "--", "*"}:
        return ""
    return s


def infer_variant_type_cn(c_hgvs: Any) -> str:
    """Infer a simplified Chinese variant type from c.HGVS text.

    Rules (per report annotations):
    - delins -> 缺失插入突变
    - del    -> 缺失突变 (was: 缺失)
    - dup    -> 重复突变 (was: 重复)
    - ins    -> 插入突变 (was: 插入)
    - else   -> 点突变

    Note: All types should have "突变" suffix to match the final report format.
    """
    s = _norm_text(c_hgvs)
    if not s:
        return ""

    low = s.lower()
    if "delins" in low:
        return "缺失插入突变"
    if "dup" in low:
        return "重复突变"
    if "ins" in low:
        return "插入突变"
    if "del" in low:
        return "缺失突变"
    return "点突变"


def format_variant_site(c_hgvs: Any, p_hgvs: Any, *, sep: str = ",\n") -> str:
    """Format a locus text by combining c.HGVS and p.HGVS (comma + newline)."""
    c = _norm_text(c_hgvs)
    p = _norm_text(p_hgvs)
    if c and p:
        return f"{c}{sep}{p}"
    return c or p

