# Quick Start Guide: Excel到Docx自动化报告生成系统

**Version**: 1.0.0  
**Date**: 2025-10-24  
**Feature**: 001-excel-docx-automation

## 目标

在30分钟内完成系统安装、配置和生成第一份医疗报告。

## 前置要求

- **操作系统**: Linux (推荐) 或 Windows
- **Python版本**: 3.9 或更高
- **磁盘空间**: 至少500MB可用空间
- **权限**: 读写项目目录的权限

## 快速开始（5分钟）

### Step 1: 安装系统

```bash
# 克隆或下载项目到本地
cd /home/report/肠癌358基因

# 安装Python依赖
pip install -r requirements.txt

# 验证安装
reportgen --version
# 预期输出: reportgen version 1.0.0
```

### Step 2: 初始化项目

```bash
# 初始化配置文件和目录结构
reportgen init

# 检查生成的目录结构
tree -L 2
```

**生成的目录结构**:
```
肠癌358基因/
├── config/
│   ├── mapping.yaml          # ✓ 已生成
│   ├── project_types.yaml    # ✓ 已生成
│   └── settings.yaml         # ✓ 已生成
├── templates/
│   ├── crc_301_msi_template.docx    # ⚠ 需要准备
│   ├── crc_358_msi_template.docx    # ⚠ 需要准备
│   └── lung_methylation_template.docx  # ⚠ 需要准备
├── data/
│   ├── input/                # 放置Excel输入文件
│   ├── output/               # 生成的报告输出位置
│   └── logs/                 # 日志文件
└── README.md
```

### Step 3: 准备模板文件

**选项A: 从已有报告提取模板**（推荐）

```bash
# 使用项目根目录的终版报告提取模板
reportgen template extract \
  --source "于凤齐-直肠癌-结直肠癌301基因+msi-mljy-lz253376-终版.docx" \
  --output templates/crc_301_msi_template.docx

# 提取358基因模板
reportgen template extract \
  --source "于建琛-直肠癌-结直肠癌358基因+msi-mljy-lz254885-终版.docx" \
  --output templates/crc_358_msi_template.docx
```

**选项B: 手动创建模板**

1. 打开任一终版报告docx文件
2. 将可变内容替换为Jinja2占位符：
   - 患者姓名 → `{{ patient_name }}`
   - 样本编号 → `{{ sample_id }}`
   - 报告日期 → `{{ report_date }}`
3. 变异明细表使用循环：
   ```
   {% for variant in variants %}
   {{ variant.gene }} | {{ variant.variant }} | {{ variant.af }}%
   {% endfor %}
   ```
4. 保存为`templates/crc_301_msi_template.docx`

### Step 4: 配置字段映射

编辑`config/mapping.yaml`，确保Excel列名与模板变量正确映射：

```yaml
single_values:
  patient_name:
    synonyms: ["患者姓名", "姓名"]
    type: string
    required: true
  
  sample_id:
    synonyms: ["样本编号", "送检编号"]
    type: string
    required: true

table_data:
  variants:
    sheet_name: "变异明细"
    columns:
      gene:
        synonyms: ["基因", "Gene"]
        type: string
```

💡 **提示**: 初始化时已生成示例映射，根据实际Excel表头调整即可。

### Step 5: 生成第一份报告

```bash
# 使用示例Excel生成报告
reportgen generate \
  --excel MLF2509307001T_MLB2509307001.result.xlsx \
  --output data/output/

# 查看生成的报告
ls -lh data/output/
```

**预期输出**:
```
[INFO] 加载Excel文件: MLF2509307001T_MLB2509307001.result.xlsx
[INFO] 文件大小: 2.3 MB
[INFO] 检测到项目类型: 结直肠癌301基因+MSI
[INFO] 选择模板: templates/crc_301_msi_template.docx
[INFO] 提取患者信息: 张三 (TEST-2025-0001)
[INFO] 提取变异明细: 5条记录
[INFO] 渲染模板...
[INFO] 生成报告: data/output/张三_TEST-2025-0001_结直肠癌301基因+msi_2025-10-24_终版.docx
[SUCCESS] 报告生成成功，耗时: 8.2秒
```

