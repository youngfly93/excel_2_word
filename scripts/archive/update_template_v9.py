#!/usr/bin/env python3
"""
更新模板 v8 -> v9
添加三个区域的Jinja2循环：
1. 基因诊疗知识章节 (gene_knowledge_sections)
2. 用药提示解析章节 (drug_analysis_sections)
3. 参考文献 (references)
"""

import os
import shutil
import zipfile
import re
from pathlib import Path
from xml.dom import minidom
import xml.etree.ElementTree as ET

# 注册命名空间
namespaces = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'w14': 'http://schemas.microsoft.com/office/word/2010/wordml',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
}

for prefix, uri in namespaces.items():
    ET.register_namespace(prefix, uri)


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


def update_references_section(xml_content: str) -> str:
    """
    更新参考文献部分：
    - 找到参考文献标题后的第一个参考文献段落
    - 将内容替换为Jinja2循环
    - 删除其他硬编码的参考文献段落
    """
    # 参考文献的特征：使用编号列表 numId="23"，内容包含"PMID:"

    # 策略：在第一个PMID段落中添加循环，删除后续的PMID段落

    # 找到所有PMID开头的段落位置
    pmid_pattern = r'<w:t[^>]*>PMID:\d+'
    pmid_matches = list(re.finditer(pmid_pattern, xml_content))

    if not pmid_matches:
        print("警告：未找到PMID参考文献")
        return xml_content

    print(f"找到 {len(pmid_matches)} 个PMID参考文献")

    # 找到第一个PMID所在的段落
    first_match = pmid_matches[0]
    first_pos = first_match.start()

    # 向前找到这个段落的开始
    para_start = xml_content.rfind('<w:p ', 0, first_pos)
    if para_start == -1:
        para_start = xml_content.rfind('<w:p>', 0, first_pos)

    # 找到这个段落的结束
    para_end = xml_content.find('</w:p>', first_pos) + len('</w:p>')

    # 提取第一个段落
    first_para = xml_content[para_start:para_end]
    print(f"第一个参考文献段落长度: {len(first_para)}")

    # 找到最后一个PMID段落的结束位置
    last_match = pmid_matches[-1]
    last_pos = last_match.start()
    last_para_end = xml_content.find('</w:p>', last_pos) + len('</w:p>')

    # 创建带循环的新段落
    # 需要将段落内容替换为循环变量
    # 使用 {%p for %} 语法进行段落级循环

    # 简化方案：直接替换文本内容
    # 创建新的段落结构
    new_para_template = '''<w:p w14:paraId="REF_LOOP">
      <w:pPr>
        <w:numPr>
          <w:ilvl w:val="0"/>
          <w:numId w:val="23"/>
        </w:numPr>
        <w:spacing w:after="0" w:line="312" w:lineRule="auto"/>
        <w:jc w:val="both"/>
        <w:rPr>
          <w:rFonts w:hint="eastAsia" w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="宋体" w:cs="Calibri"/>
          <w:sz w:val="21"/>
          <w:szCs w:val="21"/>
        </w:rPr>
      </w:pPr>
      <w:r>
        <w:rPr>
          <w:rFonts w:hint="eastAsia" w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="宋体" w:cs="Calibri"/>
          <w:sz w:val="21"/>
          <w:szCs w:val="21"/>
        </w:rPr>
        <w:t>{%p for ref in references %}{{ ref }}{%p endfor %}</w:t>
      </w:r>
    </w:p>'''

    # 替换所有PMID段落为单个循环段落
    # 但这样可能破坏格式，让我尝试另一种方法

    # 方法2：在第一个段落前添加循环开始标签，在最后一个段落后添加结束标签
    # 并将每个段落的内容替换为 {{ ref }}

    # 实际上，docxtpl的{%p for%}语法会重复整个段落
    # 所以我只需要保留一个段落，用循环包裹，删除其他段落

    # 创建循环段落 - 使用docxtpl的段落循环语法
    loop_para = first_para

    # 在段落内找到文本内容并替换
    # 匹配所有 <w:t>...</w:t> 内容
    text_pattern = r'(<w:t[^>]*>)(.*?)(</w:t>)'

    def replace_first_text(match):
        """只替换第一个文本为循环变量"""
        return match.group(1) + '{%p for ref in references %}{{ ref }}{%p endfor %}' + match.group(3)

    # 只替换第一个匹配
    loop_para = re.sub(text_pattern, replace_first_text, loop_para, count=1)

    # 删除段落中其他的<w:r>元素（如果有的话）
    # 简单起见，重新构建段落

    # docxtpl段落循环语法：
    # 1. {%p for ... %} 在独立段落中
    # 2. 内容 {{ ref }} 在带格式的段落中
    # 3. {%p endfor %} 在独立段落中

    # 开始循环标签段落
    loop_start = '''<w:p w14:paraId="REF_LOOP_START">
      <w:r>
        <w:t>{%p for ref in references %}</w:t>
      </w:r>
    </w:p>'''

    # 内容段落（保留编号格式）
    loop_content = '''<w:p w14:paraId="REF_LOOP_CONTENT">
      <w:pPr>
        <w:numPr>
          <w:ilvl w:val="0"/>
          <w:numId w:val="23"/>
        </w:numPr>
        <w:spacing w:after="0" w:line="312" w:lineRule="auto"/>
        <w:jc w:val="both"/>
        <w:rPr>
          <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="宋体" w:cs="Calibri"/>
          <w:sz w:val="21"/>
          <w:szCs w:val="21"/>
        </w:rPr>
      </w:pPr>
      <w:r>
        <w:rPr>
          <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="宋体" w:cs="Calibri"/>
          <w:sz w:val="21"/>
          <w:szCs w:val="21"/>
        </w:rPr>
        <w:t>{{ ref }}</w:t>
      </w:r>
    </w:p>'''

    # 结束循环标签段落
    loop_end = '''<w:p w14:paraId="REF_LOOP_END">
      <w:r>
        <w:t>{%p endfor %}</w:t>
      </w:r>
    </w:p>'''

    loop_para_clean = loop_start + loop_content + loop_end

    # 替换：从第一个PMID段落开始到最后一个PMID段落结束，替换为循环段落
    new_content = xml_content[:para_start] + loop_para_clean + xml_content[last_para_end:]

    print(f"参考文献部分已更新：删除了 {len(pmid_matches)} 个硬编码段落，添加了循环")

    return new_content


