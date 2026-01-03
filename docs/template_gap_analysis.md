# 模板变量差距分析

## 当前模板: jinja2_template_358_v8.docx

### 已实现的变量 (31个)

| 变量名 | 位置 | 状态 |
|--------|------|------|
| `{{ patient_name }}` | 封面、致信、患者信息表 | ✅ 已实现 |
| `{{ report_number }}` | 封面 | ✅ 已实现 |
| `{{ gender }}` | 患者信息表 | ✅ 已实现 |
| `{{ age }}` | 患者信息表 | ✅ 已实现 |
| `{{ cancer_type }}` | 患者信息表 | ✅ 已实现 |
| `{{ sample_date }}` | 患者信息表 | ✅ 已实现 (v7新增) |
| `{{ report_date }}` | 患者信息表 | ✅ 已实现 (v7新增) |
| `{{ sample_id }}` | 患者信息表 | ✅ 已实现 (v7新增) |
| `{{ sample_type }}` | 患者信息表、检测内容 | ✅ 已实现 (v7新增) |
| `{{ tmb_value }}` | 免疫治疗表 | ✅ 已实现 |
| `{{ tmb_status }}` | 免疫治疗表 | ✅ 已实现 |
| `{{ tmb_reference }}` | 免疫治疗表 | ✅ 已实现 |
| `{{ msi_status_cn }}` | 免疫治疗表 | ✅ 已实现 |
| `{%tr for row in variants %}` | 靶向药物用药提示表 | ✅ 已实现 (v7修复为行级循环) |
| `{%tr for row in summary_variants %}` | 基因变异检测结果表 | ✅ 已实现 (v7修复为行级循环) |
| `{%tr for gene in undetected_genes %}` | 未检出基因表 | ✅ 已实现 (v7修复为行级循环) |

**v6/v7 更新内容:**
- 修复表格循环: `{% for %}` → `{%tr for %}` (行级循环)
- 删除硬编码行: SETD2, ATM
- 添加基本信息变量: sample_date, report_date, sample_id, sample_type

**v8 新增变量 (5个):**
| `{{ immune_positive_count }}` | 免疫治疗表-正相关基因数量 | ✅ 已实现 (v8新增) |
| `{{ immune_negative_result }}` | 免疫治疗表-负相关基因结果 | ✅ 已实现 (v8新增) |
| `{{ immune_hyperprogression_result }}` | 免疫治疗表-超进展基因结果 | ✅ 已实现 (v8新增) |
| `{{ total_variants_count }}` | 统计-总变异数 | ✅ 已实现 (v8新增) |
| `{{ drug_related_count }}` | 统计-药物相关变异数 | ✅ 已实现 (v8新增) |

---

### 缺失的变量 (需要添加)

#### 1. 基本信息字段 ✅ 已完成 (v7)

| 应添加变量 | 当前硬编码值 | 来源Excel列 | 状态 |
|-----------|-------------|-------------|------|
| `{{ sample_date }}` | 20251121 | 送检日期 | ✅ 已实现 |
| `{{ report_date }}` | 20251204 | 报告日期 | ✅ 已实现 |
| `{{ sample_type }}` | 组织 | 样本类型 | ✅ 已实现 |
| `{{ sample_id }}` | LZ258792 | 项目编码/样本编号 | ✅ 已实现 |
| `{{ project_name }}` | 结直肠癌358基因+MSI | 项目名称 | 待添加 |
| `{{ sampling_method }}` | - | 取材手段 | 待添加 |
| `{{ sampling_site }}` | - | 取材部位 | 待添加 |

#### 2. 免疫治疗表格 ✅ 部分完成 (v8)

**已完成:**
- 免疫正相关基因数量: `{{ immune_positive_count }}`
- 免疫负相关基因结果: `{{ immune_negative_result }}`
- 免疫超进展相关基因结果: `{{ immune_hyperprogression_result }}`

