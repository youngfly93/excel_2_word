"""
Docx comparison utility

Compares a generated test report with a reference final report (.docx) and
outputs structured differences to help align templates at a granular level.

Usage:
  python3 tools/compare_docx.py \
      --test data/output/张三-MLB2509307001-报告.docx \
      --ref "孔金华-乙状结肠癌-结直肠癌358基因+msi-mljy-lz243684-终版.docx" \
      --out COMPARISON_DETAILED.md

Notes:
  - Focuses on static elements: headings, table headers, sections, margins,
    header/footer text, paragraph styles.
  - Ignores variable content cells/values by only comparing structures and
    label/header texts.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from docx import Document
from docx.enum.section import WD_ORIENT


def load_doc(path: Path) -> Document:
    return Document(str(path))


def clean_text(s: str) -> str:
    return (s or "").replace("\u200b", "").replace("\xa0", " ").strip()


def para_style_name(p) -> str:
    try:
        return p.style.name or ""
    except Exception:
        return ""


def collect_paragraphs(doc: Document) -> Dict[str, Any]:
    texts = [clean_text(p.text) for p in doc.paragraphs]
    non_empty = [t for t in texts if t]
    style_counts = Counter(para_style_name(p) for p in doc.paragraphs)

    # Candidate anchors: short, likely section labels or headings
    anchors = []
    for p in doc.paragraphs:
        t = clean_text(p.text)
        if not t:
            continue
        # Heuristics: short labels/headings
        if len(t) <= 24 or "：" in t or ":" in t:
            anchors.append((t, para_style_name(p), p.alignment))

    return {
        "total": len(doc.paragraphs),
        "non_empty": len(non_empty),
        "first_non_empty": non_empty[:20],
        "style_counts": dict(style_counts.most_common(20)),
        "anchors": anchors[:200],  # keep a cap
    }


def table_signature(table) -> Tuple[int, int, Tuple[str, ...]]:
    rows = len(table.rows)
    cols = len(table.columns)
    header = ()
    if rows:
        # first non-empty row as header
        for r in table.rows:
            cells = [clean_text(c.text) for c in r.cells]
            if any(cells):
                header = tuple(cells)
                break
    return rows, cols, header


def collect_tables(doc: Document) -> Dict[str, Any]:
    sigs = [table_signature(t) for t in doc.tables]
    rows_cols = [(r, c) for (r, c, _) in sigs]
    header_counter = Counter([h for (_, _, h) in sigs if h])
    size_counter = Counter(rows_cols)
    samples = []
    for i, (r, c, h) in enumerate(sigs[:20]):
        samples.append({"index": i, "rows": r, "cols": c, "header": list(h)})
    return {
        "count": len(doc.tables),
        "top_sizes": size_counter.most_common(10),
        "top_headers": [(list(h), n) for h, n in header_counter.most_common(10)],
        "samples": samples,
    }


def collect_sections(doc: Document) -> Dict[str, Any]:
    data = []
    for i, sec in enumerate(doc.sections):
        orient = "landscape" if sec.orientation == WD_ORIENT.LANDSCAPE else "portrait"
        margins = {
            "left": float(sec.left_margin.cm),
            "right": float(sec.right_margin.cm),
            "top": float(sec.top_margin.cm),
            "bottom": float(sec.bottom_margin.cm),
        }
        page = {
            "width_cm": float(sec.page_width.cm),
            "height_cm": float(sec.page_height.cm),
            "orientation": orient,
        }
        header_text = " ".join(
            clean_text(p.text) for p in sec.header.paragraphs if clean_text(p.text)
        )
        footer_text = " ".join(
            clean_text(p.text) for p in sec.footer.paragraphs if clean_text(p.text)
        )
        data.append(
            {
                "index": i,
                "page": page,
                "margins_cm": margins,
                "header_text": header_text[:200],
                "footer_text": footer_text[:200],
            }
        )
    return {"count": len(doc.sections), "sections": data}


def collect_inline_shapes(doc: Document) -> Dict[str, Any]:
    try:
        shapes = getattr(doc, "inline_shapes", [])
        return {"count": len(shapes)}
    except Exception:
        return {"count": 0}


def summarize(doc_path: Path) -> Dict[str, Any]:
    doc = load_doc(doc_path)
    return {
        "file": str(doc_path),
        "paragraphs": collect_paragraphs(doc),
        "tables": collect_tables(doc),
        "sections": collect_sections(doc),
        "shapes": collect_inline_shapes(doc),
    }


def md_line(s: str) -> str:
    return s.replace("\n", " ")


def render_markdown(test_summary: Dict[str, Any], ref_summary: Dict[str, Any]) -> str:
    def hdr(title: str) -> str:
        return f"\n\n## {title}\n\n"

    out = []
    out.append("# 测试报告 vs 终版报告 结构对比（颗粒度对齐参考）\n")
    out.append("生成时间: 自动\n")

    # Overview
    out.append(hdr("总体指标"))
    out.append("- 测试报告: `{}`\n".format(test_summary["file"]))
    out.append("- 终版报告: `{}`\n".format(ref_summary["file"]))
    out.append(
        "- 段落: 测试 {} | 终版 {}\n".format(
            test_summary["paragraphs"]["total"], ref_summary["paragraphs"]["total"]
        )
    )
    out.append(
        "- 表格: 测试 {} | 终版 {}\n".format(
            test_summary["tables"]["count"], ref_summary["tables"]["count"]
        )
    )
    out.append(
        "- 分节: 测试 {} | 终版 {}\n".format(
            test_summary["sections"]["count"], ref_summary["sections"]["count"]
        )
    )

    # Sections details
    out.append(hdr("页面与分节"))
    for label, s in [("测试", test_summary), ("终版", ref_summary)]:
        out.append(f"- {label} 分节数: {s['sections']['count']}\n")
        for sec in s["sections"]["sections"][:5]:
            out.append(
                f"  - 节#{sec['index']}: {sec['page']['orientation']} {sec['page']['width_cm']}x{sec['page']['height_cm']}cm 边距(cm) L{sec['margins_cm']['left']} R{sec['margins_cm']['right']} T{sec['margins_cm']['top']} B{sec['margins_cm']['bottom']}\n"
            )

    # Paragraphs
    out.append(hdr("段落/样例标题锚点"))
    out.append("- 测试报告 前20个非空段落：\n")
    for t in test_summary["paragraphs"]["first_non_empty"][:20]:
        out.append(f"  - {md_line(t)}\n")
    out.append("- 终版报告 前20个非空段落：\n")
    for t in ref_summary["paragraphs"]["first_non_empty"][:20]:
        out.append(f"  - {md_line(t)}\n")

    # Tables
    out.append(hdr("表格结构"))
    out.append("- 测试报告 Top 表格头(前10)：\n")
    for header, n in test_summary["tables"]["top_headers"]:
        head = " | ".join([md_line(x) for x in header])
        out.append(f"  - x{n} :: {head}\n")
    out.append("- 终版报告 Top 表格头(前10)：\n")
    for header, n in ref_summary["tables"]["top_headers"]:
        head = " | ".join([md_line(x) for x in header])
        out.append(f"  - x{n} :: {head}\n")

    # Alignment suggestions
    out.append(hdr("对齐建议（静态区域）"))
    out.append("- 页面设置：按终版的页面方向与边距配置模板。\n")
    out.append("- 分节数量与顺序：模板按终版的分节划分封面/目录/正文/附录。\n")
    out.append("- 段落标题文案：将模板中的固定标题与终版一致（标点/空格/换行）。\n")
    out.append("- 表格数量与顺序：依据终版的表格序列设置模板中的空表结构。\n")
    out.append("- 表头文字：模板表头与终版逐字对齐，保持列数一致。\n")
    out.append("- 页眉/页脚：拷贝终版的固定文本与版式（含页码样式）。\n")
    out.append("- 图片/Logo/页眉线：比照终版放置固定资源（统一尺寸与位置）。\n")
    out.append("- 禁止改动区域：标注仅变量可变，其余文字保持一致。\n")

    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", required=True, help="path to test/generated docx")
    ap.add_argument("--ref", required=True, help="path to reference final docx")
    ap.add_argument(
        "--out", default="COMPARISON_DETAILED.md", help="output markdown file"
    )
    args = ap.parse_args()

    test_path = Path(args.test)
    ref_path = Path(args.ref)

    test_summary = summarize(test_path)
    ref_summary = summarize(ref_path)

    md = render_markdown(test_summary, ref_summary)
    Path(args.out).write_text(md, encoding="utf-8")
    print(f"Written: {args.out}")


if __name__ == "__main__":
    main()

