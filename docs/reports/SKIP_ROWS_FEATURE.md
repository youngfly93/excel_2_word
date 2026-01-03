# Skip Rows Feature Documentation

**Feature**: 自动跳过Excel表格中的无效行（如空行、旧表头行）
**Version**: 实现于 Phase 3
**日期**: 2025-11-17

---

## 功能概述

skip_rows功能允许在读取Excel sheet时自动跳过指定数量的行。这对于处理具有多重表头、空行或无效数据行的Excel文件特别有用。

### 主要应用场景

1. **多重表头**: Excel文件包含多个表头行，只有最后一行是真实的列名
2. **空行分隔**: Excel文件使用空行分隔不同的数据区域
3. **说明文本**: Excel文件顶部包含说明文字或注释

---

## 实现原理

### 1. 配置加载

ExcelReader在初始化时从`config/mapping.yaml`中加载skip_rows配置：

```python
class ExcelReader:
    def __init__(self, config_dir: str = "config", log_file: Optional[str] = None):
        self.logger = get_logger(log_file=log_file)
        self.config_dir = config_dir
        self.skip_rows_config = self._load_skip_rows_config()
```

### 2. 配置文件格式

在`config/mapping.yaml`的`table_data`section中为每个表格配置skip_rows：

```yaml
table_data:
  cnv:
    sheet_name: "Cnv"
    skip_rows: 2  # 跳过前2行
    columns:
      gene:
        synonyms: ['Gene', 'gene', '基因']
```

### 3. 自动应用

读取Excel sheet时，ExcelReader自动查找并应用skip_rows配置：

```python
for sheet_name in sheet_names:
    # 检查是否需要跳过行
    skip_rows = self.skip_rows_config.get(sheet_name, 0)
    if skip_rows > 0:
        df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            engine="openpyxl",
            skiprows=skip_rows
        )
    else:
        df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")
```

---

## 使用示例

### 示例1: CNV Sheet

**Excel结构** (Cnv sheet):
```
Row 0: Gene, Exist%, HetNum, Cnvkit, ...  (旧表头，已废弃)
Row 1: (空行)
Row 2: #Chr, Start, End, Status, CopyNum(X), ...  (真实表头)
Row 3: chr1, 12345, 67890, Gain, 3.2, ...  (数据)
```

**配置**:
```yaml
cnv:
  sheet_name: "Cnv"
  skip_rows: 2  # 跳过Row 0和Row 1
```

