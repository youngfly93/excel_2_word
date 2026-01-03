"""
Sanitize a .docx by removing invalid relationships that target 'NULL' to make
it readable by python-docx/docxtpl.

Usage:
  python3 tools/sanitize_docx.py --in docs/samples/tempe_test.docx --out docs/samples/tempe_test.sanitized.docx
"""

from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def sanitize_rels(data: bytes) -> bytes:
    try:
        tree = ET.fromstring(data)
    except ET.ParseError:
        return data

    changed = False
    # Iterate Relationship elements
    for rel in list(tree):
        if rel.tag.endswith("Relationship"):
            target = rel.attrib.get("Target", "")
            if target.endswith("NULL") or target == "NULL" or "/NULL" in target or "\\NULL" in target:
                tree.remove(rel)
                changed = True

    if not changed:
        return data

    # Serialize back
    buf = io.BytesIO()
    ET.ElementTree(tree).write(buf, encoding="utf-8", xml_declaration=False)
    return buf.getvalue()


def sanitize_docx(src: Path, dst: Path) -> None:
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.endswith(".rels"):
                data = sanitize_rels(data)
            zout.writestr(item, data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="input .docx path")
    ap.add_argument("--out", dest="out", required=True, help="output .docx path")
    args = ap.parse_args()

    src = Path(args.inp)
    dst = Path(args.out)
    sanitize_docx(src, dst)
    print(f"Sanitized docx written: {dst}")


if __name__ == "__main__":
    main()
