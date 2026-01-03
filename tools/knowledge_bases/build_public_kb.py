#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build local knowledge-base Excel files from public sources (CIViC, CGI).

This repo's report generation can optionally use two offline "knowledge bases":
  1) targeted drug tips: gene/variant -> benefit/caution drugs
  2) immune gene list: pos/neg/hyper genes -> used to summarize detected variants

This script consumes public TSV releases and converts them into the Excel formats
expected by `reportgen/core/field_mapper.py`:
  - knowledge_bases.targeted_drug_db.path (xlsx)
  - knowledge_bases.immune_gene_list.path (xlsx)

Inputs (downloaded TSVs suggested by `data_get.md`):
  - CIViC: nightly-AssertionSummaries.tsv (CC0)
  - CGI: cgi_biomarkers_latest.tsv (CC0)

Outputs (default):
  - data/knowledge_bases/processed/targeted_drug_db_public.xlsx
  - data/knowledge_bases/processed/immune_gene_list_public.xlsx

Run:
  python3 tools/knowledge_bases/build_public_kb.py
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import pandas as pd


DEFAULT_CIVIC_ASSERTIONS = "data/knowledge_bases/raw/civic_nightly_AssertionSummaries.tsv"
DEFAULT_CGI_BIOMARKERS = "data/knowledge_bases/raw/cgi_biomarkers_latest.tsv"
DEFAULT_INTERNAL_TARGETED_DB = "2025.12.10/示例：+++自建肠癌基因数据库.xlsx"
DEFAULT_INTERNAL_IMMUNE_LIST = "2025.12.12/1-免疫治疗相关基因.xlsx"
DEFAULT_OUT_TARGETED = "data/knowledge_bases/processed/targeted_drug_db_public.xlsx"
DEFAULT_OUT_IMMUNE = "data/knowledge_bases/processed/immune_gene_list_public.xlsx"


IMMUNO_DRUG_KEYWORDS = [
    # target names
    "pd-1",
    "pd1",
    "pd-l1",
    "pdl1",
    "ctla-4",
    "ctla4",
    # common ICI generic names (EN)
    "pembrolizumab",
    "nivolumab",
    "atezolizumab",
    "durvalumab",
    "avelumab",
    "ipilimumab",
    "tremelimumab",
    "cemiplimab",
    "dostarlimab",
    # CN generics occasionally appear in internal material; keep for robustness
    "帕博利珠单抗",
    "纳武利尤单抗",
    "阿替利珠单抗",
    "度伐利尤单抗",
    "阿维鲁单抗",
    "伊匹木单抗",
    "替雷利珠单抗",
    "信迪利单抗",
    "卡瑞利珠单抗",
    "特瑞普利单抗",
]


TARGETED_DB_REQUIRED_COLS = {
    "gene": "基因名称",
    "c": "c_point",
    "p": "p_point",
    "benefit": "潜在获益靶向药物（证据等级）",
    "caution": "可能耐药或慎重药物（证据等级）",
}


@dataclass(frozen=True)
class TargetedTip:
    gene: str
    alteration_type: str
    c_point: str
    p_point: str
    benefit_items: tuple[str, ...]
    caution_items: tuple[str, ...]
    source: str
    source_url: str
    # optional metadata for production filtering / traceability
    cgi_primary_tumor_type: str = ""
    cgi_primary_tumor_type_full_name: str = ""
    cgi_evidence_level: str = ""
    cgi_association: str = ""
    civic_disease: str = ""
    civic_doid: str = ""
    civic_amp_category: str = ""