### Step 6: 验证生成的报告

```bash
# 打开生成的报告查看
libreoffice data/output/*_终版.docx
# 或在Windows上
start data/output/*_终版.docx

# 或使用验证工具
reportgen validate excel \
  --excel MLF2509307001T_MLB2509307001.result.xlsx \
  --mapping config/mapping.yaml
```

**验证检查点**:
- ✓ 报告可以正常打开
- ✓ 患者姓名、样本编号等基本信息填充正确
- ✓ 变异明细表包含所有变异记录
- ✓ MSI/TMB指标正确显示
- ✓ 无多余的占位符（如`{{ unknown_var }}`）

---

## 常见场景

### 场景1: 批量处理多个Excel文件

```bash
# 将所有Excel文件放入data/input/目录
cp *.xlsx data/input/

# 批量处理
reportgen batch \
  --excel "data/input/*.xlsx" \
  --output data/output/ \
  --summary data/output/summary.json \
  --continue-on-error

# 查看处理结果
cat data/output/summary.json
```

### 场景2: 处理单个Excel中的多个样本

```bash
# 如果Excel文件包含多行样本数据
reportgen batch \
  --excel data/input/batch_samples.xlsx \
  --output data/output/
```

系统会自动识别每行为一个样本并生成独立报告。

### 场景3: 使用自定义模板

```bash
# 指定特定模板文件
reportgen generate \
  --excel data/input/sample.xlsx \
  --template templates/custom_template.docx \
  --output data/output/
```

### 场景4: 试运行验证（不生成实际文件）

```bash
# 验证数据完整性和映射正确性
reportgen generate \
  --excel data/input/sample.xlsx \
  --dry-run \
  --verbose
```

---

## 配置指南

### 配置文件位置

- `config/mapping.yaml` - 字段映射配置（**必须**）
- `config/project_types.yaml` - 项目类型识别规则（**必须**）
- `config/settings.yaml` - 全局设置（可选，有默认值）

### 修改字段映射

**问题**: Excel列名变化或新增字段

**解决**:
1. 编辑`config/mapping.yaml`
2. 在对应变量的`synonyms`列表中添加新列名
3. 保存并重新运行

**示例**:
```yaml
# 原配置
patient_name:
  synonyms: ["患者姓名"]

# 添加同义词
patient_name:
  synonyms: ["患者姓名", "姓名", "病人姓名"]  # ← 添加新列名
```

### 添加新项目类型

**问题**: 需要支持新的检测项目

**解决**:
1. 准备该项目类型的报告模板
2. 编辑`config/project_types.yaml`：

```yaml
project_types:
  - id: new_project
    name: "新项目名称"
    keywords: ["关键词1", "关键词2"]
    template: "templates/new_project_template.docx"
```

3. 将模板文件放入`templates/`目录
4. 重新运行即可自动识别

### 调整性能设置

**问题**: 批量处理速度慢

**解决**:
编辑`config/settings.yaml`：

```yaml
generation:
  performance:
    max_workers: 8  # 增加并发数（默认4）
    timeout_seconds: 120  # 增加超时时间
```

---

## 故障排查

### 问题1: 缺失必填字段

**错误信息**:
```
[ERROR] 缺失必填字段: patient_name
建议: 检查Excel文件是否包含"患者姓名"列
```

**解决**:
1. 检查Excel文件确实包含该字段
2. 检查字段名是否在`mapping.yaml`的同义词列表中
3. 如需添加同义词，编辑配置文件

### 问题2: 模板占位符未替换

**现象**: 生成的报告中仍显示`{{ variable_name }}`

**原因**: 映射配置中缺少该变量定义

**解决**:
1. 查看日志确定缺失的变量名
2. 在`mapping.yaml`中添加该变量的映射
3. 或在模板中删除该占位符

### 问题3: 日期格式错误

**错误信息**:
```
[WARNING] 日期格式无法识别: 2025/10/24
```

**解决**:
系统会自动尝试多种日期格式，如仍失败：
1. 在Excel中手动统一日期格式为`YYYY-MM-DD`
2. 或在`mapping.yaml`中调整日期格式配置

