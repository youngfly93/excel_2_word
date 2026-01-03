# Implementation Plan: Excel到Docx自动化报告生成系统

**Branch**: `001-excel-docx-automation` | **Date**: 2025-10-24 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/001-excel-docx-automation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

本项目旨在构建一个自动化医疗报告生成系统，从Excel基因检测结果表中提取数据，通过Jinja2模板引擎填充到docx模板，批量生成标准化的终版医疗报告。核心技术栈采用 **python-docx-template (docxtpl) + pandas**，支持单个/批量报告生成、多项目类型自动识别、灵活的字段映射配置。系统需满足医疗级别的数据完整性、可追溯性和性能要求（单报告<10秒，批量50个<5分钟）。

## Technical Context

**Language/Version**: Python 3.9+  
**Primary Dependencies**: 
- `python-docx-template (docxtpl)` - Jinja2风格的docx模板渲染引擎
- `pandas` - Excel数据读取和处理
- `openpyxl` - Excel (.xlsx) 文件读写引擎（pandas后端）
- `PyYAML` - 字段映射配置文件解析
- `python-dateutil` - 日期格式解析和统一化
- `click` - 命令行接口框架

**Storage**: 文件系统（Excel输入文件、Docx模板文件、生成的报告文件、日志文件）  
**Testing**: `pytest` + `pytest-cov` (覆盖率) + `pytest-mock` (模拟)  
**Target Platform**: Linux (主要) / Windows (兼容)  
**Project Type**: single - 命令行工具，单一代码库结构  
**Performance Goals**: 
- 单个报告生成 < 10秒
- Excel文件解析 < 5秒
- 批量处理50个样本 < 5分钟（平均6秒/报告）
- 内存占用 < 500MB/样本

**Constraints**: 
- 离线运行能力（无外部API依赖）
- 医疗数据隐私合规（本地处理，无数据上传）
- 文件大小支持：Excel < 100MB，最多10000行
- 模板兼容性：支持Word 2016+生成的docx

**Scale/Scope**: 
- 支持3种项目类型（301基因、358基因、肺癌甲基化）
- 预期处理量：日均50-200个样本报告
- 并发处理：最多50个样本同时处理
- 用户规模：5-10个医疗报告处理人员

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**依据宪章文件 `.specify/memory/constitution.md` 验证以下要求**:

### 代码质量检查点
- [x] 代码遵循项目编码规范 - 采用PEP 8 Python编码规范
- [x] 函数职责单一，文档完整 - 所有公共函数包含docstring
- [x] 复杂逻辑有充分注释 - 字段映射、数据清洗、模板渲染逻辑添加详细注释
- [x] 无硬编码，配置项外部化 - 字段映射、模板路径、项目类型识别规则均在YAML配置
- [x] 通过静态代码分析（linter） - 集成flake8 + pylint，CI中强制检查

### 测试覆盖检查点 (非协商项)
- [x] 已定义单元测试策略（TDD） - 核心模块先写测试用例
- [x] 核心业务逻辑测试覆盖率 ≥ 80% - 目标85%覆盖率
- [x] 包含集成测试计划 - 端到端测试：Excel输入 → Docx输出验证
- [x] 包含数据验证测试（已知样本） - 使用MLF2509307001T_MLB2509307001.result.xlsx作为基准测试
- [x] 使用脱敏测试数据 - 所有测试用例使用脱敏或虚拟患者数据

### 用户体验检查点
- [x] 界面和交互模式保持一致 - CLI命令统一格式，输出信息结构化
- [x] 错误信息清晰可操作 - 所有错误包含问题描述、原因、建议操作
- [x] 输入验证和反馈机制完善 - 启动时验证文件存在性，处理中显示进度
- [x] 提供操作文档 - quickstart.md + CLI --help详细说明

### 性能要求检查点
- [x] 定义明确的性能指标 - 见Technical Context性能目标
- [x] 文件解析 < 5秒/文件 - pandas优化读取，只加载必要sheet
- [x] 数据处理 < 30秒/样本 - Excel解析 + 数据清洗 + 模板渲染总计<10秒
- [x] 报告生成 < 10秒/报告 - docxtpl渲染性能优化
- [x] 包含性能基准测试计划 - pytest-benchmark测量关键函数性能

