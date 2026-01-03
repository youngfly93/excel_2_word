# Research: Excel到Docx自动化报告生成系统

**Date**: 2025-10-24  
**Feature**: 001-excel-docx-automation  
**Phase**: 0 - Technology Research & Best Practices

## Technology Selection

### Decision: python-docx-template (docxtpl) + pandas

**Rationale**:
1. **数据源匹配度高**: pandas天然支持Excel多sheet读取、中文表头处理、数值/日期类型清洗
2. **模板表达力强**: docxtpl基于Jinja2，原生支持变量、循环、条件、过滤器，完美匹配医疗报告的"变异表循环 + MSI/TMB条件段落"需求
3. **富文本和图片支持**: InlineImage支持图片插入，可扩展支持页眉页脚/二维码/签名图片
4. **版式保真度**: 不依赖LibreOffice转换链，直接操作docx内部XML，Word原版式保真
5. **离线可控**: 纯Python实现，无外部守护进程，符合医疗数据隐私合规要求
6. **CLI友好**: 易于封装命令行工具，支持批处理脚本
7. **学习曲线平缓**: 用户已提供的变量命名方案与docxtpl完全匹配，无需额外适配

**Alternatives Considered**:
- **Docxtemplater (Node.js)**: 功能强大但需要Node.js环境，图片等高级功能需付费插件，不如Python生态统一
- **Carbone (CLI/Docker)**: 支持容器化部署但依赖LibreOffice，运维复杂度高，渲染性能不稳定
- **docx-mailmerge**: 仅适合简单邮件合并，不支持图片、循环逻辑弱，无法满足复杂医疗报告需求
- **LOTemplate / XDocReport (Java)**: 需要Java生态，引擎重，调优成本高
- **python-docx**: 基础库，需要手工构建文档结构，不适合模板化场景

### Dependencies Justification

| 依赖库 | 版本要求 | 用途 | 理由 |
|--------|---------|------|------|
| `python-docx-template` | >=0.16.0 | Docx模板渲染 | 核心引擎，Jinja2模板支持完善 |
| `pandas` | >=1.5.0 | Excel数据处理 | 行业标准，性能优异，API稳定 |
| `openpyxl` | >=3.0.0 | Excel读写引擎 | pandas的xlsx后端，支持样式读取 |
| `PyYAML` | >=6.0 | 配置文件解析 | 标准配置格式，可读性强 |
| `python-dateutil` | >=2.8.0 | 日期解析 | 智能识别多种日期格式 |
| `click` | >=8.0.0 | CLI框架 | 参数验证、帮助文档自动生成 |
| `pytest` | >=7.0.0 | 测试框架 | 行业标准，插件生态丰富 |
| `pytest-cov` | >=4.0.0 | 覆盖率测试 | 与pytest集成完美 |

## Best Practices Research

### 1. Excel数据提取最佳实践

**问题**: Excel文件可能包含合并单元格、多种日期格式、全角/半角混用

**解决方案**:
```python
# 使用pandas读取Excel时的最佳配置
pd.read_excel(
    file_path,
    sheet_name=None,          # 读取所有sheet
    dtype=str,                # 初始全部按字符串读取，避免自动类型推断错误
    na_values=['', 'NA', 'N/A', '-'],  # 统一空值处理
    keep_default_na=False     # 保留原始空字符串
)

# 处理合并单元格：pandas自动将合并单元格值填充到第一个单元格
# 需要手动前向填充（forward fill）
df.fillna(method='ffill')
```

**参考来源**: pandas官方文档 + StackOverflow医疗数据处理最佳实践

### 2. Docx模板设计模式

**问题**: 复杂表格循环、条件段落、动态图片插入

**解决方案**:

**单值变量**:
```jinja2
患者姓名：{{ patient_name }}
样本编号：{{ sample_id }}
```

**表格循环** (在Word表格中):
```jinja2
{% for variant in variants %}
| {{ variant.gene }} | {{ variant.variant }} | {{ variant.af }}% | {{ variant.depth }} |
{% endfor %}
```

**条件段落**:
```jinja2
{% if msi.status == 'MSI-H' %}
结论：微卫星高度不稳定（MSI-H），提示可能对免疫治疗敏感。
{% else %}
结论：微卫星稳定（{{ msi.status }}）。
{% endif %}
```

**动态图片**:
```jinja2
{{ signature_image }}  # 需在Python中使用InlineImage对象
```

**参考来源**: python-docx-template官方文档和示例

### 3. 字段映射配置设计

**问题**: Excel表头可能是中文且存在同义词（如"样本编号"、"送检编号"、"条码号"）

**解决方案**: 使用YAML配置，支持同义词列表