### 问题4: 批量处理部分失败

**现象**: 50个样本处理了45个成功，5个失败

**解决**:
1. 查看汇总报告`summary.json`中的`failed_samples`
2. 根据错误信息逐个修复
3. 使用`--continue-on-error`继续处理成功的样本

### 问题5: 文件权限错误

**错误信息**:
```
[ERROR] 无法写入输出目录: /data/output/
```

**解决**:
```bash
# Linux
chmod 755 data/output/

# 或更改输出目录
reportgen generate --excel data.xlsx --output ~/reports/
```

---

## 高级功能

### 自定义日志级别

```bash
# 详细调试信息
reportgen generate --excel data.xlsx --verbose

# 或编辑settings.yaml
logging:
  level: "DEBUG"
```

### 生成质量报告

```bash
# 启用质量检查并生成报告
# 在settings.yaml中配置
quality:
  enabled: true
  report:
    generate: true
```

### 性能监控

```bash
# 查看性能指标
# 日志中自动记录处理时间、内存使用等
tail -f data/logs/reportgen_*.log
```

### 自动化脚本示例

**每日批量处理脚本** (`daily_batch.sh`):
```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d)
INPUT_DIR="/path/to/input/"
OUTPUT_DIR="/path/to/output/$DATE/"

mkdir -p "$OUTPUT_DIR"

reportgen batch \
  --excel "$INPUT_DIR/*.xlsx" \
  --output "$OUTPUT_DIR" \
  --summary "$OUTPUT_DIR/summary.json" \
  --log "$OUTPUT_DIR/batch.log" \
  --continue-on-error

# 发送通知
if [ $? -eq 0 ]; then
  echo "批量处理完成" | mail -s "报告生成通知" admin@example.com
fi
```

---

## 最佳实践

### 1. 组织Excel文件

```
data/input/
├── 2025-10/
│   ├── batch_001.xlsx
│   ├── batch_002.xlsx
│   └── ...
└── 2025-11/
```

### 2. 备份配置文件

```bash
# 定期备份配置
cp config/mapping.yaml config/mapping.yaml.backup
```

### 3. 版本控制

```bash
# 将配置文件纳入版本控制
git add config/*.yaml
git commit -m "更新字段映射配置"
```

### 4. 日志管理

```bash
# 定期清理旧日志（保留最近30天）
find data/logs/ -name "*.log" -mtime +30 -delete
```

### 5. 模板管理

- 每个模板使用语义化版本（如`template_v1.0.0.docx`）
- 在模板文件中添加版本号标识
- 重大模板变更时更新`project_types.yaml`

---

## 性能参考

**硬件环境**: Intel Core i5, 8GB RAM, SSD

| 操作 | 数据量 | 预期时间 |
|------|--------|---------|
| Excel解析 | 2MB文件 | < 3秒 |
| 单个报告生成 | 标准模板 | < 8秒 |
| 批量处理 | 10个样本 | < 1分钟 |
| 批量处理 | 50个样本 | < 5分钟 |

---

## 获取帮助

### 查看文档

```bash
# CLI帮助
reportgen --help
reportgen generate --help

# 查看完整文档
cat README.md
```

### 检查系统状态

```bash
# 验证配置
reportgen validate all

# 列出模板
reportgen template list

# 查看版本
reportgen --version
```

### 常见命令速查

```bash
# 生成单个报告
reportgen generate -e <excel> -o <output>

# 批量处理
reportgen batch -e "<pattern>" -o <output>

# 验证配置
reportgen validate config

# 初始化项目
reportgen init

# 提取模板
reportgen template extract --source <docx> --output <output>
```

---

## 下一步

完成快速开始后，您可以：

1. ✅ 阅读完整的CLI接口文档：`contracts/cli-interface.md`
2. ✅ 了解数据模型定义：`data-model.md`
3. ✅ 深入配置schema：`contracts/mapping-schema.yaml`, `contracts/config-schema.yaml`
4. ✅ 查看技术研究文档：`research.md`
5. ✅ 开始实现开发（参考`plan.md`）

---

**祝您使用愉快！如有问题，请查看故障排查部分或联系技术支持。**

