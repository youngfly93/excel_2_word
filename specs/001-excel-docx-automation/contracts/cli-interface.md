# CLI Interface Contract

**Feature**: 001-excel-docx-automation  
**Version**: 1.0.0  
**Date**: 2025-10-24

## Overview

本文档定义`reportgen`命令行工具的完整接口规范，包括所有命令、参数、选项和输出格式。

## Installation & Setup

```bash
# 安装
pip install reportgen

# 验证安装
reportgen --version
# 输出: reportgen version 1.0.0

# 查看帮助
reportgen --help
```

## Commands

### 1. `reportgen generate` - 生成单个报告

**用途**: 从Excel文件生成单个患者的医疗报告

**语法**:
```bash
reportgen generate --excel <PATH> [OPTIONS]
```

**必需参数**:
- `--excel <PATH>`, `-e <PATH>`: 输入Excel文件路径

**可选参数**:
- `--output <DIR>`, `-o <DIR>`: 输出目录（默认：`./output/`）
- `--template <PATH>`, `-t <PATH>`: 指定模板文件路径（默认：自动识别）
- `--mapping <PATH>`, `-m <PATH>`: 字段映射配置文件（默认：`config/mapping.yaml`）
- `--config <PATH>`, `-c <PATH>`: 全局配置文件（默认：`config/settings.yaml`）
- `--sample-id <ID>`, `-s <ID>`: 指定样本编号（当Excel包含多个样本时）
- `--log <PATH>`, `-l <PATH>`: 日志文件路径（默认：`logs/reportgen_{timestamp}.log`）
- `--verbose`, `-v`: 详细输出模式
- `--quiet`, `-q`: 静默模式（仅输出错误）
- `--dry-run`: 试运行模式（验证但不生成文件）

**示例**:
```bash
# 基本用法
reportgen generate --excel data/input/sample.xlsx

# 指定输出目录
reportgen generate --excel data/input/sample.xlsx --output reports/2025-10/

# 使用自定义模板和映射
reportgen generate \
  --excel data/input/sample.xlsx \
  --template templates/custom_template.docx \
  --mapping config/custom_mapping.yaml

# 试运行验证
reportgen generate --excel data/input/sample.xlsx --dry-run

# 详细输出
reportgen generate --excel data/input/sample.xlsx --verbose
```

**输出**:
```
[INFO] 加载Excel文件: data/input/sample.xlsx
[INFO] 文件大小: 2.3 MB
[INFO] 检测到项目类型: 结直肠癌301基因+MSI
[INFO] 选择模板: templates/crc_301_msi_template.docx
[INFO] 提取患者信息: 张三 (TEST-2025-0001)
[INFO] 提取变异明细: 5条记录
[INFO] 提取MSI指标: MSI-H
[INFO] 渲染模板...
[INFO] 生成报告: output/张三_TEST-2025-0001_结直肠癌301基因+msi_2025-10-24_终版.docx
[SUCCESS] 报告生成成功，耗时: 8.2秒
```

**退出码**:
- `0`: 成功
- `1`: 一般错误（文件不存在、格式错误等）
- `2`: 验证错误（缺失必填字段）
- `3`: 渲染错误（模板问题）

---

### 2. `reportgen batch` - 批量生成报告

**用途**: 从单个Excel文件或多个Excel文件批量生成报告

**语法**:
```bash
reportgen batch --excel <PATTERN> [OPTIONS]
```

**必需参数**:
- `--excel <PATTERN>`, `-e <PATTERN>`: Excel文件路径或glob模式

**可选参数**:
- `--output <DIR>`, `-o <DIR>`: 输出目录（默认：`./output/`）
- `--mapping <PATH>`, `-m <PATH>`: 字段映射配置文件
- `--config <PATH>`, `-c <PATH>`: 全局配置文件
- `--max-workers <N>`: 最大并发数（默认：4）
- `--continue-on-error`: 遇到错误继续处理其他样本
- `--log <PATH>`, `-l <PATH>`: 日志文件路径
- `--summary <PATH>`: 生成汇总报告文件路径
- `--verbose`, `-v`: 详细输出模式
- `--quiet`, `-q`: 静默模式

**示例**:
```bash
# 批量处理单个Excel中的多个样本
reportgen batch --excel data/input/batch_001.xlsx

# 批量处理多个Excel文件（使用glob）
reportgen batch --excel "data/input/*.xlsx"

# 并发处理，遇到错误继续
reportgen batch \
  --excel "data/input/*.xlsx" \
  --max-workers 8 \
  --continue-on-error \
  --summary data/output/summary_2025-10-24.json

# 静默模式，只生成汇总
reportgen batch \
  --excel "data/input/*.xlsx" \
  --quiet \
  --summary summary.json
```