def _norm_text(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    s = str(v).strip()
    if s.lower() == "nan":
        return ""
    return s


def _norm_gene(gene: str) -> str:
    return _norm_text(gene).upper()


def _split_tokens(s: str) -> list[str]:
    s = _norm_text(s)
    if not s:
        return []
    parts = re.split(r"[;,]\s*|\s+/\s+|\s*\+\s*", s)
    out: list[str] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        out.append(p)
    return out


def _mk_item(name: str, tag: str) -> str:
    name = _norm_text(name)
    if not name:
        return ""
    return f"{name}（{tag}）"


def _parse_gene_from_civic_profile(profile: str) -> str:
    s = _norm_text(profile)
    if not s:
        return ""
    if s.startswith("v::"):
        s = s[len("v::") :].strip()
    m = re.match(r"^([A-Za-z0-9]+)", s)
    return _norm_gene(m.group(1)) if m else ""


def _infer_alteration_from_civic_profile(profile: str) -> tuple[str, str, str]:
    """Infer (alteration_type, c_point, p_point) from CIViC molecular_profile string."""
    s = _norm_text(profile)
    if s.startswith("v::"):
        s = s[len("v::") :].strip()
    lower = s.lower()

    # CNA-like
    if "amplification" in lower or "amp" in lower:
        return "CNA", "", ""
    if "deletion" in lower or "del" in lower:
        return "CNA", "", ""

    # Fusions
    if "fusion" in lower:
        return "FUS", "", ""

    # Try to capture a simple protein token (e.g., V600E, T790M)
    m = re.search(r"\b([A-Za-z])(\d+)([A-Za-z\*])\b", s)
    if m:
        p = f"p.{m.group(1).upper()}{m.group(2)}{m.group(3).upper()}"
        return "MUT", "", p

    return "", "", ""


def civic_assertions_to_tips(df: pd.DataFrame) -> list[TargetedTip]:
    tips: list[TargetedTip] = []

    required = {"molecular_profile", "therapies", "assertion_type", "significance", "amp_category"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CIViC AssertionSummaries missing columns: {sorted(missing)}")

    sub = df[
        (df["assertion_type"].astype(str) == "Predictive")
        & (df["significance"].astype(str).isin(["Sensitivity/Response", "Resistance"]))
        & (~df.get("is_flagged", False).astype(bool))
    ].copy()

    for _, r in sub.iterrows():
        gene = _parse_gene_from_civic_profile(r.get("molecular_profile"))
        if not gene:
            continue

        alteration_type, c_point, p_point = _infer_alteration_from_civic_profile(
            r.get("molecular_profile")
        )

        amp = _norm_text(r.get("amp_category")) or "CIViC"
        url = _norm_text(r.get("assertion_civic_url") or r.get("molecular_profile_civic_url"))

        therapies = _split_tokens(r.get("therapies"))
        items = tuple(_mk_item(x, f"CIViC:{amp}") for x in therapies if _mk_item(x, f"CIViC:{amp}"))

        significance = _norm_text(r.get("significance"))
        if significance == "Sensitivity/Response":
            benefit, caution = items, tuple()
        else:
            benefit, caution = tuple(), items

        tips.append(
            TargetedTip(
                gene=gene,
                alteration_type=alteration_type,
                c_point=c_point,
                p_point=p_point,
                benefit_items=benefit,
                caution_items=caution,
                source="CIViC",
                source_url=url,
                civic_disease=_norm_text(r.get("disease")),
                civic_doid=_norm_text(r.get("doid")),
                civic_amp_category=_norm_text(r.get("amp_category")),
            )
        )

    return tips


def _cgi_row_is_immunotherapy(row: pd.Series) -> bool:
    parts = [
        _norm_text(row.get("Drug")),
        _norm_text(row.get("Drug full name")),
        _norm_text(row.get("Drug family")),
    ]
    text = (";".join([p for p in parts if p])).lower()
    return any(k in text for k in IMMUNO_DRUG_KEYWORDS)


def _parse_cgi_alteration(
    gene: str, alteration_type: str, alteration: str
) -> tuple[str, str, str]:
    """Infer (alt_type, c_point, p_point) from CGI fields."""
    gene = _norm_gene(gene)
    alt_type = _norm_text(alteration_type)
    alt = _norm_text(alteration)

    # CGI uses patterns like GENE:V600E / GENE:amp / GENE:del / GENE:over / GENE:norm / GENE:.
    # For multi-gene biomarkers it may be "GENE1:...;GENE2:...".
    if ";" in alt:
        # handled upstream (we pass per-gene alt when possible)
        pass

    if ":" in alt:
        _, tail = alt.split(":", 1)
    else:
        tail = alt
    tail = tail.strip()

    # CNA markers
    if tail in {"amp", "del", "gain", "loss", "over", "norm"}:
        return alt_type or "CNA", "", ""

    # Ranges / unknowns (e.g., "268-471", ".", "")
    if not tail or tail == "." or re.fullmatch(r"\d+\s*-\s*\d+", tail):
        return alt_type, "", ""

    # Protein-like token (A692V, V600E, T790M)
    m = re.fullmatch(r"([A-Za-z])(\d+)([A-Za-z\*])", tail)
    if m:
        p_point = f"p.{m.group(1).upper()}{m.group(2)}{m.group(3).upper()}"
        return alt_type or "MUT", "", p_point

    # Fallback: not safely parseable
    return alt_type, "", ""


def _explode_cgi_row(row: pd.Series) -> list[tuple[str, str, str]]:
    """Return [(gene, alt_type, alt_str)] per gene in this row."""
    gene_field = _norm_text(row.get("Gene"))
    if not gene_field:
        return []

    genes = [g.strip() for g in gene_field.split(";") if g.strip()]
    alt_type_field = _norm_text(row.get("Alteration type"))
    alt_types = [x.strip() for x in alt_type_field.split(";") if x.strip()] if alt_type_field else []
    alteration_field = _norm_text(row.get("Alteration"))

    # Try to map alteration parts per gene: "G1:...;G2:..."
    alt_map: dict[str, str] = {}
    for part in [p.strip() for p in alteration_field.split(";") if p.strip()]:
        if ":" in part:
            g, tail = part.split(":", 1)
            alt_map[_norm_gene(g)] = f"{_norm_gene(g)}:{tail.strip()}"

    out = []
    for i, g in enumerate(genes):
        gene = _norm_gene(g)
        alt = alt_map.get(gene, alteration_field)
        at = alt_types[i] if i < len(alt_types) else alt_type_field
        out.append((gene, at, alt))
    return out


def cgi_biomarkers_to_tips(df: pd.DataFrame) -> list[TargetedTip]:
    tips: list[TargetedTip] = []

    required = {"Gene", "Alteration type", "Alteration", "Drug", "Association", "Evidence level", "Source"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CGI biomarkers missing columns: {sorted(missing)}")

    # keep response/resistance signals; ignore toxicity-only rows by default
    allowed_assoc = {"Responsive", "Resistant", "No Responsive"}
    sub = df[df["Association"].astype(str).isin(sorted(allowed_assoc))].copy()

    for _, r in sub.iterrows():
        evidence = _norm_text(r.get("Evidence level")) or "CGI"
        source = _norm_text(r.get("Source"))
        source_tag = f"CGI:{evidence}"
        drugs = [d for d in _split_tokens(r.get("Drug")) if d and d != "[]"]
        if not drugs:
            # Some rows have no explicit drug list; skip (cannot populate report field).
            continue

        items = tuple(_mk_item(d, source_tag) for d in drugs if _mk_item(d, source_tag))
        if not items:
            continue

        assoc = _norm_text(r.get("Association"))
        primary_tt = _norm_text(r.get("Primary Tumor type"))
        primary_tt_full = _norm_text(r.get("Primary Tumor type full name"))
        for gene, alt_type, alt in _explode_cgi_row(r):
            alt_type, c_point, p_point = _parse_cgi_alteration(gene, alt_type, alt)
            if assoc == "Responsive":
                benefit, caution = items, tuple()
            else:
                benefit, caution = tuple(), items

            tips.append(
                TargetedTip(
                    gene=gene,
                    alteration_type=alt_type,
                    c_point=c_point,
                    p_point=p_point,
                    benefit_items=benefit,
                    caution_items=caution,
                    source="CGI",
                    source_url=source,
                    cgi_primary_tumor_type=primary_tt,
                    cgi_primary_tumor_type_full_name=primary_tt_full,
                    cgi_evidence_level=evidence,
                    cgi_association=assoc,
                )
            )

    return tips


def _find_targeted_sheet(path: Path) -> Optional[tuple[str, pd.DataFrame]]:
    if not path.exists():
        return None
    try:
        xl = pd.ExcelFile(str(path), engine="openpyxl")
    except Exception:
        return None

    for sheet in xl.sheet_names:
        try:
            df = xl.parse(sheet)
        except Exception:
            continue
        cols = [str(c).strip() for c in df.columns]
        if TARGETED_DB_REQUIRED_COLS["gene"] not in cols:
            continue
        if not any("潜在获益靶向药物" in c for c in cols):
            continue
        if not any(("可能耐药" in c) or ("慎重" in c) for c in cols):
            continue
        return sheet, df
    return None


def _tips_to_dataframe(tips: Iterable[TargetedTip]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for t in tips:
        rows.append(
            {
                "基因名称": t.gene,
                "变异等级": "",
                "c_point": t.c_point,
                "p_point": t.p_point,
                "扩增/缺失/融合/胚系/未见突变": t.alteration_type,
                "潜在获益靶向药物（证据等级）": "\n".join(sorted({x for x in t.benefit_items if x})) or "--",
                "可能耐药或慎重药物（证据等级）": "\n".join(sorted({x for x in t.caution_items if x})) or "--",
                "source_db": t.source,
                "source_ref": t.source_url,
                "cgi_primary_tumor_type": t.cgi_primary_tumor_type,
                "cgi_primary_tumor_type_full_name": t.cgi_primary_tumor_type_full_name,
                "cgi_evidence_level": t.cgi_evidence_level,
                "cgi_association": t.cgi_association,
                "civic_disease": t.civic_disease,
                "civic_doid": t.civic_doid,
                "civic_amp_category": t.civic_amp_category,
            }
        )
    return pd.DataFrame(rows)


def _build_targeted_db(
    *,
    civic_assertions_tsv: Path,
    cgi_biomarkers_tsv: Path,
    internal_targeted_db: Optional[Path],
    out_path: Path,
) -> dict[str, Any]:
    civic_df = pd.read_csv(civic_assertions_tsv, sep="\t")
    cgi_df = pd.read_csv(cgi_biomarkers_tsv, sep="\t")

    civic_tips = civic_assertions_to_tips(civic_df)
    cgi_tips = cgi_biomarkers_to_tips(cgi_df)
    public_df = _tips_to_dataframe([*civic_tips, *cgi_tips])

    internal_sheet = None
    internal_df = None
    if internal_targeted_db and internal_targeted_db.exists():
        found = _find_targeted_sheet(internal_targeted_db)
        if found:
            internal_sheet, internal_df = found

    def normalize_internal(df: pd.DataFrame) -> pd.DataFrame:
        cols = [str(c).strip() for c in df.columns]
        benefit_col = next((c for c in cols if "潜在获益靶向药物" in c), None)
        caution_col = next((c for c in cols if ("可能耐药" in c) or ("慎重" in c)), None)
        if benefit_col is None or caution_col is None:
            raise ValueError("internal_targeted_db sheet missing benefit/caution columns")

        rename = {
            "基因名称": "基因名称",
            "变异等级": "变异等级",
            "c_point": "c_point",
            "p_point": "p_point",
            "扩增/缺失/融合/胚系/未见突变": "扩增/缺失/融合/胚系/未见突变",
            benefit_col: TARGETED_DB_REQUIRED_COLS["benefit"],
            caution_col: TARGETED_DB_REQUIRED_COLS["caution"],
        }
        out = df.rename(columns=rename).copy()
        for k in [
            "基因名称",
            "变异等级",
            "c_point",
            "p_point",
            "扩增/缺失/融合/胚系/未见突变",
            TARGETED_DB_REQUIRED_COLS["benefit"],
            TARGETED_DB_REQUIRED_COLS["caution"],
        ]:
            if k not in out.columns:
                out[k] = ""
        out["source_db"] = "internal"
        out["source_ref"] = str(internal_targeted_db) if internal_targeted_db else ""
        # keep column compatibility with public-derived metadata
        out["cgi_primary_tumor_type"] = ""
        out["cgi_primary_tumor_type_full_name"] = ""
        out["cgi_evidence_level"] = ""
        out["cgi_association"] = ""
        out["civic_disease"] = ""
        out["civic_doid"] = ""
        out["civic_amp_category"] = ""
        return out[
            [
                "基因名称",
                "变异等级",
                "c_point",
                "p_point",
                "扩增/缺失/融合/胚系/未见突变",
                TARGETED_DB_REQUIRED_COLS["benefit"],
                TARGETED_DB_REQUIRED_COLS["caution"],
                "source_db",
                "source_ref",
                "cgi_primary_tumor_type",
                "cgi_primary_tumor_type_full_name",
                "cgi_evidence_level",
                "cgi_association",
                "civic_disease",
                "civic_doid",
                "civic_amp_category",
            ]
        ]

    combined_parts = []
    if internal_df is not None:
        combined_parts.append(normalize_internal(internal_df))
    combined_parts.append(public_df)
    combined_df = pd.concat(combined_parts, ignore_index=True, sort=False)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        # NOTE: FieldMapper currently loads the *first* usable sheet; keep the combined sheet first.
        combined_df.to_excel(writer, sheet_name="targeted_drug_tips", index=False)
        if internal_df is not None:
            internal_df.to_excel(writer, sheet_name="internal_targeted_drug_tips", index=False)
        public_df.to_excel(writer, sheet_name="public_targeted_drug_tips", index=False)

        meta = pd.DataFrame(
            [
                {
                    "source": "CIViC AssertionSummaries",
                    "path_or_url": str(civic_assertions_tsv),
                    "license": "CC0 (per https://civicdb.org/releases/licensing)",
                    "rows_used": len(civic_tips),
                },
                {
                    "source": "CGI Biomarkers",
                    "path_or_url": str(cgi_biomarkers_tsv),
                    "license": "CC0 (per https://creativecommons.org/publicdomain/zero/1.0/)",
                    "rows_used": len(cgi_tips),
                },
                {
                    "source": "internal_targeted_db",
                    "path_or_url": str(internal_targeted_db) if internal_targeted_db else "",
                    "license": "internal",
                    "rows_used": int(internal_df.shape[0]) if internal_df is not None else 0,
                    "sheet": internal_sheet or "",
                },
            ]
        )
        meta.to_excel(writer, sheet_name="meta", index=False)

    return {
        "output": str(out_path),
        "combined_rows": int(combined_df.shape[0]),
        "public_rows": int(public_df.shape[0]),
        "internal_rows": int(internal_df.shape[0]) if internal_df is not None else 0,
    }


def _extract_gene_set_from_sheet(df: pd.DataFrame, col_names: list[str]) -> set[str]:
    genes: set[str] = set()
    for col in col_names:
        if col not in df.columns:
            continue
        for v in df[col].tolist():
            s = _norm_text(v)
            if not s or s == "基因":
                continue
            # allow notes after whitespace (e.g., "EGFR 只要扩增")
            genes.add(s.split()[0].strip().upper())
    return genes


def _build_immune_list(
    *,
    cgi_biomarkers_tsv: Path,
    internal_immune_list: Optional[Path],
    out_path: Path,
) -> dict[str, Any]:
    base_pos: set[str] = set()
    base_neg: set[str] = set()
    base_hyper: set[str] = set()

    if internal_immune_list and internal_immune_list.exists():
        df = pd.read_excel(internal_immune_list, sheet_name=0, engine="openpyxl")
        base_pos = _extract_gene_set_from_sheet(df, ["免疫治疗正相关基因", "Unnamed: 1", "Unnamed: 2"])
        base_neg = _extract_gene_set_from_sheet(df, ["免疫治疗负相关基因", "Unnamed: 4", "Unnamed: 5"])
        base_hyper = _extract_gene_set_from_sheet(df, ["免疫超进展相关基因", "Unnamed: 7"])

    cgi_df = pd.read_csv(cgi_biomarkers_tsv, sep="\t")
    # select immunotherapy-related rows by keywords
    imm = cgi_df[cgi_df.apply(_cgi_row_is_immunotherapy, axis=1)].copy()

    add_pos: set[str] = set()
    add_neg: set[str] = set()
    for _, r in imm.iterrows():
        assoc = _norm_text(r.get("Association"))
        genes = [_norm_gene(g) for g, _, _ in _explode_cgi_row(r)]
        if assoc == "Responsive":
            add_pos |= set(genes)
        elif assoc in {"Resistant", "No Responsive"}:
            add_neg |= set(genes)

    pos = sorted((base_pos | add_pos) - {""})
    neg = sorted((base_neg | add_neg) - {""})
    hyper = sorted(base_hyper - {""})

    # Build a compact sheet with 3 columns (the loader in reportgen is tolerant to missing Unnamed columns).
    max_len = max(len(pos), len(neg), len(hyper), 1)
    rows = []
    for i in range(max_len + 1):  # + header row
        rows.append(
            {
                "免疫治疗正相关基因": "基因" if i == 0 else (pos[i - 1] if i - 1 < len(pos) else ""),
                "免疫治疗负相关基因": "基因" if i == 0 else (neg[i - 1] if i - 1 < len(neg) else ""),
                "免疫超进展相关基因": "基因" if i == 0 else (hyper[i - 1] if i - 1 < len(hyper) else ""),
            }
        )
    out_df = pd.DataFrame(rows)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        out_df.to_excel(writer, sheet_name="immune_gene_list", index=False)
        meta = pd.DataFrame(
            [
                {
                    "source": "CGI Biomarkers (immunotherapy subset)",
                    "path_or_url": str(cgi_biomarkers_tsv),
                    "license": "CC0",
                    "rows_matched": int(imm.shape[0]),
                    "pos_added": len(add_pos),
                    "neg_added": len(add_neg),
                },
                {
                    "source": "internal_immune_gene_list",
                    "path_or_url": str(internal_immune_list) if internal_immune_list else "",
                    "license": "internal",
                    "pos": len(base_pos),
                    "neg": len(base_neg),
                    "hyper": len(base_hyper),
                },
            ]
        )
        meta.to_excel(writer, sheet_name="meta", index=False)

    return {
        "output": str(out_path),
        "pos": len(pos),
        "neg": len(neg),
        "hyper": len(hyper),
        "cgi_rows_matched": int(imm.shape[0]),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--civic-assertions", default=DEFAULT_CIVIC_ASSERTIONS, help="CIViC AssertionSummaries TSV path")
    ap.add_argument("--cgi-biomarkers", default=DEFAULT_CGI_BIOMARKERS, help="CGI biomarkers TSV path")
    ap.add_argument(
        "--internal-targeted-db",
        default=DEFAULT_INTERNAL_TARGETED_DB,
        help="existing internal targeted drug db xlsx (optional)",
    )
    ap.add_argument(
        "--internal-immune-list",
        default=DEFAULT_INTERNAL_IMMUNE_LIST,
        help="existing internal immune gene list xlsx (optional)",
    )
    ap.add_argument("--out-targeted", default=DEFAULT_OUT_TARGETED, help="output targeted drug db xlsx path")
    ap.add_argument("--out-immune", default=DEFAULT_OUT_IMMUNE, help="output immune gene list xlsx path")
    args = ap.parse_args()

    civic = Path(args.civic_assertions)
    cgi = Path(args.cgi_biomarkers)
    if not civic.exists():
        raise SystemExit(f"Missing input: {civic}")
    if not cgi.exists():
        raise SystemExit(f"Missing input: {cgi}")

    internal_targeted = Path(args.internal_targeted_db) if args.internal_targeted_db else None
    internal_immune = Path(args.internal_immune_list) if args.internal_immune_list else None

    out_targeted = Path(args.out_targeted)
    out_immune = Path(args.out_immune)

    t_stats = _build_targeted_db(
        civic_assertions_tsv=civic,
        cgi_biomarkers_tsv=cgi,
        internal_targeted_db=internal_targeted,
        out_path=out_targeted,
    )
    i_stats = _build_immune_list(
        cgi_biomarkers_tsv=cgi,
        internal_immune_list=internal_immune,
        out_path=out_immune,
    )

    print("OK")
    print("targeted_db:", t_stats)
    print("immune_list:", i_stats)


if __name__ == "__main__":
    main()