**待完成 (需在数据层处理):**
| 位置 | 说明 |
|------|------|
| 免疫正相关基因变异列表 | TP53/KRAS/ATM 等变异详情需在 `immune_positive_result` 变量中动态生成 |

#### 3. 靶向药物用药提示表 ✅ 已完成 (v6/v7)

**已修复内容:**
- 循环改为行级别: `{%tr for row in variants %}...{%tr endfor %}`
- 删除了硬编码的 SETD2、ATM 行

```
新结构 (v7):
┌─────────────────┐
│ {%tr for row in variants %}  │
│ {{ row.gene }} ...           │  ← 循环生成所有行
│ {%tr endfor %}               │
└─────────────────┘
```

#### 4. 基因诊疗知识部分 (第三部分)

**当前问题**: 整个"基因变异解析"章节全部是硬编码的

| 当前硬编码 | 应改为 |
|-----------|--------|
| TP53：c.844C>T，p.R282W；67.29% | `{% for section in gene_knowledge_sections %}` |
| (TP53基因简介...) | `{{ section.intro }}` |
| (该样本检出TP53基因...) | `{{ section.mutation_desc }}` |
| KRAS：c.34G>A，p.G12S；46.29% | (继续循环) |
| ... | ... |

**建议的模板结构**:
```jinja2
{% for section in gene_knowledge_sections %}
◆ {{ section.header }}

{{ section.intro }}

{{ section.mutation_desc }}

{{ section.mutation_analysis }}

{% endfor %}
```

#### 5. 其他检测汇总部分

| 位置 | 当前状态 | 应添加 |
|------|---------|--------|
| 本次共检出体细胞变异：8个 | 硬编码 | `{{ total_variants_count }}` |
| 与靶向药物用药相关的变异有：4个 | 硬编码 | `{{ drug_related_variants_count }}` |
| 检出有害变异时可能疗效较好（免疫正相关）| 硬编码基因列表 | 动态循环 |

#### 6. 用药提示解析部分

**当前问题**: 药物疗效临床解析部分全部硬编码

需要添加:
```jinja2
{% for drug in drug_analysis_sections %}
◆ {{ drug.drug_name }}
{{ drug.clinical_analysis }}
{% endfor %}
```

---

### 优先级建议

#### 高优先级 (P0) - 全部完成
1. ✅ 添加基本信息变量: `sample_date`, `report_date`, `sample_type`, `sample_id` (已完成 v7)
2. ✅ 删除硬编码的 SETD2、ATM 行 (已完成 v6)
3. ✅ 修复免疫相关基因的动态显示 (已完成 v8)
   - `{{ immune_positive_count }}` - 正相关基因数量
   - `{{ immune_negative_result }}` - 负相关基因结果
   - `{{ immune_hyperprogression_result }}` - 超进展基因结果

#### 中优先级 (P1) - 全部完成
4. ✅ 添加基因诊疗知识的循环生成 (数据层已实现)
   - `GeneKnowledgeProvider.build_all_gene_knowledge_sections()` 生成完整章节
   - 包含: header, intro, mutation_desc, mutation_analysis, drug_info
5. ✅ 添加统计数字的动态计算 (数据层已实现)
   - `total_variants_count` - 总变异数
   - `drug_related_count` - 药物相关变异数

#### 低优先级 (P2) - 全部完成
6. ✅ 添加用药提示解析的动态生成 (数据层已实现)
   - `drug_analysis_sections`: 包含完整药物分析信息
   - 数据来源: `2025.12.10/示例：+++自建肠癌基因数据库.xlsx` - 用药提示解析sheet
7. ✅ 添加参考文献的动态生成 (数据层已实现)
   - `references`: 扁平化参考文献列表
   - `references_by_gene`: 按基因分组的参考文献
   - 数据来源: `2025.12.10/示例：+++自建肠癌基因数据库.xlsx` - 参考文献sheet

---

### 结构复杂部分的处理建议