```yaml
# mapping.yaml
single_values:
  patient_name:
    synonyms: ["患者姓名", "姓名", "病人姓名"]
    type: string
    required: true
  sample_id:
    synonyms: ["样本编号", "送检编号", "条码号", "样本ID"]
    type: string
    required: true
  report_date:
    synonyms: ["出报告日期", "报告日期", "报告时间"]
    type: date
    format: "%Y-%m-%d"
    required: true

table_data:
  variants:
    sheet_name: "变异明细"
    columns:
      gene:
        synonyms: ["基因", "Gene", "基因名称"]
        type: string
      variant:
        synonyms: ["变异", "Variant", "变异位点", "突变"]
        type: string
      af:
        synonyms: ["频率", "丰度", "AF", "变异频率"]
        type: float
        format: "{:.2f}%"
```

**映射算法**:
1. 读取Excel表头
2. 对每个目标变量，遍历同义词列表
3. 找到第一个匹配的列名（不区分大小写，去除空格）
4. 提取数据并应用类型转换和格式化

**参考来源**: 医疗信息系统集成经验 + 12-factor app配置管理

### 4. 数据清洗和验证

**问题**: 数值包含非法字符、日期格式不统一、全角/半角混用

**解决方案**:

**日期统一化**:
```python
from dateutil import parser

def normalize_date(date_str):
    """支持多种日期格式自动识别"""
    try:
        dt = parser.parse(str(date_str), fuzzy=True)
        return dt.strftime("%Y-%m-%d")
    except:
        return None
```

**数值清洗**:
```python
import re

def clean_numeric(value_str):
    """去除空格、全角字符、百分号等"""
    if pd.isna(value_str):
        return None
    # 全角转半角
    cleaned = value_str.translate(str.maketrans('０１２３４５６７８９．', '0123456789.'))
    # 去除空格和百分号
    cleaned = re.sub(r'[\s%]', '', cleaned)
    try:
        return float(cleaned)
    except:
        return None
```

**文本标准化**:
```python
def clean_text(text):
    """去除不可见字符、统一空格"""
    if pd.isna(text):
        return ""
    # 去除不可见字符
    text = ''.join(char for char in text if char.isprintable() or char in '\n\r\t')
    # 统一多个空格为单个
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
```

**参考来源**: 数据清洗最佳实践 + 中文数据处理经验

### 5. 错误处理和日志记录

**问题**: 需要详细的操作审计和问题追溯

**解决方案**: 结构化JSON日志 + 分级错误处理

```python
import logging
import json
from datetime import datetime

# 配置结构化日志
class StructuredLogger:
    def __init__(self, log_file):
        self.logger = logging.getLogger('reportgen')
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_event(self, event_type, **kwargs):
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            **kwargs
        }
        self.logger.info(json.dumps(log_entry, ensure_ascii=False))

# 使用示例
logger.log_event(
    'report_generated',
    input_file='data.xlsx',
    output_file='report.docx',
    template_version='1.0.0',
    mapping_version='1.0.0',
    duration_seconds=8.5,
    status='success'
)
```

**错误分级**:
- **CRITICAL**: 关键字段缺失，中止生成
- **ERROR**: 文件损坏、权限不足，终止当前样本
- **WARNING**: 非关键字段缺失，使用默认值
- **INFO**: 正常操作日志

**参考来源**: 医疗系统审计标准 + Python logging最佳实践

### 6. 性能优化策略

**问题**: 批量处理50个样本需在5分钟内完成

**解决方案**:

**Excel读取优化**:
```python
# 只读取需要的sheet，避免全量加载
sheets_needed = ['基本信息', '变异明细', 'MSI']
data = pd.read_excel(file_path, sheet_name=sheets_needed)

# 使用usecols只读取需要的列
data = pd.read_excel(file_path, usecols=['患者姓名', '样本编号', ...])
```

**模板缓存**:
```python
# 批量处理时复用同一模板对象
template = DocxTemplate('template.docx')
for sample_data in batch_samples:
    template.render(sample_data)
    template.save(f'output_{sample_data["sample_id"]}.docx')
    # 重要：每次save后重新加载模板
    template = DocxTemplate('template.docx')
```

**并发处理** (可选，Phase 2):
```python
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(generate_report, sample) for sample in samples]
    results = [f.result() for f in futures]
```

**参考来源**: pandas性能调优指南 + docxtpl性能建议

### 7. 项目类型识别策略

**问题**: 自动识别"301基因+MSI"、"358基因+MSI"、"肺癌甲基化"

**解决方案**: 基于关键词匹配的规则引擎

```yaml
# project_types.yaml
project_types:
  - id: crc_301_msi
    name: "结直肠癌301基因+MSI"
    keywords: ["301", "基因", "msi", "结直肠"]
    template: "templates/crc_301_msi_template.docx"
    
  - id: crc_358_msi
    name: "结直肠癌358基因+MSI"
    keywords: ["358", "基因", "msi", "结直肠"]
    template: "templates/crc_358_msi_template.docx"
    
  - id: lung_methylation
    name: "肺癌甲基化"
    keywords: ["肺癌", "甲基化", "methylation"]
    template: "templates/lung_methylation_template.docx"
```

