# Excel字段到报告映射表

**快速参考文档**
**生成时间**: 2025-11-17

---

## 📊 单值字段映射

| 报告字段 | Excel来源 | 提取方法 | 示例值 |
|---------|----------|---------|--------|
| **患者姓名** | config/patient_info.yaml | 通过sample_id查询 | 张三 |
| **性别** | config/patient_info.yaml | 通过sample_id查询 | 男 |
| **年龄** | config/patient_info.yaml | 通过sample_id查询 | 45 |
| **样本编号** | Excel文件名 | 正则提取：MLB\d+ | MLB2509307001 |
| **样本类型** | config/patient_info.yaml | 通过sample_id查询 | 组织 |
| **TMB值** | TMB Sheet, 行4, 列2 | 直接读取 | 7.56 |
| **TMB单位** | 固定值 | 常量 | Muts/Mb |
| **MSI状态** | Msisensor Sheet, 行1, 列4 | %<20=MSS, 20-40=MSI-L, >40=MSI-H | MSS |
| **MSI百分比** | Msisensor Sheet, 行1, 列4 | 直接读取 | 2.63% |
| **报告日期** | 自动生成 | datetime.now() | 2025-11-17 |

---

## 📋 表格数据映射

### 表格2: 基因变异简表（靶向用药）

**Excel来源**: Variations Sheet
**行数**: 122行（过滤后约7-8行）
**过滤条件**: 有靶向药物关联的变异

| 报告列 | Excel列 | 列位置 | 数据类型 | 说明 |
|-------|---------|--------|---------|------|
| 基因 | Gene_Symbol | C | string | 基因名称 |
| 突变位点 | cHGVS | E | string | 变异位点（cDNA层面）|
| 潜在获益靶向药物 | (需关联CtDrug) | - | string | 从CtDrug表查询 |
| 可能耐药或慎重药物 | (需关联CtDrug) | - | string | 从CtDrug表查询 |

### 表格4: 基因变异详表（全部变异）

**Excel来源**: Variations Sheet
**行数**: 122行（过滤后约27-28行）
**过滤条件**: 频率>5% 且 临床显著

| 报告列 | Excel列 | 列位置 | 数据类型 | 格式化 |
|-------|---------|--------|---------|--------|
| 基因名称 | Gene_Symbol | C | string | - |
| cDNA变异 | cHGVS | E | string | - |
| 蛋白变异 | pHGVS_S / pHGVS_A | F / G | string | 优先pHGVS_S |
| 变异类型 | Function | H | string | - |
| 变异丰度 | Freq(%) | 某列 | float | 保留2位小数 |
| 测序深度 | Total_depth | 某列 | int | - |
| 功能影响 | ExonFunc | 某列 | string | - |
| 人群频率 | PopFreqMax | 某列 | float | 科学计数法 |
| 临床意义 | Clinvar | 某列 | string | - |

### 表格5: 化疗药物汇总表

**Excel来源**: CtDrug Sheet
**行数**: 1100行（过滤后约7-8行）
**过滤条件**: 患者检出相关基因突变的药物

| 报告列 | Excel列 | 列位置 | 数据类型 | 说明 |
|-------|---------|--------|---------|------|
| 药物名称 | 药物 | A | string | 中英文名称 |
| 相关基因 | 检测基因 | B | string | 基因名称 |
| 药物适应情况 | 用药提示 / 基因型 | E / D | string | 合并显示 |

### 表格11-44: 化疗药物详细解析表（❌ 当前缺失）

**Excel来源**: CtDrug Sheet
**数量**: 34个表格，每个药物一个
**过滤条件**: 按药物名称分组

| 报告列 | Excel列 | 列位置 | 数据类型 | 说明 |
|-------|---------|--------|---------|------|
| 药物名称 | 药物 | A | string | 表格标题 |
| 基因 | 检测基因 | B | string | - |
| 检测位点 | 检测位点 | C | string | SNP位点 |
| 基因型 | 基因型 | D | string | 杂合/纯合 |
| 等级 | 等级 | F | string | 证据等级 |
| 检测结果 | 用药提示 | E | string | - |
| 参考文献 | 参考文献 | G | string | PMID |

### 表格6: 检测基因列表

**Excel来源**: Variations Sheet + 固定基因列表
**行数**: 33行（固定）

| 报告列 | 数据来源 | 说明 |
|-------|---------|------|
| 检测基因 | 固定列表（358基因） | EGFR, KRAS, NRAS等 |
| 检测内容 | 固定值 | 外显子18/19/20/21 |
| 检测结果 | 从Variations查询 | 未检出 / 检出变异 |

