"""
CLI命令行接口

提供reportgen命令行工具。
"""

import click
import sys
from pathlib import Path
from reportgen import __version__
from reportgen.core.report_generator import ReportGenerator
from reportgen.utils.logger import get_logger


@click.group()
@click.version_option(version=__version__)
@click.option(
    "--config-dir",
    default="config",
    help="配置文件目录路径",
    show_default=True,
)
@click.option(
    "--log-file",
    default=None,
    help="日志文件路径（可选）",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="显示详细日志",
)
@click.pass_context
def cli(ctx, config_dir, log_file, verbose):
    """
    Excel到Docx自动化报告生成系统

    从Excel基因检测结果表生成标准化的docx医疗报告。
    """
    # 初始化上下文
    ctx.ensure_object(dict)
    ctx.obj["config_dir"] = config_dir
    ctx.obj["log_file"] = log_file
    ctx.obj["verbose"] = verbose

    # 设置日志级别
    log_level = "DEBUG" if verbose else "INFO"
    ctx.obj["log_level"] = log_level


@cli.command()
@click.option(
    "--excel",
    "-e",
    required=True,
    type=click.Path(exists=True),
    help="Excel结果文件路径",
)
@click.option(
    "--template",
    "-t",
    required=False,
    default="templates/jinja2_template_358_v17.docx",
    type=click.Path(exists=True),
    help="Docx模板文件路径（默认: templates/jinja2_template_358_v17.docx）",
)
@click.option(
    "--output",
    "-o",
    required=False,
    default="data/output",
    type=click.Path(),
    help="输出目录路径（默认: data/output）",
)
@click.option(
    "--filename",
    "-f",
    default=None,
    help="输出文件名（可选，默认自动生成）",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="严格模式：缺失关键字段时阻断生成（默认：只警告不阻断）",
)
@click.option(
    "--auto-detect",
    is_flag=True,
    default=False,
    help="自动检测项目类型并选择模板",
)
@click.pass_context
def generate(ctx, excel, template, output, filename, strict, auto_detect):
    """
    生成单个报告

    示例:

        # 最简用法（使用默认模板和输出目录）
        reportgen generate -e data/input/sample.xlsx

        # 指定模板和输出目录
        reportgen generate -e data/input/sample.xlsx -t templates/template.docx -o output/

        # 自动检测项目类型
        reportgen generate -e data/input/sample.xlsx --auto-detect
    """
    config_dir = ctx.obj["config_dir"]
    log_file = ctx.obj["log_file"]
    verbose = ctx.obj["verbose"]

    # 初始化日志
    logger = get_logger(log_file=log_file, level=ctx.obj["log_level"])

    # 自动检测项目类型
    prefetched_excel_data = None
    if auto_detect:
        from reportgen.core.project_detector import ProjectDetector
        from reportgen.core.excel_reader import ExcelReader

        click.echo(f"📊 Excel到Docx报告生成系统 v{__version__}")
        click.echo(f"📂 Excel文件: {excel}")
        click.echo("🔍 正在自动检测项目类型...")

        detector = ProjectDetector(
            config_dir=config_dir, log_file=log_file, log_level=ctx.obj["log_level"]
        )

        # 预读Excel（一次性读取，后续生成阶段复用，避免重复IO）
        excel_reader = ExcelReader(
            config_dir=config_dir, log_file=log_file, log_level=ctx.obj["log_level"]
        )
        try:
            prefetched_excel_data = excel_reader.read(excel, include_tables=True)
        except Exception as e:
            logger.warning("自动检测阶段读取Excel失败，回退为仅文件名识别", error=str(e))
            prefetched_excel_data = None

        detection_result = detector.detect(excel, excel_data=prefetched_excel_data)

        if detection_result["detected"]:
            detected_template = detection_result["template"]
            click.echo(f"✅ 检测到项目类型: {detection_result['project_name']}")
            click.echo(f"   置信度: {detection_result['confidence']:.0%}")

            if template:
                click.echo(f"📄 使用指定模板: {template}")
            elif detected_template and Path(detected_template).exists():
                template = detected_template
                click.echo(f"📄 使用推荐模板: {template}")
            else:
                click.echo("⚠️  推荐模板不存在，请手动指定模板", err=True)
                sys.exit(1)
        else:
            click.echo("⚠️  无法自动检测项目类型", err=True)
            if not template:
                click.echo("请使用 -t 参数指定模板文件", err=True)
                sys.exit(1)
            click.echo(f"📄 使用指定模板: {template}")

        click.echo(f"📁 输出目录: {output}")
        click.echo("")
    else:
        # 非自动检测模式，使用指定模板或默认模板
        click.echo(f"📊 Excel到Docx报告生成系统 v{__version__}")
        click.echo(f"📂 Excel文件: {excel}")
        click.echo(f"📄 模板文件: {template}")
        click.echo(f"📁 输出目录: {output}")
        click.echo("")

    try:
        # 初始化生成器
        generator = ReportGenerator(
            config_dir=config_dir,
            log_file=log_file,
            log_level=ctx.obj["log_level"],
        )

        # 验证输入
        if verbose:
            click.echo("🔍 验证输入参数...")

        is_valid, errors = generator.validate_inputs(excel, template, output)
        if not is_valid:
            click.echo("❌ 输入验证失败:", err=True)
            for error in errors:
                click.echo(f"   - {error}", err=True)
            sys.exit(1)

        # 生成报告
        if strict:
            click.echo("⚙️  正在生成报告（严格模式）...")
        else:
            click.echo("⚙️  正在生成报告...")

        result = generator.generate(
            excel_file=excel,
            template_file=template,
            output_dir=output,
            output_filename=filename,
            strict_mode=strict,
            excel_data=prefetched_excel_data,
        )

        if result["success"]:
            click.echo("✅ 报告生成成功!")
            click.echo(f"📄 输出文件: {result['output_file']}")
            click.echo(f"⏱️  耗时: {result['duration']:.2f}秒")

            # 显示警告
            if result["warnings"]:
                click.echo(f"\n⚠️  警告 ({len(result['warnings'])}个):")
                for warning in result["warnings"]:
                    click.echo(f"   - {warning}")

            sys.exit(0)
        else:
            click.echo("❌ 报告生成失败!", err=True)
            click.echo(f"⏱️  耗时: {result['duration']:.2f}秒", err=True)

            if result["errors"]:
                click.echo("\n错误详情:", err=True)
                for error in result["errors"]:
                    click.echo(f"   - {error}", err=True)

            sys.exit(1)

    except Exception as e:
        logger.error("命令执行失败", command="generate", error=str(e))
        click.echo(f"❌ 执行失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--template",
    "-t",
    required=True,
    type=click.Path(exists=True),
    help="Docx模板文件路径",
)
@click.option(
    "--show-vars",
    is_flag=True,
    default=False,
    help="显示模板中的所有变量",
)
@click.option(
    "--check-mapping",
    is_flag=True,
    default=False,
    help="校验模板变量是否与mapping配置匹配",
)
@click.pass_context
def validate(ctx, template, show_vars, check_mapping):
    """
    验证模板文件

    示例:

        reportgen validate -t templates/template.docx

        reportgen validate -t templates/template.docx --show-vars

        reportgen validate -t templates/template.docx --check-mapping
    """
    from reportgen.core.template_renderer import TemplateRenderer
    from reportgen.config.loader import ConfigLoader

    log_file = ctx.obj["log_file"]
    config_dir = ctx.obj["config_dir"]

    click.echo(f"🔍 验证模板文件: {template}")

    try:
        renderer = TemplateRenderer(log_file=log_file, log_level=ctx.obj["log_level"])
        is_valid, error = renderer.validate_template(template)

        if not is_valid:
            click.echo(f"❌ 模板文件无效: {error}", err=True)
            sys.exit(1)

        click.echo("✅ 模板文件格式有效")

        # 显示变量
        if show_vars or check_mapping:
            vars_list = renderer.get_template_variables(template)
            single_vars = [v for v in vars_list if not v.startswith('row')]
            row_vars = [v for v in vars_list if v.startswith('row')]

            if show_vars:
                click.echo(f"\n📋 模板变量统计:")
                click.echo(f"   单值变量: {len(single_vars)}个")
                click.echo(f"   循环变量: {len(row_vars)}个")

                click.echo(f"\n📌 单值变量列表:")
                for v in sorted(single_vars):
                    click.echo(f"   - {v}")

                click.echo(f"\n🔄 循环变量列表:")
                for v in sorted(row_vars):
                    click.echo(f"   - {v}")

        # 校验mapping
        if check_mapping:
            config_loader = ConfigLoader(
                config_dir=config_dir, log_file=log_file, log_level=ctx.obj["log_level"]
            )
            mapping_config = config_loader.load_mapping_config()

            # 获取mapping中定义的变量
            available_vars = list(mapping_config.get("single_values", {}).keys())
            available_vars.extend(list(mapping_config.get("table_data", {}).keys()))

            available_row_keys = set()
            for _, table_cfg in mapping_config.get("table_data", {}).items():
                cols = (table_cfg or {}).get("columns", {})
                for col_var, col_cfg in (cols or {}).items():
                    available_row_keys.add(str(col_var))
                    for syn in (col_cfg or {}).get("synonyms", []) or []:
                        available_row_keys.add(str(syn))

            _, missing_vars, unused_vars = renderer.validate_template_variables(
                template, available_vars, available_row_keys=available_row_keys
            )

            click.echo(f"\n🔗 Mapping配置校验:")
            if missing_vars:
                click.echo(f"   ⚠️  模板中有 {len(missing_vars)} 个变量在mapping中未定义:")
                for v in missing_vars[:10]:
                    click.echo(f"      - {v}")
                if len(missing_vars) > 10:
                    click.echo(f"      ... 还有 {len(missing_vars) - 10} 个")
            else:
                click.echo("   ✅ 所有模板变量都有对应的mapping定义")

            if unused_vars:
                click.echo(f"   ℹ️  mapping中有 {len(unused_vars)} 个变量在模板中未使用")

        sys.exit(0)

    except Exception as e:
        click.echo(f"❌ 验证失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--template",
    "-t",
    required=True,
    type=click.Path(exists=True),
    help="Docx模板文件路径",
)
@click.option(
    "--output",
    "-o",
    default=None,
    type=click.Path(),
    help="输出文件路径（默认: 模板名_highlighted.docx）",
)
@click.option(
    "--list",
    "list_only",
    is_flag=True,
    default=False,
    help="仅列出所有Jinja2变量，不生成高亮文件",
)
@click.pass_context
def highlight(ctx, template, output, list_only):
    """
    高亮模板中的Jinja2变量区域

    为模板中的Jinja2表达式添加颜色高亮：
    - {{ 变量 }} → 黄色高亮
    - {% 控制结构 %} → 青色高亮

    示例:

        # 生成高亮版本
        reportgen highlight -t templates/jinja2_template_358_v9.docx

        # 仅列出变量
        reportgen highlight -t templates/jinja2_template_358_v9.docx --list

        # 指定输出路径
        reportgen highlight -t templates/template.docx -o output/highlighted.docx
    """
    # 导入高亮工具
    try:
        from tools.highlight_jinja2_vars import (
            highlight_jinja2_variables,
            list_jinja2_variables,
        )
    except ImportError:
        # 如果tools不在路径中，尝试从当前目录导入
        sys.path.insert(0, str(Path.cwd()))
        from tools.highlight_jinja2_vars import (
            highlight_jinja2_variables,
            list_jinja2_variables,
        )

    click.echo(f"📄 模板文件: {template}")

    try:
        if list_only:
            click.echo("\n🔍 扫描Jinja2表达式...\n")
            variables, controls = list_jinja2_variables(template)
            click.echo(f"\n📊 总计: {len(variables)} 个变量, {len(controls)} 个控制结构")
        else:
            click.echo("🎨 正在生成高亮版本...")
            output_file = highlight_jinja2_variables(template, output)
            click.echo(f"\n✅ 高亮版本已生成!")
            click.echo(f"📁 输出文件: {output_file}")

        sys.exit(0)

    except Exception as e:
        click.echo(f"❌ 处理失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def init(ctx):
    """
    初始化项目结构

    创建必要的目录和示例配置文件。
    """
    click.echo("🚀 初始化项目结构...")

    directories = [
        "config",
        "templates",
        "data/input",
        "data/output",
        "data/logs",
    ]

    try:
        for directory in directories:
            path = Path(directory)
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                click.echo(f"✅ 创建目录: {directory}")
            else:
                click.echo(f"⏭️  目录已存在: {directory}")

        click.echo("\n✅ 项目初始化完成!")
        click.echo("\n下一步:")
        click.echo("1. 将Excel文件放入 data/input/ 目录")
        click.echo("2. 将Docx模板放入 templates/ 目录")
        click.echo("3. 运行: reportgen generate \\")
        click.echo("   -e data/input/your_file.xlsx \\")
        click.echo("   -t templates/your_template.docx \\")
        click.echo("   -o data/output/")

        sys.exit(0)

    except Exception as e:
        click.echo(f"❌ 初始化失败: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