def update_gene_knowledge_section(xml_content: str) -> str:
    """
    更新基因诊疗知识章节：
    这部分比较复杂，包含多个子节（标题、简介、变异说明、变异解析）

    由于格式复杂，采用简化方案：
    - 在第一个基因章节前添加循环开始标记
    - 将硬编码内容替换为变量
    - 在最后一个基因章节后添加循环结束标记

    但这种方法对于复杂格式可能不可行。

    替代方案：使用占位符，在Python代码中生成完整内容
    """
    # 由于基因诊疗知识部分格式非常复杂（红色字体、下划线、多段落），
    # 直接在XML中添加循环风险较高。

    # 采用替代方案：添加一个简单的占位符段落
    # 数据层将生成完整的格式化文本

    # 查找 "基因变异解析" 标题
    gene_analysis_pattern = r'基因变异解析'

    # 这部分暂时跳过，后续使用RichText方案处理
    print("基因诊疗知识章节：由于格式复杂，建议使用RichText方案（暂时跳过XML修改）")

    return xml_content


def update_drug_analysis_section(xml_content: str) -> str:
    """
    更新用药提示解析章节
    同样由于格式复杂，暂时跳过
    """
    print("用药提示解析章节：由于格式复杂，建议使用RichText方案（暂时跳过XML修改）")
    return xml_content


def main():
    # 路径配置
    base_dir = Path("/mnt/g/work/minhao/肠癌358基因")
    template_v8 = base_dir / "templates" / "jinja2_template_358_v8.docx"
    template_v9 = base_dir / "templates" / "jinja2_template_358_v9.docx"
    temp_dir = Path("/tmp/template_v9_work")

    print(f"输入模板: {template_v8}")
    print(f"输出模板: {template_v9}")

    # 解包模板
    print("\n1. 解包模板...")
    unpack_docx(str(template_v8), str(temp_dir))

    # 读取document.xml
    doc_xml_path = temp_dir / "word" / "document.xml"
    print(f"\n2. 读取 {doc_xml_path}...")
    with open(doc_xml_path, 'r', encoding='utf-8') as f:
        xml_content = f.read()

    original_length = len(xml_content)
    print(f"   原始XML长度: {original_length}")

    # 更新参考文献部分
    print("\n3. 更新参考文献部分...")
    xml_content = update_references_section(xml_content)

    # 更新基因诊疗知识部分（暂时跳过）
    print("\n4. 更新基因诊疗知识部分...")
    xml_content = update_gene_knowledge_section(xml_content)

    # 更新用药提示解析部分（暂时跳过）
    print("\n5. 更新用药提示解析部分...")
    xml_content = update_drug_analysis_section(xml_content)

    # 保存修改后的document.xml
    print(f"\n6. 保存修改后的XML...")
    print(f"   新XML长度: {len(xml_content)} (差异: {len(xml_content) - original_length})")
    with open(doc_xml_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)

    # 打包新模板
    print(f"\n7. 打包新模板 -> {template_v9}...")
    pack_docx(str(temp_dir), str(template_v9))

    # 清理临时目录
    shutil.rmtree(temp_dir)

    print("\n完成！")
    print(f"新模板保存在: {template_v9}")
    print("\n注意事项:")
    print("1. 参考文献部分已添加循环: {%p for ref in references %}{{ ref }}{%p endfor %}")
    print("2. 基因诊疗知识和用药提示解析部分暂时保持原状，建议使用RichText方案")


if __name__ == "__main__":
    main()