### 可观测性检查点
- [x] 关键操作记录结构化日志 - 使用Python logging，JSON格式日志
- [x] 实现操作审计和数据溯源 - 日志记录输入文件、模板版本、映射配置版本
- [x] 错误追踪包含完整上下文 - 异常捕获记录完整堆栈和输入数据摘要
- [x] 报告包含版本标识信息 - 在报告元数据或页脚添加软件版本、生成时间

**宪章合规性**: ✅ 所有检查点通过，无违规项需要申明

## Project Structure

### Documentation (this feature)

```text
specs/001-excel-docx-automation/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output - 技术选型和最佳实践研究
├── data-model.md        # Phase 1 output - 数据模型定义
├── quickstart.md        # Phase 1 output - 快速开始指南
├── contracts/           # Phase 1 output - CLI接口规范和配置文件schema
│   ├── cli-interface.md
│   ├── mapping-schema.yaml
│   └── config-schema.yaml
└── checklists/
    └── requirements.md  # 已生成 - 规范质量检查清单
```

### Source Code (repository root)

```text
reportgen/                          # 主包目录
├── __init__.py
├── __version__.py                  # 版本信息
├── cli.py                          # Click命令行入口
├── core/                           # 核心业务逻辑
│   ├── __init__.py
│   ├── excel_reader.py             # Excel数据提取
│   ├── field_mapper.py             # 字段映射引擎
│   ├── template_renderer.py        # Docx模板渲染
│   ├── data_cleaner.py             # 数据清洗和格式化
│   └── report_generator.py         # 报告生成协调器
├── models/                         # 数据模型
│   ├── __init__.py
│   ├── excel_data.py               # ExcelDataSource模型
│   ├── mapping.py                  # FieldMapping模型
│   ├── report_data.py              # ReportData模型
│   └── project_type.py             # 项目类型枚举和识别
├── utils/                          # 工具函数
│   ├── __init__.py
│   ├── logger.py                   # 结构化日志配置
│   ├── validators.py               # 数据验证器
│   └── file_utils.py               # 文件操作工具
└── config/                         # 配置管理
    ├── __init__.py
    └── loader.py                   # 配置加载器

tests/                              # 测试目录
├── __init__.py
├── conftest.py                     # pytest配置和fixtures
├── unit/                           # 单元测试
│   ├── test_excel_reader.py
│   ├── test_field_mapper.py
│   ├── test_template_renderer.py
│   ├── test_data_cleaner.py
│   └── test_validators.py
├── integration/                    # 集成测试
│   ├── test_end_to_end.py         # 完整流程测试
│   └── test_batch_processing.py   # 批量处理测试
└── fixtures/                       # 测试数据
    ├── sample_excel.xlsx           # 脱敏测试Excel
    ├── sample_template.docx        # 测试模板
    └── expected_output.docx        # 预期输出

data/                               # 数据目录（不提交到git）
├── input/                          # 输入Excel文件
├── output/                         # 生成的报告
└── logs/                           # 日志文件

templates/                          # Docx模板文件
├── crc_301_msi_template.docx      # 结直肠癌301基因+MSI模板
├── crc_358_msi_template.docx      # 结直肠癌358基因+MSI模板
└── lung_methylation_template.docx # 肺癌甲基化模板

config/                             # 配置文件
├── mapping.yaml                    # 字段映射配置
├── project_types.yaml              # 项目类型识别规则
└── settings.yaml                   # 全局设置

requirements.txt                    # Python依赖
requirements-dev.txt                # 开发依赖（pytest, flake8等）
setup.py                            # 包安装脚本
README.md                           # 项目说明
.gitignore                          # Git忽略规则
```

**Structure Decision**: 采用**单一项目结构**（Option 1），因为这是一个独立的命令行工具，不涉及前后端分离或移动端。核心逻辑放在`reportgen/`包中，按职责分为`core/`（业务逻辑）、`models/`（数据模型）、`utils/`（工具）、`config/`（配置）。测试目录`tests/`与源码分离，包含单元测试和集成测试。数据文件、模板文件、配置文件分别存放在独立目录便于管理。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

无违规项，本节留空。

---

**Phase 0 和 Phase 1 的详细设计文档将在以下文件中生成**：
- `research.md` - 技术选型研究和最佳实践
- `data-model.md` - 数据模型定义
- `contracts/` - CLI接口和配置schema
- `quickstart.md` - 快速开始指南