**结果**:
- Row 2 (#Chr, Start, End, ...) 被作为表头
- Row 3 及之后的行被作为数据

### 示例2: Fusion Sheet

**Excel结构** (Fusion sheet):
```
Row 0: Est_Type, chr1, gene1, ...  (旧表头)
Row 1: (空行)
Row 2: #Est_Type, Gene1, Gene2, ...  (真实表头)
Row 3: (空行)
Row 4: Gene1, Chr1, Pos1, ...  (数据)
```

**配置**:
```yaml
fusion:
  sheet_name: "Fusion"
  skip_rows: 2  # 跳过Row 0和Row 1
```

**结果**:
- Row 2 (#Est_Type, Gene1, Gene2, ...) 被作为表头
- Row 3 (空行) 被pandas自动过滤
- Row 4 及之后的行被作为数据

### 示例3: HLA Sheet (不跳过)

**Excel结构** (HLA sheet):
```
Row 0: HLA-A, HET, ...  (表头)
Row 1: [Type 1], 24:02:01:03, ...  (数据)
Row 2: [Type 2], 24:02:83, ...  (数据)
```

**配置**:
```yaml
hla:
  sheet_name: "HLA"
  skip_rows: 0  # 不跳过任何行
```

**结果**:
- Row 0 (HLA-A, HET, ...) 被作为表头
- Row 1 及之后的行被作为数据

---

## 技术细节

### Pandas skiprows参数

ExcelReader使用pandas的`skiprows`参数来实现跳过行功能：

```python
df = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=2)
```

**Pandas行为**:
- `skiprows=2`: 跳过前2行（索引0和1）
- 跳过后的第一行（原始索引2）被自动作为列名（header）
- 后续行（原始索引3+）被作为数据

### 配置加载逻辑

`_load_skip_rows_config`方法从mapping.yaml中提取skip_rows配置：

```python
def _load_skip_rows_config(self) -> Dict[str, int]:
    """
    从mapping配置中加载skip_rows设置

    Returns:
        字典 {sheet_name: skip_rows数量}
    """
    skip_rows_map = {}

    mapping_file = os.path.join(self.config_dir, "mapping.yaml")
    with open(mapping_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 遍历table_data配置，提取skip_rows设置
    table_data = config.get('table_data', {})
    for table_name, table_config in table_data.items():
        sheet_name = table_config.get('sheet_name')
        skip_rows = table_config.get('skip_rows')

        if sheet_name and skip_rows is not None:
            skip_rows_map[sheet_name] = skip_rows

    return skip_rows_map
```

---

## 配置建议

### 如何确定skip_rows的值

1. **检查Excel文件结构**: 使用inspect_sheets.py脚本查看sheet的原始结构：
   ```bash
   python3 inspect_sheets.py
   ```

2. **识别真实表头**: 找到包含实际列名的行（通常以#开头或包含描述性列名）

3. **计算跳过行数**:
   - skip_rows = 真实表头的行索引
   - 例如：真实表头在Row 2，则skip_rows=2

4. **验证配置**: 使用test_skip_rows.py验证：
   ```bash
   python3 test_skip_rows.py
   ```

### 常见配置值

- `skip_rows: 0` - 不跳过任何行（第1行就是表头）
- `skip_rows: 1` - 跳过第1行（第2行是表头）
- `skip_rows: 2` - 跳过前2行（第3行是表头）

---

## 测试工具

### test_skip_rows.py

测试skip_rows功能是否正确应用：

```bash
python3 test_skip_rows.py [excel_file]
```

**输出**:
- skip_rows配置加载结果
- CNV/Fusion/HLA数据读取情况
- 列名验证（检查是否读取到正确的表头）

### inspect_sheets.py

详细检查Excel sheet的原始结构：

```bash
python3 inspect_sheets.py
```

**输出**:
- 原始数据（不跳过行）
- 跳过1行后的结果
- 跳过2行后的结果
- 列名对比

### debug_config_loading.py

调试mapping.yaml配置加载：

```bash
python3 debug_config_loading.py
```

**输出**:
- Top-level配置项
- table_data配置数量
- 所有包含skip_rows的表格

---

## 常见问题

### Q1: 为什么CNV数据显示"未找到"？

**A**: 如果Excel文件中CNV sheet只有表头而没有数据行，ExcelReader会将其过滤掉（`_extract_table_data`方法要求`len(df) > 1`）。这是正常现象，表示该样本没有CNV突变。

### Q2: 列名显示为"Unnamed: 0", "Unnamed: 1"怎么办？

**A**: 这说明skip_rows值不正确，跳过后的第一行不是有效的表头。需要调整skip_rows值：
- 如果表头在更后面的行，增加skip_rows值
- 如果表头在更前面的行，减少skip_rows值

### Q3: skip_rows配置未生效怎么办？

**A**: 检查以下几点：
1. 配置是否在`table_data:`section内（不能在validation或其他section）
2. `sheet_name`是否与Excel中的sheet名称完全匹配（区分大小写）
3. 重启程序/重新运行（配置在初始化时加载，修改后需要重新运行）

### Q4: 如何处理多个空行？

**A**: skip_rows只跳过开头的连续行。如果数据中间有空行，pandas会自动过滤掉全空的行，不需要额外配置。

---

## 修改历史

| 日期 | 版本 | 修改内容 |
|------|------|----------|
| 2025-11-17 | 1.0 | 初始实现skip_rows功能 |
| 2025-11-17 | 1.1 | 修复CNV/Fusion skip_rows从1改为2 |
| 2025-11-17 | 1.2 | 修复mapping.yaml结构问题（将CNV/Fusion/HLA移入table_data section） |

---

## 相关文件

- `reportgen/core/excel_reader.py` - ExcelReader实现
- `config/mapping.yaml` - 配置文件
- `test_skip_rows.py` - 测试脚本
- `inspect_sheets.py` - 检查脚本
- `debug_config_loading.py` - 调试脚本
- `fix_mapping_structure.py` - 结构修复脚本

---

## 下一步改进

1. **支持更灵活的skip配置**: 支持跳过特定行号列表（如skiprows=[0, 2, 4]）
2. **自动检测表头**: 自动识别真实表头行，无需手动配置skip_rows
3. **验证工具**: 添加配置验证工具，检查skip_rows配置是否正确
4. **错误提示**: 当skip_rows配置不正确时，提供更详细的错误信息

---

**维护者**: Claude Code
**最后更新**: 2025-11-17
