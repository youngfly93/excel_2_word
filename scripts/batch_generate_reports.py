#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量生成报告脚本

用法:
    python scripts/batch_generate_reports.py
    python scripts/batch_generate_reports.py data/input
    python scripts/batch_generate_reports.py data/input data/output
    python scripts/batch_generate_reports.py data/input data/output templates/jinja2_template_358_v9.docx
    python scripts/batch_generate_reports.py data/input data/output --auto-detect
"""

import argparse
import glob
import os
from pathlib import Path


DEFAULT_TEMPLATE_FILE = "templates/jinja2_template_358_v9.docx"


def batch_generate_reports(
    input_dir: str = "data/input",
    output_dir: str = "data/output",
    template_file: str = DEFAULT_TEMPLATE_FILE,
    *,
    strict_mode: bool = False,
    auto_detect: bool = False,
):
    """批量生成报告（与CLI/ReportGenerator保持同一管道与口径）。"""

    from reportgen.core.project_detector import ProjectDetector
    from reportgen.core.report_generator import ReportGenerator

    print("=" * 80)
    print("📊 批量生成Excel到Docx报告")
    print("=" * 80)

    # 查找所有Excel文件
    excel_pattern = os.path.join(input_dir, "*.xlsx")
    excel_files = glob.glob(excel_pattern)

    # 过滤掉临时文件
    excel_files = [f for f in excel_files if not os.path.basename(f).startswith('~$')]

    if not excel_files:
        print(f"\n❌ 在 {input_dir} 目录中未找到Excel文件")
        return

    print(f"\n📂 输入目录: {input_dir}")
    print(f"📁 输出目录: {output_dir}")
    if auto_detect:
        print("📄 模板选择: 自动检测项目类型（可通过第3个参数强制指定模板）")
    else:
        print(f"📄 使用模板: {template_file}")
    print(f"\n找到 {len(excel_files)} 个Excel文件:")
    for i, f in enumerate(excel_files, 1):
        print(f"  {i}. {os.path.basename(f)}")

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 统计信息
    success_count = 0
    failed_count = 0
    failed_files = []

    # 初始化组件（复用）
    generator = ReportGenerator(config_dir="config")
    detector = (
        ProjectDetector(config_dir="config", log_level="INFO") if auto_detect else None
    )

    print("\n" + "=" * 80)
    print("开始批量处理...")
    print("=" * 80)

    # 处理每个文件
    for idx, excel_file in enumerate(excel_files, 1):
        filename = os.path.basename(excel_file)
        print(f"\n[{idx}/{len(excel_files)}] 处理: {filename}")
        print("-" * 80)

        try:
            template_to_use = template_file
            prefetched_excel_data = None

            # 自动检测项目类型并选模板（复用预读Excel，减少IO）
            if detector is not None:
                try:
                    prefetched_excel_data = generator.excel_reader.read(
                        excel_file, include_tables=True
                    )
                except Exception:
                    prefetched_excel_data = None

                detection_result = detector.detect(
                    excel_file, excel_data=prefetched_excel_data
                )
                detected_template = detection_result.get("template")
                if detected_template and Path(detected_template).exists():
                    template_to_use = detected_template

            result = generator.generate(
                excel_file=excel_file,
                template_file=template_to_use,
                output_dir=output_dir,
                strict_mode=strict_mode,
                excel_data=prefetched_excel_data,
            )

            if result.get("success"):
                output_file = result.get("output_file") or ""
                file_size = os.path.getsize(output_file) if output_file and os.path.exists(output_file) else 0
                print(
                    f"  ✅ 报告生成成功: {Path(output_file).name} ({file_size / 1024:.1f} KB)"
                )
                success_count += 1
            else:
                err = "; ".join(result.get("errors") or []) or "生成失败"
                print(f"  ❌ 处理失败: {err[:200]}")
                failed_count += 1
                failed_files.append((filename, err[:200]))

        except Exception as e:
            print(f"  ❌ 处理失败: {str(e)[:100]}")
            failed_count += 1
            failed_files.append((filename, str(e)[:100]))

    # 打印汇总
    print("\n" + "=" * 80)
    print("批量处理完成")
    print("=" * 80)
    print(f"\n📊 处理统计:")
    print(f"  总文件数: {len(excel_files)}")
    print(f"  ✅ 成功: {success_count}")
    print(f"  ❌ 失败: {failed_count}")

    if failed_files:
        print(f"\n❌ 失败文件列表:")
        for filename, error in failed_files:
            print(f"  - {filename}")
            print(f"    错误: {error}")

    print("\n" + "=" * 80)

    return success_count, failed_count


def main():
    """主函数"""
    ap = argparse.ArgumentParser(description="批量生成Excel到Docx报告")
    ap.add_argument("input_dir", nargs="?", default="data/input", help="Excel输入目录")
    ap.add_argument("output_dir", nargs="?", default="data/output", help="报告输出目录")
    ap.add_argument(
        "template_file",
        nargs="?",
        default=None,
        help=f"模板文件路径（可选，默认: {DEFAULT_TEMPLATE_FILE}）",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="严格模式：缺失关键字段时阻断生成（默认：只警告不阻断）",
    )
    ap.add_argument(
        "--auto-detect",
        action="store_true",
        help="自动检测项目类型并选择模板（若显式传入template_file，则以传入为准）",
    )
    args = ap.parse_args()

    template_file = args.template_file or DEFAULT_TEMPLATE_FILE

    success, failed = batch_generate_reports(
        args.input_dir,
        args.output_dir,
        template_file,
        strict_mode=args.strict,
        auto_detect=args.auto_detect and (args.template_file is None),
    )

    raise SystemExit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
