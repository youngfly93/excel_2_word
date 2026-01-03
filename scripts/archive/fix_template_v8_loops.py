#!/usr/bin/env python3
"""
修复 v8 模板的表格循环结构错误

问题：当前模板的 {%tr for %}...{%tr endfor %} 都在同一行
     导致 docxtpl 处理时只保留 endfor，丢失 for 和所有内容

解决方案：将每个循环拆分为3行：
    Row 1: {%tr for ...%}  <- 只包含循环开始标签
    Row 2: content with {{ row.xxx }}  <- 实际内容，会被重复
    Row 3: {%tr endfor %}  <- 只包含循环结束标签
"""

import os
import shutil
import zipfile
import re
from pathlib import Path

def unpack_docx(docx_path: str, output_dir: str):
    """解压docx文件"""
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    with zipfile.ZipFile(docx_path, 'r') as zip_ref:
        zip_ref.extractall(output_dir)

def pack_docx(input_dir: str, output_path: str):
    """打包docx文件"""
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(input_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, input_dir)
                zipf.write(file_path, arcname)

def create_for_row(loop_var: str) -> str:
    """创建只包含 {%tr for %} 的行"""
    return f'''<w:tr><w:trPr><w:trHeight w:val="0" w:hRule="auto"/></w:trPr><w:tc><w:tcPr><w:tcW w:w="0" w:type="auto"/></w:tcPr><w:p><w:r><w:t>{{%tr for {loop_var} %}}</w:t></w:r></w:p></w:tc></w:tr>'''

def create_endfor_row() -> str:
    """创建只包含 {%tr endfor %} 的行"""
    return '''<w:tr><w:trPr><w:trHeight w:val="0" w:hRule="auto"/></w:trPr><w:tc><w:tcPr><w:tcW w:w="0" w:type="auto"/></w:tcPr><w:p><w:r><w:t>{%tr endfor %}</w:t></w:r></w:p></w:tc></w:tr>'''

def fix_table_loop(xml_content: str, loop_name: str) -> str:
    """
    修复单个表格循环

    找到包含 {%tr for loop_name %} 和 {%tr endfor %} 的行
    将其拆分为3行
    """
    # 构建匹配模式
    for_pattern = rf'\{{%tr for ({loop_name}) %\}}'

    # 找到 {%tr for ...%} 的位置
    for_match = re.search(for_pattern, xml_content)
    if not for_match:
        print(f"  未找到循环: {loop_name}")
        return xml_content

    for_pos = for_match.start()
    loop_var = for_match.group(1)
    print(f"  找到循环: {loop_var} at position {for_pos}")

    # 找到这个位置所在的 <w:tr> 行
    tr_start_pattern = r'<w:tr[\s>]'
    tr_matches = list(re.finditer(tr_start_pattern, xml_content[:for_pos]))
    if not tr_matches:
        print(f"  错误：找不到包含循环的表格行")
        return xml_content

    row_start = tr_matches[-1].start()

    # 找到 </w:tr> 结束位置
    row_end = xml_content.find("</w:tr>", for_pos) + len("</w:tr>")

    # 提取原始行内容
    original_row = xml_content[row_start:row_end]
    print(f"  原始行长度: {len(original_row)}")

    # 检查是否同时包含 for 和 endfor
    if "{%tr endfor %}" not in original_row:
        print(f"  该行不包含 endfor，可能已经是正确结构")
        return xml_content

    # 创建内容行 - 移除 {%tr for %} 和 {%tr endfor %}
    content_row = original_row
    content_row = re.sub(rf'\{{%tr for {loop_var} %\}}', '', content_row)
    content_row = re.sub(r'\{%tr endfor %\}', '', content_row)

    # 构建新的3行结构
    new_structure = create_for_row(loop_var) + "\n" + content_row + "\n" + create_endfor_row()

    # 替换原始行
    new_content = xml_content[:row_start] + new_structure + xml_content[row_end:]

    print(f"  已修复循环: {loop_var}")
    print(f"  原始行被替换为3行结构")

    return new_content

def main():
    base_dir = Path("/mnt/g/work/minhao/肠癌358基因")
    template_v8 = base_dir / "templates" / "jinja2_template_358_v8.docx"
    template_v8_fixed = base_dir / "templates" / "jinja2_template_358_v8_fixed.docx"
    temp_dir = Path("/tmp/template_v8_fix")

    print(f"输入模板: {template_v8}")
    print(f"输出模板: {template_v8_fixed}")

    # 解包
    print("\n1. 解包模板...")
    unpack_docx(str(template_v8), str(temp_dir))

    # 读取 document.xml
    doc_xml_path = temp_dir / "word" / "document.xml"
    with open(doc_xml_path, 'r', encoding='utf-8') as f:
        xml_content = f.read()

    original_len = len(xml_content)
    print(f"   原始XML长度: {original_len}")

    # 修复每个表格循环
    # 需要按顺序处理，因为每次修复会改变位置
    loops_to_fix = [
        "row in variants",
        "row in summary_variants",
        "gene in undetected_genes"
    ]

    print("\n2. 修复表格循环结构...")
    for loop_name in loops_to_fix:
        print(f"\n处理: {loop_name}")
        xml_content = fix_table_loop(xml_content, loop_name)

    # 保存修改
    print(f"\n3. 保存修改后的XML...")
    print(f"   新XML长度: {len(xml_content)} (差异: {len(xml_content) - original_len})")
    with open(doc_xml_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)

    # 打包
    print(f"\n4. 打包新模板...")
    pack_docx(str(temp_dir), str(template_v8_fixed))

    # 清理
    shutil.rmtree(temp_dir)

    print(f"\n完成！修复后的模板: {template_v8_fixed}")

if __name__ == "__main__":
    main()