以下部分由于Word文档XML结构复杂，建议在数据层（Python代码）生成完整内容后填充：

1. **免疫正相关基因变异列表** ✅ 已完成
   - `immune_positive_result`: 完整显示文本，格式为 "检出（N个）\nGENE1：cHGVS，pHGVS\n..."
   - `immune_positive_genes`: 仅基因列表，格式为 "GENE1：cHGVS，pHGVS\nGENE2：..."
   - `immune_positive_count`: 正相关基因数量（整数）

2. **免疫负相关/超进展基因** ✅ 已完成
   - `immune_negative_result`: "未检出" 或 "检出：GENE1：cHGVS，pHGVS；..."
   - `immune_hyperprogression_result`: "未检出" 或 "检出：GENE1：cHGVS，pHGVS；..."

3. **统计字段** ✅ 已完成
   - `total_variants_count`: 总变异数（含Ⅰ/Ⅱ/Ⅲ类）
   - `drug_related_count`: 药物相关变异数

4. **基因诊疗知识章节** ✅ 已完成
   - 使用 `gene_knowledge_sections` 列表
   - 由 `GeneKnowledgeProvider.build_all_gene_knowledge_sections()` 生成
   - 每个元素包含: header, intro, mutation_desc, mutation_analysis, drug_info

5. **用药提示解析章节** ✅ 已完成
   - 使用 `drug_analysis_sections` 列表
   - 由 `GeneKnowledgeProvider.build_drug_analysis_sections()` 生成
   - 每个元素包含: gene, drug_name, drug_type, drug_type_cn, relation, clinical

6. **参考文献** ✅ 已完成
   - `references`: 扁平化参考文献列表（字符串列表，已去重）
   - `references_by_gene`: 按基因分组的参考文献列表
   - 由 `GeneKnowledgeProvider.build_references()` 和 `build_all_references_flat()` 生成

---

### 新模板变量清单

```yaml
# 基本信息
patient_name: 患者姓名
gender: 性别
age: 年龄
cancer_type: 临床诊断
sample_id: 项目编码/样本编号
sample_type: 样本类型
sample_date: 送检日期
report_date: 报告日期
report_number: 报告编号
project_name: 项目名称
sampling_method: 取材手段
sampling_site: 取材部位

# MSI/TMB
msi_status: MSI状态 (MSS/MSI-H/MSI-L)
msi_status_cn: MSI状态中文描述
tmb_value: TMB值
tmb_status: TMB状态 (H/L)
tmb_reference: TMB参考值

# 统计
total_variants_count: 总变异数（含Ⅰ/Ⅱ/Ⅲ类）
drug_related_count: 药物相关变异数

# 免疫相关字符串字段（v8数据层生成）
immune_positive_count: 正相关基因数量（整数）
immune_positive_result: 正相关基因完整显示文本 ("检出（N个）\nGENE1：cHGVS，pHGVS\n...")
immune_positive_genes: 正相关基因列表（不含前缀）
immune_negative_result: 负相关基因结果 ("未检出" 或 "检出：GENE1：...")
immune_hyperprogression_result: 超进展基因结果 ("未检出" 或 "检出：GENE1：...")

# 表格数据
variants: 主表变异列表 (Ⅰ类+Ⅱ类)
summary_variants: 汇总表变异列表 (含Ⅲ类)
undetected_genes: 未检出基因列表
immune_positive_variants: 免疫正相关变异（表格数据）
immune_negative_variants: 免疫负相关变异（表格数据）
immune_hyperprogression_variants: 免疫超进展变异（表格数据）
gene_knowledge_sections: 基因诊疗知识章节（每个元素含 header, intro, mutation_desc, mutation_analysis）
drug_analysis_sections: 用药提示解析章节（每个元素含 gene, drug_name, drug_type, relation, clinical）
references: 扁平化参考文献列表（字符串列表，已去重）
references_by_gene: 按基因分组的参考文献（每个元素含 gene, references）
```
