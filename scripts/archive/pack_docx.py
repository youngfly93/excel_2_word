#!/usr/bin/env python3
"""Pack unpacked OOXML directory back into .docx file (Python 3.9 compatible)."""

import sys
import os
import zipfile
from pathlib import Path

def pack_document(input_dir, output_file):
    """Pack directory into .docx file."""
    input_path = Path(input_dir)
    output_path = Path(output_file)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create the docx (which is a zip file)
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in input_path.rglob('*'):
            if file_path.is_file():
                # Get relative path from input directory
                rel_path = file_path.relative_to(input_path)
                # Add to zip
                zf.write(file_path, rel_path)
                print(f"  Added: {rel_path}")

    print(f"\nPacked to: {output_path}")
    print(f"File size: {output_path.stat().st_size:,} bytes")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python pack_docx.py <input_dir> <output_file>")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_file = sys.argv[2]

    print(f"Packing: {input_dir}")
    print(f"Output: {output_file}")
    print("-" * 40)

    pack_document(input_dir, output_file)
