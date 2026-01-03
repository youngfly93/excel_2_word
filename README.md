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
cd /home/report/肠癌358基因

# 安装依赖
pip install -r requirements.txt

# 开发模式安装
pip install -e .
```

### 基本使用

```bash
# 生成单个报告
reportgen generate --excel data/input/sample.xlsx --output data/output/

# 批量处理
reportgen batch --excel "data/input/*.xlsx" --output data/output/

# 验证配置
reportgen validate all

# 查看帮助
reportgen --help
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