**输出**:
```
[INFO] 开始批量处理...
[INFO] 找到2个Excel文件，共50个样本
[PROGRESS] [████████████████████░░░░] 80% (40/50) - 预计剩余: 1分钟
[INFO] 处理完成
[SUCCESS] 成功: 48个，失败: 2个，总耗时: 4分38秒
[INFO] 汇总报告已保存: summary.json
```

**汇总报告格式** (`summary.json`):
```json
{
  "timestamp": "2025-10-24T15:30:00",
  "total_samples": 50,
  "success_count": 48,
  "failed_count": 2,
  "duration_seconds": 278,
  "average_time_per_sample": 5.56,
  "success_files": [
    "output/张三_TEST-001_结直肠癌301基因+msi_2025-10-24_终版.docx",
    "..."
  ],
  "failed_samples": [
    {
      "sample_id": "TEST-045",
      "error": "缺失必填字段: patient_name"
    },
    {
      "sample_id": "TEST-023",
      "error": "Excel文件损坏，无法读取sheet: 变异明细"
    }
  ],
  "missing_fields_summary": {
    "hospital": 5,
    "pathology_id": 3
  }
}
```

---

### 3. `reportgen validate` - 验证配置和模板

**用途**: 验证配置文件、模板文件和Excel数据的完整性

**语法**:
```bash
reportgen validate [RESOURCE] [OPTIONS]
```

**资源类型**:
- `config`: 验证配置文件
- `template`: 验证模板文件
- `excel`: 验证Excel数据文件
- `all`: 验证所有（默认）

**可选参数**:
- `--mapping <PATH>`: 映射配置文件路径
- `--config <PATH>`: 全局配置文件路径
- `--template <PATH>`: 模板文件路径
- `--excel <PATH>`: Excel文件路径
- `--strict`: 严格模式（警告也视为错误）

**示例**:
```bash
# 验证所有配置
reportgen validate

# 仅验证映射配置
reportgen validate config --mapping config/mapping.yaml

# 验证模板
reportgen validate template --template templates/crc_301_msi_template.docx

# 验证Excel数据
reportgen validate excel --excel data/input/sample.xlsx --mapping config/mapping.yaml

# 严格模式
reportgen validate all --strict
```

**输出**:
```
[INFO] 验证映射配置: config/mapping.yaml
  ✓ YAML格式正确
  ✓ 包含57个字段映射
  ✓ 必填字段完整: patient_name, sample_id, report_date
  ⚠ 建议: 字段"tmb_score"未定义默认值

[INFO] 验证模板: templates/crc_301_msi_template.docx
  ✓ 文件可正常打开
  ✓ 提取占位符: 42个
  ✓ 循环块: 3个（variants, fusions, cnvs）
  ✓ 条件块: 2个（msi, methylation）

[INFO] 验证Excel数据: data/input/sample.xlsx
  ✓ 文件格式正确
  ✓ 包含sheet: 基本信息, 变异明细, MSI, 质控
  ✓ 必填字段存在: patient_name, sample_id
  ⚠ 非必填字段缺失: hospital, pathology_id

[SUMMARY] 验证完成: 12个检查通过, 3个警告, 0个错误
```

---

### 4. `reportgen init` - 初始化项目

**用途**: 创建配置文件和目录结构

**语法**:
```bash
reportgen init [OPTIONS]
```

**可选参数**:
- `--project-dir <DIR>`: 项目目录（默认：当前目录）
- `--extract-template <DOCX>`: 从已有报告提取模板
- `--sample-excel <PATH>`: 使用示例Excel生成默认映射

**示例**:
```bash
# 在当前目录初始化
reportgen init

# 指定项目目录
reportgen init --project-dir /path/to/project

# 从已有报告提取模板并生成映射
reportgen init \
  --extract-template 参考报告.docx \
  --sample-excel MLF2509307001T_MLB2509307001.result.xlsx
```

**生成的目录结构**:
```
project/
├── config/
│   ├── mapping.yaml          # 字段映射配置
│   ├── project_types.yaml    # 项目类型识别规则
│   └── settings.yaml         # 全局设置
├── templates/
│   └── template.docx         # 模板文件（如提供）
├── data/
│   ├── input/                # 输入Excel目录
│   ├── output/               # 输出报告目录
│   └── logs/                 # 日志目录
└── README.md                 # 快速开始说明
```

---

### 5. `reportgen template` - 模板管理

**用途**: 管理模板文件（列表、添加、验证）

**子命令**:
- `list`: 列出所有模板
- `add`: 添加新模板
- `extract`: 从已有报告提取模板
- `verify`: 验证模板完整性

**示例**:
```bash
# 列出所有模板
reportgen template list

# 添加新模板
reportgen template add \
  --file templates/new_template.docx \
  --id lung_methylation \
  --name "肺癌甲基化" \
  --keywords "肺癌,甲基化"

# 从已有报告提取模板
reportgen template extract \
  --source 参考报告.docx \
  --output templates/extracted_template.docx

# 验证模板
reportgen template verify --file templates/crc_301_msi_template.docx
```

