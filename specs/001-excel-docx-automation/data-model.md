# Data Model: Excel到Docx自动化报告生成系统

**Date**: 2025-10-24  
**Feature**: 001-excel-docx-automation  
**Phase**: 1 - Data Model Definition

## Overview

本文档定义系统中的核心数据模型，包括实体类、字段定义、验证规则和状态转换。所有模型基于特性规范中的Key Entities设计。

## Core Entities

### 1. ExcelDataSource

**描述**: 表示Excel结果表数据源，封装Excel文件的读取和数据提取逻辑

**字段**:

| 字段名 | 类型 | 必填 | 描述 | 验证规则 |
|--------|------|------|------|---------|
| `file_path` | str | ✓ | Excel文件的绝对路径 | 文件存在、后缀为.xlsx |
| `file_size` | int | ✓ | 文件大小（字节） | > 0, < 100MB |
| `sheets` | Dict[str, pd.DataFrame] | ✓ | 所有sheet的数据字典，key为sheet名 | 至少包含1个sheet |
| `sheet_names` | List[str] | ✓ | 所有sheet的名称列表 | 非空列表 |
| `loaded_at` | datetime | ✓ | 数据加载时间戳 | 系统自动生成 |

**方法**:
- `load()`: 从文件路径加载Excel数据到内存
- `get_sheet(sheet_name: str) -> pd.DataFrame`: 获取指定sheet的数据
- `get_column_names(sheet_name: str) -> List[str]`: 获取指定sheet的列名列表
- `validate()`: 验证文件格式和数据完整性

**示例**:
```python
excel_data = ExcelDataSource(file_path="/path/to/result.xlsx")
excel_data.load()
basic_info = excel_data.get_sheet("基本信息")
variants = excel_data.get_sheet("变异明细")
```

---

### 2. FieldMapping

**描述**: 字段映射规则，定义Excel列名到模板变量的映射关系

**字段**:

| 字段名 | 类型 | 必填 | 描述 | 验证规则 |
|--------|------|------|------|---------|
| `variable_name` | str | ✓ | 模板中的变量名（如patient_name） | 小写+下划线，无空格 |
| `synonyms` | List[str] | ✓ | Excel列名同义词列表 | 非空列表 |
| `data_type` | str | ✓ | 数据类型：string/int/float/date/bool | 枚举值 |
| `required` | bool | ✓ | 是否为必填字段 | true/false |
| `default_value` | Any | ✗ | 缺失时的默认值 | 可为None |
| `format_template` | str | ✗ | 格式化模板（如"{:.2f}%"） | 可为None |
| `sheet_name` | str | ✗ | 所属sheet（用于表格数据） | 可为None表示单值字段 |

**方法**:
- `match_column(column_names: List[str]) -> Optional[str]`: 在列名列表中查找匹配的列名
- `format_value(raw_value: Any) -> str`: 按格式模板格式化值
- `validate_value(value: Any) -> bool`: 验证值的合法性

**示例**:
```python
mapping = FieldMapping(
    variable_name="patient_name",
    synonyms=["患者姓名", "姓名", "病人姓名"],
    data_type="string",
    required=True
)
matched_column = mapping.match_column(["患者姓名", "年龄", "性别"])
# 返回: "患者姓名"
```

---

### 3. ReportData

**描述**: 待填充的报告数据模型，包含所有需要填充到模板的数据

**字段**:

| 字段名 | 类型 | 必填 | 描述 | 验证规则 |
|--------|------|------|------|---------|
| `patient_info` | Dict[str, Any] | ✓ | 患者基本信息 | 必须包含patient_name和sample_id |
| `project_info` | Dict[str, Any] | ✓ | 项目检测信息 | 必须包含project_name |
| `variants` | List[Dict[str, Any]] | ✗ | 变异明细列表 | 可为空列表 |
| `fusions` | List[Dict[str, Any]] | ✗ | 融合列表 | 可为空列表 |
| `cnvs` | List[Dict[str, Any]] | ✗ | CNV拷贝数变异列表 | 可为空列表 |
| `msi` | Dict[str, Any] | ✗ | MSI指标 | 包含status和score |
| `tmb` | Dict[str, Any] | ✗ | TMB指标 | 包含value和unit |
| `methylation` | Dict[str, Any] | ✗ | 甲基化结果（肺癌项目） | 可为None |
| `qc_metrics` | Dict[str, Any] | ✗ | 质控指标 | 包含覆盖度、深度等 |
| `metadata` | Dict[str, Any] | ✓ | 元数据 | 包含生成时间、版本信息 |

