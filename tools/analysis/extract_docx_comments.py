"""
Extract Word (.docx) comments with anchors and approximate locations.

This tool is meant for reverse-engineering "mapping contracts" embedded as
Word comments/annotations (批注) in a final report. It reads:
  - comment bodies from `word/comments.xml`
  - comment anchors from `word/document.xml` and other parts (headers/footers/
    footnotes/endnotes when present)

It outputs a JSON that merges:
  - comment metadata (id/author/date/text)
  - anchor text captured inside comment ranges (when the range contains text)
  - reference location: part + table/row/cell + paragraph text + cell text

Usage:
  python3 tools/analysis/extract_docx_comments.py \
      --docx "2025.12.10/对应关系：苏雨起-...-终版.docx" \
      --out data/output/analysis/docx_comment_map.json
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import xml.etree.ElementTree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"


def _clean_text(s: str) -> str:
    s = (s or "").replace("\u200b", "").replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _attr(elem: ET.Element, local_name: str) -> Optional[str]:
    return elem.attrib.get(f"{W}{local_name}") or elem.attrib.get(local_name)


def _extract_text(elem: ET.Element) -> str:
    parts: List[str] = []
    for node in elem.iter():
        if node.tag in (f"{W}t", f"{W}instrText", f"{W}delText"):
            if node.text:
                parts.append(node.text)
        elif node.tag in (f"{W}br", f"{W}cr"):
            parts.append("\n")
        elif node.tag == f"{W}tab":
            parts.append("\t")
    return "".join(parts)


def _iter_doc_parts(zf: zipfile.ZipFile) -> List[str]:
    names = set(zf.namelist())
    parts = []
    for base in ["word/document.xml", "word/footnotes.xml", "word/endnotes.xml"]:
        if base in names:
            parts.append(base)

    # headers/footers can be header1.xml, header2.xml, ...
    for n in sorted(names):
        if re.fullmatch(r"word/header\d+\.xml", n) or re.fullmatch(r"word/footer\d+\.xml", n):
            parts.append(n)
    return parts


def _parse_comments_xml(xml_bytes: bytes) -> Dict[str, Dict[str, Any]]:
    root = ET.fromstring(xml_bytes)
    comments: Dict[str, Dict[str, Any]] = {}
    for c in root.findall(f".//{W}comment"):
        cid = _attr(c, "id")
        if cid is None:
            continue

        paras = c.findall(f"./{W}p")
        if not paras:
            paras = c.findall(f".//{W}p")

        text = "\n".join(_clean_text(_extract_text(p)) for p in paras if _clean_text(_extract_text(p)))
        comments[str(cid)] = {
            "cid": str(cid),
            "author": _attr(c, "author") or "",
            "date": _attr(c, "date") or "",
            "initials": _attr(c, "initials") or "",
            "text": text,
        }
    return comments


@dataclass(frozen=True)
class Location:
    part: str
    table_index: Optional[int]
    row_index: Optional[int]
    cell_index: Optional[int]
    paragraph_index: Optional[int]
    paragraph_text: str
    cell_text: str


def _walk_part(xml_bytes: bytes, part_name: str) -> Dict[str, Any]:
    root = ET.fromstring(xml_bytes)

    active: List[str] = []
    range_text: Dict[str, List[str]] = {}
    range_starts: Dict[str, List[Location]] = {}
    references: Dict[str, List[Location]] = {}

    def record_start(cid: str, ctx: Dict[str, Any], paragraph_text: str) -> None:
        loc = Location(
            part=part_name,
            table_index=ctx.get("table_index"),
            row_index=ctx.get("row_index"),
            cell_index=ctx.get("cell_index"),
            paragraph_index=ctx.get("paragraph_index"),
            paragraph_text=_clean_text(paragraph_text),
            cell_text=_clean_text(ctx.get("cell_text") or ""),
        )
        range_starts.setdefault(cid, []).append(loc)

    def record_ref(cid: str, ctx: Dict[str, Any], paragraph_text: str) -> None:
        loc = Location(
            part=part_name,
            table_index=ctx.get("table_index"),
            row_index=ctx.get("row_index"),
            cell_index=ctx.get("cell_index"),
            paragraph_index=ctx.get("paragraph_index"),
            paragraph_text=_clean_text(paragraph_text),
            cell_text=_clean_text(ctx.get("cell_text") or ""),
        )
        references.setdefault(cid, []).append(loc)

    def append_text(txt: str) -> None:
        if not txt:
            return
        for cid in active:
            range_text.setdefault(cid, []).append(txt)

    def walk(elem: ET.Element, ctx: Dict[str, Any]) -> None:
        tag = elem.tag

        if tag == f"{W}tbl":
            table_index = ctx["next_table_index"]
            ctx["next_table_index"] += 1
            inner = dict(ctx)
            inner.update(
                {
                    "table_index": table_index,
                    "row_index": None,
                    "cell_index": None,
                    "next_row_index": 0,
                }
            )
            for child in list(elem):
                walk(child, inner)
            return

        if tag == f"{W}tr":
            row_index = ctx.get("next_row_index", 0)
            inner = dict(ctx)
            inner.update({"row_index": row_index, "cell_index": None, "next_cell_index": 0})
            inner["next_row_index"] = row_index + 1
            for child in list(elem):
                walk(child, inner)
            return

        if tag == f"{W}tc":
            cell_index = ctx.get("next_cell_index", 0)
            inner = dict(ctx)
            inner.update({"cell_index": cell_index})
            inner["next_cell_index"] = cell_index + 1
            inner["cell_text"] = _extract_text(elem)
            for child in list(elem):
                walk(child, inner)
            return

        if tag == f"{W}p":
            paragraph_index = ctx["next_paragraph_index"]
            ctx["next_paragraph_index"] += 1
            paragraph_text = _extract_text(elem)
            inner = dict(ctx)
            inner.update({"paragraph_index": paragraph_index, "paragraph_text": paragraph_text})
            for child in list(elem):
                walk(child, inner)
            # paragraph-level tail text is not expected in w:p; ignore.
            return

        if tag == f"{W}commentRangeStart":
            cid = _attr(elem, "id")
            if cid is not None:
                active.append(str(cid))
                if str(cid) not in range_text:
                    range_text[str(cid)] = []
                record_start(str(cid), ctx, ctx.get("paragraph_text") or "")
            return

        if tag == f"{W}commentRangeEnd":
            cid = _attr(elem, "id")
            if cid is not None:
                cid = str(cid)
                for i in range(len(active) - 1, -1, -1):
                    if active[i] == cid:
                        active.pop(i)
                        break
            return

        if tag == f"{W}commentReference":
            cid = _attr(elem, "id")
            if cid is not None:
                record_ref(str(cid), ctx, ctx.get("paragraph_text") or "")
            return

        if tag in (f"{W}t", f"{W}instrText", f"{W}delText"):
            append_text(elem.text or "")

        if tag in (f"{W}br", f"{W}cr"):
            append_text("\n")
        elif tag == f"{W}tab":
            append_text("\t")

        # Recurse
        for child in list(elem):
            walk(child, ctx)

    ctx0: Dict[str, Any] = {
        "next_table_index": 0,
        "table_index": None,
        "row_index": None,
        "cell_index": None,
        "next_paragraph_index": 0,
        "paragraph_index": None,
        "cell_text": "",
        "paragraph_text": "",
    }
    walk(root, ctx0)

    return {
        "range_text": {k: _clean_text("".join(v)) for k, v in range_text.items()},
        "range_starts": range_starts,
        "references": references,
    }


def _loc_to_dict(loc: Location) -> Dict[str, Any]:
    return {
        "part": loc.part,
        "table_index": loc.table_index,
        "row_index": loc.row_index,
        "cell_index": loc.cell_index,
        "paragraph_index": loc.paragraph_index,
        "paragraph_text": loc.paragraph_text,
        "cell_text": loc.cell_text,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx", required=True, help="input .docx path")
    ap.add_argument("--out", required=True, help="output JSON path")
    args = ap.parse_args()

    docx_path = Path(args.docx)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(docx_path, "r") as zf:
        if "word/comments.xml" not in zf.namelist():
            raise SystemExit("No comments found: missing word/comments.xml")

        comments = _parse_comments_xml(zf.read("word/comments.xml"))
        parts = _iter_doc_parts(zf)

        part_maps = []
        for part in parts:
            try:
                part_maps.append((part, _walk_part(zf.read(part), part)))
            except KeyError:
                continue

    merged: List[Dict[str, Any]] = []
    for cid, meta in sorted(comments.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else kv[0]):
        anchor_text = ""
        starts: List[Dict[str, Any]] = []
        refs: List[Dict[str, Any]] = []

        for _, pm in part_maps:
            if cid in pm["range_text"] and pm["range_text"][cid]:
                anchor_text = pm["range_text"][cid]
            if cid in pm["range_starts"]:
                starts.extend([_loc_to_dict(x) for x in pm["range_starts"][cid]])
            if cid in pm["references"]:
                refs.extend([_loc_to_dict(x) for x in pm["references"][cid]])

        merged.append(
            {
                **meta,
                "anchor_text": anchor_text,
                "range_starts": starts,
                "references": refs,
            }
        )

    payload = {
        "docx": str(docx_path),
        "comments_count": len(merged),
        "comments": merged,
        "parts_scanned": [p for p, _ in part_maps],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote: {out_path} (comments={len(merged)})")


if __name__ == "__main__":
    main()