---

### 6. 全局选项

适用于所有命令的全局选项：

- `--version`: 显示版本信息
- `--help`, `-h`: 显示帮助信息
- `--config-dir <DIR>`: 配置文件目录（默认：`./config/`）
- `--no-color`: 禁用彩色输出
- `--debug`: 开启调试模式

**示例**:
```bash
# 显示版本
reportgen --version

# 查看命令帮助
reportgen generate --help

# 使用自定义配置目录
reportgen generate --excel data.xlsx --config-dir /etc/reportgen/
```

---

## Error Handling

### 错误消息格式

```
[ERROR] <错误类型>: <错误描述>
原因: <具体原因>
建议: <操作建议>

详细信息: <详细堆栈或上下文>
```

### 常见错误

| 错误代码 | 错误类型 | 示例消息 | 建议操作 |
|---------|---------|---------|---------|
| E001 | 文件不存在 | "Excel文件不存在: /path/to/file.xlsx" | 检查文件路径是否正确 |
| E002 | 文件格式错误 | "不支持的文件格式，仅支持.xlsx" | 使用Excel 2007+格式 |
| E003 | 必填字段缺失 | "缺失必填字段: patient_name" | 检查Excel数据完整性 |
| E004 | 模板错误 | "模板文件损坏，无法打开" | 检查模板文件或重新下载 |
| E005 | 渲染错误 | "变量未定义: {{ unknown_var }}" | 检查映射配置或模板占位符 |
| E006 | 权限不足 | "无法写入输出目录: /path/" | 检查目录权限 |
| E007 | 磁盘空间不足 | "磁盘空间不足，无法保存文件" | 清理磁盘空间 |
| E008 | 配置错误 | "mapping.yaml格式错误: line 15" | 检查YAML语法 |

---

## Environment Variables

可通过环境变量配置默认行为：

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `REPORTGEN_CONFIG_DIR` | 配置文件目录 | `./config/` |
| `REPORTGEN_TEMPLATE_DIR` | 模板文件目录 | `./templates/` |
| `REPORTGEN_OUTPUT_DIR` | 默认输出目录 | `./output/` |
| `REPORTGEN_LOG_LEVEL` | 日志级别 | `INFO` |
| `REPORTGEN_LOG_FORMAT` | 日志格式 | `json` / `text` |

**示例**:
```bash
export REPORTGEN_CONFIG_DIR=/etc/reportgen/config
export REPORTGEN_LOG_LEVEL=DEBUG

reportgen generate --excel data.xlsx
```

---

## Progress Reporting

批量处理时的进度显示格式：

```
[PROGRESS] [████████████████████░░░░] 80% (40/50)
  成功: 38  失败: 2  当前: 正在处理 TEST-040
  已用时间: 3分20秒  预计剩余: 50秒
  平均速度: 12.0样本/分钟
```

---

## Configuration Files

CLI工具依赖以下配置文件：

1. `config/mapping.yaml` - 字段映射配置（必需）
2. `config/project_types.yaml` - 项目类型识别规则（必需）
3. `config/settings.yaml` - 全局设置（可选，有默认值）

详细配置格式见 `mapping-schema.yaml` 和 `config-schema.yaml`。

---

## Logging

### 日志级别

- `DEBUG`: 详细调试信息
- `INFO`: 一般信息（默认）
- `WARNING`: 警告信息
- `ERROR`: 错误信息
- `CRITICAL`: 严重错误

### 日志格式

**JSON格式** (默认，用于机器读取):
```json
{
  "timestamp": "2025-10-24T15:30:25.123456",
  "level": "INFO",
  "event": "report_generated",
  "sample_id": "TEST-001",
  "duration": 8.2,
  "status": "success"
}
```

**文本格式** (用于人类阅读):
```
2025-10-24 15:30:25 [INFO] report_generated: TEST-001 (8.2s) - success
```

---

## Return Codes

| 退出码 | 含义 | 说明 |
|-------|------|------|
| 0 | 成功 | 所有操作成功完成 |
| 1 | 一般错误 | 文件不存在、格式错误等 |
| 2 | 验证错误 | 数据验证失败（缺失必填字段等） |
| 3 | 渲染错误 | 模板渲染失败 |
| 4 | 配置错误 | 配置文件格式错误或缺失 |
| 5 | 权限错误 | 文件权限不足 |
| 6 | 系统错误 | 磁盘空间不足等系统级错误 |
| 128+N | 信号中断 | 被信号N中断（如Ctrl+C） |

---

## Version History

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| 1.0.0 | 2025-10-24 | 初始版本，定义核心CLI接口 |

---

## Next Steps

- 实现CLI框架（使用Click）
- 实现每个命令的处理逻辑
- 添加完整的单元测试覆盖
- 编写用户文档和示例