**方法**:
- `validate()`: 验证所有必填字段完整性
- `to_template_context() -> Dict`: 转换为模板引擎需要的上下文字典
- `get_missing_required_fields() -> List[str]`: 返回缺失的必填字段列表

**字段详细定义**:

**patient_info**:
```python
{
    "patient_name": str,      # 必填
    "sample_id": str,         # 必填
    "gender": str,            # 可选："男"/"女"
    "age": int,               # 可选
    "pathology_id": str,      # 可选：病理号
    "hospital": str,          # 可选：送检医院
    "department": str,        # 可选：送检科室
    "sample_type": str,       # 可选：样本类型
    "collection_date": str,   # 可选：采样日期 YYYY-MM-DD
    "receive_date": str,      # 可选：接收日期
}
```

**project_info**:
```python
{
    "project_name": str,      # 必填：项目名称
    "cancer_type": str,       # 可选：癌种
    "panel_name": str,        # 可选：panel名称
    "detection_method": str,  # 可选：检测方法
    "report_date": str,       # 必填：报告日期 YYYY-MM-DD
}
```

**variants**:
```python
[
    {
        "gene": str,          # 基因名
        "variant": str,       # 变异位点
        "exon": str,          # 外显子
        "cds": str,           # cDNA位置
        "protein": str,       # 蛋白改变
        "af": float,          # 变异频率（0-100）
        "depth": int,         # 覆盖深度
        "type": str,          # 变异类型：SNV/Indel/CNV
        "evidence": str,      # 证据级别：1A/1B/2A/2B/3/4
    },
    # ... 更多变异
]
```

**metadata**:
```python
{
    "generated_at": str,           # 生成时间 ISO格式
    "software_version": str,       # 软件版本
    "template_version": str,       # 模板版本
    "mapping_version": str,        # 映射配置版本
    "source_excel": str,           # 源Excel文件路径
}
```

---

### 4. DocxTemplate

**描述**: Docx模板文件的抽象，封装模板加载和渲染逻辑

**字段**:

| 字段名 | 类型 | 必填 | 描述 | 验证规则 |
|--------|------|------|------|---------|
| `template_path` | str | ✓ | 模板文件路径 | 文件存在、后缀为.docx |
| `template_id` | str | ✓ | 模板唯一标识 | 如"crc_301_msi" |
| `template_name` | str | ✓ | 模板显示名称 | 如"结直肠癌301基因+MSI" |
| `version` | str | ✓ | 模板版本号 | 语义化版本 x.y.z |
| `applicable_project_types` | List[str] | ✓ | 适用的项目类型列表 | 非空列表 |
| `placeholders` | List[str] | ✗ | 模板中的占位符列表 | 系统自动提取 |
| `loaded_template` | DocxTemplate | ✗ | 加载的模板对象（缓存） | 内部使用 |

**方法**:
- `load()`: 加载模板文件到内存
- `render(context: Dict) -> bytes`: 渲染模板，返回docx字节流
- `extract_placeholders() -> List[str]`: 提取模板中的所有占位符
- `validate_context(context: Dict) -> List[str]`: 验证上下文是否包含所有必需占位符

**示例**:
```python
template = DocxTemplate(
    template_path="/templates/crc_301_msi_template.docx",
    template_id="crc_301_msi",
    template_name="结直肠癌301基因+MSI",
    version="1.0.0"
)
template.load()
output_bytes = template.render(report_data.to_template_context())
```

---

### 5. ProjectType

**描述**: 项目类型定义和识别规则

**字段**:

| 字段名 | 类型 | 必填 | 描述 | 验证规则 |
|--------|------|------|------|---------|
| `id` | str | ✓ | 项目类型唯一标识 | 如"crc_301_msi" |
| `name` | str | ✓ | 项目类型显示名称 | 如"结直肠癌301基因+MSI" |
| `keywords` | List[str] | ✓ | 识别关键词列表 | 非空列表 |
| `template_path` | str | ✓ | 对应的模板路径 | 文件存在 |
| `priority` | int | ✗ | 优先级（用于关键词冲突） | 默认0，数字越大优先级越高 |