---

## 🔗 特殊字段提取代码

### TMB值提取

```python
import pandas as pd

# 读取TMB Sheet
tmb_df = pd.read_excel('xxx.xlsx', sheet_name='TMB')

# 提取TMB值（第4行，第2列）
tmb_value = float(tmb_df.iloc[3, 1])
# 结果: 7.56
```

### MSI状态计算

```python
# 读取Msisensor Sheet
msi_df = pd.read_excel('xxx.xlsx', sheet_name='Msisensor')

# 提取MSI百分比（第1行，第4列）
msi_percentage_str = str(msi_df.iloc[0, 3])
msi_percentage = float(msi_percentage_str.rstrip('%'))

# 计算MSI状态
if msi_percentage < 20:
    msi_status = 'MSS'
elif msi_percentage < 40:
    msi_status = 'MSI-L'
else:
    msi_status = 'MSI-H'

# 结果: MSS (2.63%)
```

### 样本编号提取

```python
import re

filename = "data/input/MLF2509307001T_MLB2509307001.result.xlsx"

# 提取MLB开头的编号
match = re.search(r'MLB\d+', filename)
sample_id = match.group(0) if match else None

# 结果: MLB2509307001
```

### 患者信息查询

```python
import yaml

# 加载患者信息库
with open('config/patient_info.yaml', 'r', encoding='utf-8') as f:
    patient_info = yaml.safe_load(f)

# 通过样本编号查询
sample_id = "MLB2509307001"
if sample_id in patient_info:
    patient_data = patient_info[sample_id]
    patient_name = patient_data.get('patient_name')
    gender = patient_data.get('gender')
    age = patient_data.get('age')
    # 等等...
```

---

## 🚫 未使用的Excel数据

以下Sheet包含数据但当前未被报告使用：

| Sheet | 行数 | 列数 | 潜在用途 | 优先级 |
|-------|------|------|---------|--------|
| **Cnv** | 2 | 15 | 拷贝数变异 | P1 高 |
| **Fusion** | 4 | 18 | 基因融合 | P1 高 |
| **HLA** | 13 | 6 | HLA分型 | P1 高 |
| QC | 46 | 13 | 质量控制 | P2 中 |
| Hereditary_tumor | 102 | 72 | 遗传性肿瘤 | P2 中 |
| Hotspot | 163 | 14 | 热点变异 | P3 低 |
| Ct1000 | 149 | 14 | 药物代谢详细 | P3 低 |
| Ct15 | 4 | 11 | 药物代谢详细 | P3 低 |

**建议**: 优先添加CNV、Fusion、HLA数据到报告中，可显著提升报告完整性。

---

## ⚙️ 数据过滤逻辑

### 变异数据过滤（表格2、表格4）

**当前逻辑**:
```python
# 包含所有变异（122个）
variants = all_variants
```

**建议逻辑**:
```python
# 仅包含临床显著变异
variants = df[
    (df['Freq(%)'] > 5) &  # 频率 > 5%
    (
        df['Clinvar'].isin(['Pathogenic', 'Likely pathogenic']) |
        df['has_drug_association'] |
        df['Function'].isin(['Nonsense', 'Frameshift'])
    )
]
```

### 化疗药物过滤（表格5）

**当前逻辑**:
```python
# 所有药物（1100行）
drugs = all_drug_gene_combinations
```

**建议逻辑**:
```python
# 仅患者检出基因相关的药物
patient_genes = set(variants_df['Gene_Symbol'])
drugs = ctdrug_df[ctdrug_df['检测基因'].isin(patient_genes)]
```

---

## 📝 配置文件位置

| 配置类型 | 文件路径 | 说明 |
|---------|---------|------|
| 字段映射 | config/mapping.yaml | 869行，定义所有字段映射规则 |
| 患者信息 | config/patient_info.yaml | 患者基本信息数据库 |
| 报告模板 | templates/aligned_template_final.docx | 7.38 MB完整模板 |

---

## 🎯 快速参考

### 报告生成命令

```bash
# 单个报告
python3 scripts/generate_report.py data/input/MLF2509307001T_MLB2509307001.result.xlsx

# 批量生成
python3 scripts/batch_generate_reports.py
```

### 验证映射关系

```bash
# 分析Excel结构
python3 analyze_excel_source.py xxx.xlsx

# 分析报告结构
python3 analyze_generated_report.py xxx.docx
```

---

**最后更新**: 2025-11-17
**相关文档**: GRANULAR_ALIGNMENT_REPORT.md
