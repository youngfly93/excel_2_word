#!/usr/bin/env python3
"""
创建 v9 模板：基于修复后的 v8 模板添加参考文献循环

参考文献使用 {%p for ref in references %}{{ ref }}{%p endfor %} 段落循环
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
    """打包docx文件（排除备份文件）"""
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(input_dir):
            for file in files:
                if '.bak' in file:
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, input_dir)
                zipf.write(file_path, arcname)

def add_reference_loop(xml_content: str) -> str:
    """
    添加参考文献循环：
    1. 找到所有PMID参考文献段落
    2. 用一个循环段落替换它们
    """
    # 找到所有PMID开头的段落位置
    # PMID格式：PMID:数字 开头的段落
    pmid_pattern = r'<w:t[^>]*>PMID:\d+'
    pmid_matches = list(re.finditer(pmid_pattern, xml_content))

    if not pmid_matches:
        print("警告：未找到PMID参考文献")
        return xml_content

    print(f"找到 {len(pmid_matches)} 个PMID参考文献")

    # 找到第一个PMID所在的段落
    first_match = pmid_matches[0]
    first_pos = first_match.start()

    # 向前找到这个段落的开始 <w:p 或 <w:p>
    para_start = xml_content.rfind('<w:p ', 0, first_pos)
    if para_start == -1:
        para_start = xml_content.rfind('<w:p>', 0, first_pos)

    # 找到这个段落的 </w:p>
    para_end = xml_content.find('</w:p>', first_pos) + len('</w:p>')

    # 提取第一个段落的格式信息
    first_para = xml_content[para_start:para_end]
    print(f"第一个参考文献段落长度: {len(first_para)}")

    # 找到最后一个PMID段落的结束位置
    last_match = pmid_matches[-1]
    last_pos = last_match.start()
    last_para_end = xml_content.find('</w:p>', last_pos) + len('</w:p>')

    # 创建循环段落
    # docxtpl的段落循环语法：{%p for item in items %}内容{%p endfor %}
    # 需要放在同一个段落内

    # 提取第一个段落的样式属性（保留编号格式等）
    ppr_match = re.search(r'<w:pPr>(.*?)</w:pPr>', first_para, re.DOTALL)
    ppr_content = ppr_match.group(0) if ppr_match else '<w:pPr></w:pPr>'

    # 提取字体样式
    rpr_match = re.search(r'<w:rPr>(.*?)</w:rPr>', first_para, re.DOTALL)
    rpr_content = rpr_match.group(0) if rpr_match else '<w:rPr></w:rPr>'

    # 创建循环结构 - 必须分开为3个段落！
    # 1. for 标签段落（会被替换为 {% for %}）
    # 2. 内容段落（保留格式，会被重复）
    # 3. endfor 标签段落（会被替换为 {% endfor %}）

    loop_start = '''<w:p><w:r><w:t>{%p for ref in references %}</w:t></w:r></w:p>'''
    loop_content = f'''<w:p>{ppr_content}<w:r>{rpr_content}<w:t>{{{{ ref }}}}</w:t></w:r></w:p>'''
    loop_end = '''<w:p><w:r><w:t>{%p endfor %}</w:t></w:r></w:p>'''

    loop_para = loop_start + loop_content + loop_end

    # 替换所有PMID段落为循环段落
    new_content = xml_content[:para_start] + loop_para + xml_content[last_para_end:]

    print(f"参考文献部分已更新：删除了 {len(pmid_matches)} 个硬编码段落，添加了循环")
    print(f"删除范围: {para_start} - {last_para_end}")
    print(f"原始长度: {len(xml_content)}, 新长度: {len(new_content)}")

    return new_content

def main():
    base_dir = Path("/mnt/g/work/minhao/肠癌358基因")
    template_v8_fixed = base_dir / "templates" / "jinja2_template_358_v8_fixed_clean.docx"
    template_v9 = base_dir / "templates" / "jinja2_template_358_v9.docx"
    temp_dir = Path("/tmp/template_v9_work")

    print(f"输入模板: {template_v8_fixed}")
    print(f"输出模板: {template_v9}")

    # 解包
    print("\n1. 解包模板...")
    unpack_docx(str(template_v8_fixed), str(temp_dir))

    # 读取 document.xml
    doc_xml_path = temp_dir / "word" / "document.xml"
    with open(doc_xml_path, 'r', encoding='utf-8') as f:
        xml_content = f.read()

    original_len = len(xml_content)
    print(f"   原始XML长度: {original_len}")

    # 添加参考文献循环
    print("\n2. 添加参考文献循环...")
    xml_content = add_reference_loop(xml_content)

    # 保存修改
    print(f"\n3. 保存修改后的XML...")
    print(f"   新XML长度: {len(xml_content)} (差异: {len(xml_content) - original_len})")
    with open(doc_xml_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)

    # 打包
    print(f"\n4. 打包新模板...")
    pack_docx(str(temp_dir), str(template_v9))

    # 清理
    shutil.rmtree(temp_dir)

    print(f"\n完成！v9模板保存在: {template_v9}")
    print("\n包含的循环:")
    print("  1. variants 表格循环: {%tr for row in variants %}")
    print("  2. summary_variants 表格循环: {%tr for row in summary_variants %}")
    print("  3. undetected_genes 表格循环: {%tr for gene in undetected_genes %}")
    print("  4. references 段落循环: {%p for ref in references %}")

if __name__ == "__main__":
    main()