**方法**:
- `calculate_match_score(project_name: str) -> float`: 计算与给定项目名称的匹配分数
- `is_match(project_name: str, threshold: float = 0.6) -> bool`: 判断是否匹配

**示例**:
```python
project_type = ProjectType(
    id="crc_301_msi",
    name="结直肠癌301基因+MSI",
    keywords=["301", "基因", "msi", "结直肠"],
    template_path="/templates/crc_301_msi_template.docx",
    priority=10
)
score = project_type.calculate_match_score("结直肠癌301基因+msi检测")
# 返回: 0.8 (匹配3/4个关键词)
```

---

### 6. GeneratedReport

**描述**: 生成的报告文件信息

**字段**:

| 字段名 | 类型 | 必填 | 描述 | 验证规则 |
|--------|------|------|------|---------|
| `output_path` | str | ✓ | 输出文件绝对路径 | 目录必须存在 |
| `file_name` | str | ✓ | 文件名 | 符合命名规范 |
| `sample_id` | str | ✓ | 关联的样本编号 | 非空 |
| `status` | str | ✓ | 生成状态 | success/failed |
| `file_size` | int | ✗ | 文件大小（字节） | > 0 |
| `generated_at` | datetime | ✓ | 生成时间 | 系统自动生成 |
| `duration_seconds` | float | ✗ | 生成耗时（秒） | >= 0 |
| `error_message` | str | ✗ | 错误信息（失败时） | 可为None |
| `warnings` | List[str] | ✗ | 警告信息列表 | 如缺失非必填字段 |

**方法**:
- `validate_file()`: 验证生成的文件可正常打开
- `calculate_checksum() -> str`: 计算文件MD5校验和

**文件命名规范**:
```
{patient_name}_{sample_id}_{project_name}_{report_date}_终版.docx

示例:
张三_TEST-2025-0001_结直肠癌301基因+msi_2025-10-24_终版.docx
```

---

### 7. ProcessLog

**描述**: 处理日志，记录每次报告生成的完整信息

**字段**:

| 字段名 | 类型 | 必填 | 描述 | 验证规则 |
|--------|------|------|------|---------|
| `log_id` | str | ✓ | 日志唯一ID（UUID） | UUID格式 |
| `timestamp` | datetime | ✓ | 操作时间戳 | ISO 8601格式 |
| `operation_type` | str | ✓ | 操作类型 | single/batch |
| `input_file` | str | ✓ | 输入Excel文件路径 | 绝对路径 |
| `output_files` | List[str] | ✓ | 输出文件路径列表 | 绝对路径列表 |
| `status` | str | ✓ | 整体状态 | success/partial/failed |
| `duration_seconds` | float | ✓ | 总耗时（秒） | >= 0 |
| `success_count` | int | ✓ | 成功生成数量 | >= 0 |
| `failed_count` | int | ✓ | 失败数量 | >= 0 |
| `error_details` | List[Dict] | ✗ | 错误详情列表 | 每项包含sample_id和error_message |
| `missing_fields` | List[str] | ✗ | 缺失字段汇总 | 去重后的字段列表 |
| `template_version` | str | ✓ | 使用的模板版本 | 语义化版本 |
| `mapping_version` | str | ✓ | 使用的映射配置版本 | 语义化版本 |
| `software_version` | str | ✓ | 软件版本 | 语义化版本 |

**方法**:
- `to_json() -> str`: 序列化为JSON格式日志
- `to_dict() -> Dict`: 转换为字典
- `log_to_file(log_path: str)`: 写入日志文件

**日志JSON格式示例**:
```json
{
  "log_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2025-10-24T14:30:25.123456",
  "operation_type": "batch",
  "input_file": "/data/input/batch_001.xlsx",
  "output_files": [
    "/data/output/张三_TEST-001_结直肠癌301基因+msi_2025-10-24_终版.docx",
    "/data/output/李四_TEST-002_结直肠癌301基因+msi_2025-10-24_终版.docx"
  ],
  "status": "success",
  "duration_seconds": 18.5,
  "success_count": 2,
  "failed_count": 0,
  "template_version": "1.0.0",
  "mapping_version": "1.0.0",
  "software_version": "1.0.0"
}
```

