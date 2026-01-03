#!/usr/bin/env python3
"""
创建简单的docx模板用于测试

该脚本创建一个包含基本占位符的模板文件。
"""

from docx import Document
from pathlib import Path

def create_simple_template():
    """创建简单的测试模板"""
    doc = Document()
    
    # 添加标题
    doc.add_heading('医疗检测报告', 0)
    
    # 添加患者信息
    doc.add_heading('患者信息', level=1)
    doc.add_paragraph('患者姓名: {{ patient_name }}')
    doc.add_paragraph('样本编号: {{ sample_id }}')
    doc.add_paragraph('性别: {{ gender }}')
    doc.add_paragraph('年龄: {{ age }}')
    doc.add_paragraph('送检医院: {{ hospital }}')
    doc.add_paragraph('报告日期: {{ report_date }}')
    
    # 添加项目信息
    doc.add_heading('检测项目', level=1)
    doc.add_paragraph('项目名称: {{ project_name }}')
    doc.add_paragraph('肿瘤类型: {{ cancer_type }}')
    doc.add_paragraph('检测方法: {{ detection_method }}')
    
    # 添加检测结果摘要
    doc.add_heading('检测结果摘要', level=1)
    doc.add_paragraph('MSI状态: {{ msi_status }}')
    doc.add_paragraph('TMB值: {{ tmb_value }} {{ tmb_unit }}')
    
    # 添加变异明细表格
    doc.add_heading('变异明细', level=1)
    doc.add_paragraph('检测到以下变异:')
    
    # 添加表格占位符（使用Jinja2循环语法）
    para = doc.add_paragraph('{% for variant in variants %}')
    para = doc.add_paragraph('- 基因: {{ variant.gene }}, 变异: {{ variant.variant }}, 频率: {{ variant.af }}%')
    para = doc.add_paragraph('{% endfor %}')
    
    # 添加签发信息
    doc.add_heading('签发信息', level=1)
    doc.add_paragraph('签发人: {{ issuer }}')
    doc.add_paragraph('审核人: {{ reviewer }}')
    
    # 保存模板
    template_path = Path('templates/test_template.docx')
    template_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(template_path))
    
    print(f"✅ 模板创建成功: {template_path}")
    return str(template_path)

if __name__ == '__main__':
    create_simple_template()


