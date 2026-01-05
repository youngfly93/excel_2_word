# Excel到Docx自动化报告生成系统

**版本**: 1.0.0  
**状态**: 开发中

## 概述

自动化医疗报告生成系统，从Excel基因检测结果表中提取数据，通过Jinja2模板引擎填充到docx模板，批量生成标准化的终版医疗报告。

## 核心功能

- ✅ **单个报告生成**: 从Excel读取患者数据，生成标准化docx报告
- ✅ **批量处理**: 一次处理多个样本，生成汇总统计
- ✅ **项目类型自动识别**: 自动识别301基因、358基因、肺癌甲基化等类型
- ✅ **灵活配置**: 支持字段映射同义词，无需代码修改

## 技术栈

- **Python**: 3.9+
- **核心库**: python-docx-template (docxtpl), pandas, openpyxl
- **CLI框架**: Click
- **测试**: pytest, pytest-cov

## 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/youngfly93/excel_2_word.git
cd excel_2_word

# 安装依赖
pip install -r requirements.txt

# 开发模式安装
pip install -e .
```

### 基本使用

```bash
# 生成单个报告
reportgen generate --excel data/input/sample.xlsx --output data/output/

# 批量处理（脚本）
python scripts/batch_generate_reports.py data/input data/output --auto-detect

# 一键诊断（依赖/模板契约/可选：带excel做口径校验）
reportgen diagnose
reportgen diagnose -e data/input/sample.xlsx

# 查看帮助
reportgen --help

# 校验模板（变量/映射）
reportgen validate -t templates/jinja2_template_358_v18.docx --show-vars
reportgen validate -t templates/jinja2_template_358_v18.docx --check-mapping
```

### 配置

主要配置文件位于 `config/` 目录：

- `mapping.yaml` - 字段映射配置（Excel列名到模板变量）
- `project_types.yaml` - 项目类型识别规则
- `settings.yaml` - 全局设置

## 项目结构

```
reportgen/          # 主包目录
├── core/          # 核心业务逻辑
├── models/        # 数据模型
├── utils/         # 工具函数
└── config/        # 配置管理

tests/             # 测试目录
├── unit/          # 单元测试
├── integration/   # 集成测试
└── fixtures/      # 测试数据

config/            # 配置文件
templates/         # Docx模板文件
data/              # 数据目录
docs/              # 合同/操作手册/归档文档
scripts/           # 便捷脚本（CLI轻量封装）
tools/             # 分析/模板处理工具
```

## 性能指标

- Excel解析: < 5秒/文件
- 单个报告生成: < 10秒
- 批量50个样本: < 5分钟
- 内存占用: < 500MB/样本

## 开发

### 运行测试

```bash
# 运行所有测试
pytest tests/

# 测试覆盖率
pytest tests/ --cov=reportgen --cov-report=html

# 运行性能测试
pytest tests/ --benchmark-only
```

### 代码质量检查

```bash
# 代码风格检查
flake8 reportgen/

# 代码质量分析
pylint reportgen/

# 代码格式化
black reportgen/
isort reportgen/
```

## 文档

详细文档位于 `specs/001-excel-docx-automation/`:

- `spec.md` - 功能规范
- `plan.md` - 实施计划
- `quickstart.md` - 快速开始指南
- `data-model.md` - 数据模型定义
- `contracts/` - CLI接口和配置schema

## License

内部项目

## 联系方式

医疗报告团队

## 部署方式（推荐：Linux 服务器/生产环境）

> 本项目为 CLI 工具型应用，部署的核心是：准备 Python 环境 + 安装依赖 + 放置配置/模板 + 通过命令行运行。

### 1) 准备环境

- Python: 3.9+
- 建议使用独立账号与虚拟环境（venv）

### 2) 安装（生产安装建议）

```bash
git clone https://github.com/youngfly93/excel_2_word.git
cd excel_2_word

python3 -m venv .venv
source .venv/bin/activate

python -m pip install -U pip
pip install -r requirements.txt

# 生产建议使用非 editable 安装（锁定当次代码状态）
pip install .
```

### 3) 配置与模板

- 配置目录：`config/`
- 默认模板：`templates/jinja2_template_358_v18.docx`
- 输出目录建议提前创建：`data/output/`（或自定义）

可先跑一遍自检：

```bash
reportgen diagnose
```

### 4) 运行（单份/批量）

```bash
# 单份
reportgen generate -e /path/to/input.xlsx -o /path/to/output_dir

# 自动识别项目类型并选模板
reportgen generate -e /path/to/input.xlsx --auto-detect -o /path/to/output_dir

# 批量（脚本）
python scripts/batch_generate_reports.py /path/to/excels /path/to/output_dir --auto-detect
```

### 5) （可选）参考文献缓存预热

如果你启用了基因知识库并希望减少在线请求，可预先把 PMID/NCT 信息拉到本地缓存（默认写入 `data/cache/`）：

```bash
python scripts/prefetch_references.py --input /path/to/gene_knowledge.xlsx
```

