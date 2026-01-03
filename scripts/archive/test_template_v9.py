#!/usr/bin/env python3
"""
测试模板v9的参考文献循环是否正常工作
"""

import sys
sys.path.insert(0, '/mnt/g/work/minhao/肠癌358基因')

from docxtpl import DocxTemplate
from pathlib import Path

def test_references_loop():
    """测试参考文献循环"""
    template_path = Path("/mnt/g/work/minhao/肠癌358基因/templates/jinja2_template_358_v9.docx")
    output_path = Path("/tmp/test_v9_output.docx")

    print(f"加载模板: {template_path}")

    try:
        doc = DocxTemplate(template_path)
        print("模板加载成功")
    except Exception as e:
        print(f"模板加载失败: {e}")
        return False

    # 准备测试数据
    context = {
        # 基本信息
        'patient_name': '测试患者',
        'report_number': 'TEST-001',
        'sample_date': '20251230',
        'report_date': '20251230',
        'gender': '男',
        'age': '50',
        'cancer_type': '测试癌症',
        'sample_id': 'TEST001',
        'sample_type': '组织',

        # TMB/MSI
        'tmb_value': '10.0',
        'tmb_status': 'TMB-L',
        'tmb_reference': '10',
        'msi_status_cn': '微卫星稳定型',

        # 免疫相关
        'immune_positive_count': '3',
        'immune_negative_result': '未检出',
        'immune_hyperprogression_result': '未检出',

        # 统计
        'total_variants_count': '8',
        'drug_related_count': '4',

        # 表格数据（空）
        'variants': [],
        'summary_variants': [],
        'undetected_genes': [],

        # 参考文献测试数据
        'references': [
            'PMID:12345678 Test reference 1 - This is a test reference.',
            'PMID:23456789 Test reference 2 - Another test reference.',
            'PMID:34567890 Test reference 3 - Yet another test reference.',
        ]
    }

    print(f"\n测试数据:")
    print(f"  - 参考文献数量: {len(context['references'])}")
    for ref in context['references']:
        print(f"    - {ref[:50]}...")

    try:
        print("\n渲染模板...")
        doc.render(context)
        print("渲染成功")
    except Exception as e:
        print(f"渲染失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    try:
        print(f"\n保存输出: {output_path}")
        doc.save(output_path)
        print("保存成功")
    except Exception as e:
        print(f"保存失败: {e}")
        return False

    # 验证输出
    print("\n验证输出...")
    import subprocess
    result = subprocess.run(
        ['pandoc', str(output_path), '-o', '/tmp/test_v9_output.md'],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        with open('/tmp/test_v9_output.md', 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查参考文献是否正确渲染
        ref_count = content.count('PMID:')
        print(f"  - 输出文档中包含 {ref_count} 个PMID参考文献")

        if ref_count == 3:
            print("  - 参考文献循环验证通过!")
            return True
        else:
            print(f"  - 警告: 期望3个参考文献，实际找到{ref_count}个")
            # 打印参考文献部分
            lines = content.split('\n')
            in_ref = False
            for line in lines:
                if '参考文献' in line:
                    in_ref = True
                if in_ref:
                    print(f"    {line}")
                    if 'PMID' not in line and line.strip() and in_ref:
                        break
            return False
    else:
        print(f"  - pandoc转换失败: {result.stderr}")
        return False


if __name__ == "__main__":
    success = test_references_loop()
    print(f"\n测试结果: {'通过' if success else '失败'}")
    sys.exit(0 if success else 1)