---

## Entity Relationships

```
ExcelDataSource
    ↓ (provides data to)
FieldMapping
    ↓ (maps to)
ReportData
    ↓ (rendered by)
DocxTemplate ← (selected by) ← ProjectType
    ↓ (generates)
GeneratedReport
    ↓ (logged in)
ProcessLog
```

**关系说明**:
1. `ExcelDataSource`读取Excel文件数据
2. `FieldMapping`定义如何从Excel提取数据并映射到变量
3. `ReportData`聚合所有提取的数据
4. `ProjectType`识别项目类型并选择对应的`DocxTemplate`
5. `DocxTemplate`使用`ReportData`渲染生成`GeneratedReport`
6. `ProcessLog`记录整个生成过程

---

## Validation Rules

### 全局验证规则

1. **必填字段验证**: 所有标记为必填的字段在实例化时必须提供
2. **类型验证**: 字段值必须符合定义的类型
3. **范围验证**: 数值字段必须在合理范围内（如AF: 0-100, file_size > 0）
4. **格式验证**: 日期、文件路径等必须符合预定格式

### 业务逻辑验证

1. **关键字段非空**: patient_name和sample_id不能为空字符串
2. **文件存在性**: 所有文件路径在使用前必须验证存在性
3. **模板兼容性**: 渲染前验证ReportData包含模板所需的所有占位符
4. **项目类型匹配**: 确保选择的模板与识别的项目类型一致

---

## State Transitions

### ReportData状态流转

```
CREATED → VALIDATED → RENDERED → SAVED
```

1. **CREATED**: ReportData对象创建，数据初步填充
2. **VALIDATED**: 通过validate()验证所有必填字段完整
3. **RENDERED**: 数据已传递给模板引擎并渲染完成
4. **SAVED**: 渲染结果已保存为文件

### GeneratedReport状态流转

```
PENDING → GENERATING → SUCCESS/FAILED
```

1. **PENDING**: 报告生成任务创建
2. **GENERATING**: 正在生成中
3. **SUCCESS**: 生成成功，文件可用
4. **FAILED**: 生成失败，error_message记录原因

---

## Data Types Reference

### 自定义类型

```python
# 日期类型（字符串，格式YYYY-MM-DD）
DateString = str  # 必须匹配 r'\d{4}-\d{2}-\d{2}'

# 文件路径（绝对路径）
FilePath = str  # 必须是绝对路径

# 变异频率（百分比，0-100）
AlleleFrequency = float  # 0.0 <= value <= 100.0

# 覆盖深度（正整数）
Depth = int  # value > 0

# 项目类型ID
ProjectTypeId = str  # 小写字母+下划线，如"crc_301_msi"
```

### 枚举类型

```python
class OperationType(Enum):
    SINGLE = "single"
    BATCH = "batch"

class ReportStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"

class DataType(Enum):
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    DATE = "date"
    BOOL = "bool"

class VariantType(Enum):
    SNV = "SNV"
    INDEL = "Indel"
    CNV = "CNV"
    FUSION = "Fusion"

class EvidenceLevel(Enum):
    LEVEL_1A = "1A"
    LEVEL_1B = "1B"
    LEVEL_2A = "2A"
    LEVEL_2B = "2B"
    LEVEL_3 = "3"
    LEVEL_4 = "4"
```

---

## Performance Considerations

1. **Excel数据加载**: 使用pandas的lazy loading，只加载需要的sheet
2. **模板缓存**: 批量处理时复用模板对象，减少重复加载
3. **内存管理**: 处理大批量时分批加载，避免一次性加载所有数据到内存
4. **数据验证**: 在数据提取阶段就进行验证，避免在渲染阶段才发现错误

---

## Next Steps

- ✅ Phase 1: Data Model完成
- ⏭️ Phase 1: 生成contracts/定义CLI接口和配置schema
- ⏭️ Phase 1: 生成quickstart.md快速开始指南