**识别算法**:
1. 读取Excel中"项目名称"或"检测项目"字段
2. 转换为小写并去除空格
3. 计算与每个项目类型的关键词匹配分数
4. 选择分数最高的项目类型
5. 若无匹配或分数过低，使用默认模板并记录警告

**参考来源**: 规则引擎设计模式 + 医疗项目分类经验

## Testing Strategy

### Unit Testing

**核心模块测试覆盖**:
- `excel_reader.py`: 测试多sheet读取、合并单元格处理、类型转换
- `field_mapper.py`: 测试同义词匹配、必填字段验证、默认值处理
- `data_cleaner.py`: 测试日期解析、数值清洗、文本标准化
- `template_renderer.py`: 测试变量替换、循环渲染、条件逻辑

**测试数据准备**:
- 创建脱敏的测试Excel文件，包含：
  - 完整数据样本
  - 缺失关键字段样本
  - 缺失非关键字段样本
  - 特殊字符和格式异常样本

### Integration Testing

**端到端测试场景**:
1. 使用MLF2509307001T_MLB2509307001.result.xlsx生成报告
2. 验证生成的docx文件可正常打开
3. 提取docx内容，比对关键字段值
4. 验证日志文件包含完整操作记录

**批量处理测试**:
1. 准备10个样本的Excel文件
2. 执行批量生成命令
3. 验证生成10个独立文件
4. 验证汇总日志的统计准确性

### Performance Testing

**基准测试**:
```python
import pytest

@pytest.mark.benchmark
def test_excel_parsing_performance(benchmark):
    result = benchmark(parse_excel, 'large_file.xlsx')
    assert result is not None

@pytest.mark.benchmark
def test_report_generation_performance(benchmark):
    result = benchmark(generate_report, sample_data)
    assert result['duration'] < 10.0  # 小于10秒
```

**性能目标验证**:
- Excel解析 < 5秒
- 单个报告生成 < 10秒
- 批量50个 < 5分钟

### Test Data Management

**测试数据脱敏策略**:
- 患者姓名：使用"测试患者001-100"
- 样本编号：使用"TEST-2025-0001"格式
- 其他敏感信息：使用随机生成或固定假数据

**测试数据版本控制**:
- 小型测试文件（<1MB）提交到git
- 大型测试文件放在`tests/fixtures/`并添加到.gitignore
- 在CI环境中使用环境变量指定测试数据路径

## Security & Compliance

### 医疗数据隐私保护

1. **本地处理**: 所有数据处理在本地进行，无外部API调用
2. **无数据留存**: 系统不存储任何患者数据，仅在内存中处理
3. **日志脱敏**: 日志中不记录患者姓名等敏感信息，仅记录样本ID
4. **测试数据脱敏**: 所有测试和开发使用脱敏数据

### 数据完整性保障

1. **输入验证**: 严格验证Excel文件格式和必填字段
2. **数据溯源**: 每份报告记录源Excel文件路径、处理时间、软件版本
3. **审计日志**: 完整记录所有操作，支持事后审计
4. **版本标识**: 生成的报告包含软件版本、模板版本、配置版本

## Deployment Considerations

### Installation

```bash
# 安装依赖
pip install -r requirements.txt

# 开发模式安装
pip install -e .

# 运行测试
pytest tests/ --cov=reportgen --cov-report=html
```

### Configuration

```
config/
├── mapping.yaml          # 字段映射（必须配置）
├── project_types.yaml    # 项目类型识别（必须配置）
└── settings.yaml         # 全局设置（可选，有默认值）
```

### Usage

```bash
# 单个报告生成
reportgen generate --excel data/input/sample.xlsx --output data/output/

# 批量处理
reportgen batch --excel data/input/*.xlsx --output data/output/

# 查看帮助
reportgen --help
```

## Risks & Mitigation

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Excel格式不兼容 | 无法读取数据 | 支持.xlsx格式，在文档中明确说明，启动时验证文件格式 |
| 模板损坏 | 无法生成报告 | 启动时验证模板完整性，提供模板自检命令 |
| 性能不达标 | 批量处理超时 | 性能基准测试持续监控，必要时引入缓存和并发 |
| 字段映射错误 | 数据填充错位 | 详细的单元测试覆盖，提供映射配置验证工具 |
| 日期格式多样 | 解析失败 | 使用dateutil智能解析，记录解析失败的原始值 |

## Next Steps

1. ✅ Phase 0完成 - 技术选型和最佳实践研究完成
2. ⏭️ Phase 1 - 生成data-model.md定义数据结构
3. ⏭️ Phase 1 - 生成contracts/定义CLI接口和配置schema
4. ⏭️ Phase 1 - 生成quickstart.md快速开始指南
5. ⏭️ Phase 2 - 生成tasks.md任务分解（由/speckit.tasks命令执行）

