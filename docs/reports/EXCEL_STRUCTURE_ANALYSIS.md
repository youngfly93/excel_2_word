# 📊 Excel文件结构完整分析

**文件名**: data/input/MLF2509307001T_MLB2509307001.result.xlsx  
**分析日期**: 2025-10-24  
**目的**: Week 1 - 为映射配置提供精确的字段信息

---

## 📋 一、Sheet概览

| # | Sheet名称 | 行数 | 列数 | 用途 | 重要性 |
|---|----------|------|------|------|--------|
| 1 | **QC** | 46 | 13 | 质控数据 | ⭐⭐ |
| 2 | **Variations** | 131 | 53 | 体细胞变异明细 | ⭐⭐⭐⭐⭐ |
| 3 | **Hereditary_tumor** | 102 | 72 | 遗传性肿瘤变异 | ⭐⭐⭐⭐ |
| 4 | **CtDrug** | 1100 | 8 | 化疗药物基因型 | ⭐⭐⭐ |
| 5 | **Hotspot** | 163 | 14 | 热点位点检测 | ⭐⭐⭐ |
| 6 | **Cnv** | 2 | 15 | 拷贝数变异 | ⭐⭐ |
| 7 | **Fusion** | 4 | 18 | 基因融合 | ⭐⭐ |
| 8 | **Msisensor** | 21 | 32 | MSI检测结果 | ⭐⭐⭐⭐⭐ |
| 9 | **HLA** | 13 | 6 | HLA分型 | ⭐⭐ |
| 10 | **TMB** | 18 | 4 | TMB值计算 | ⭐⭐⭐⭐⭐ |
| 11 | **Ct1000** | 149 | 14 | 化疗药物详细 | ⭐⭐ |
| 12 | **Ct15** | ? | ? | 化疗药物简化 | ⭐⭐ |

---

## 🔍 二、关键Sheet详细分析

### 2.1 QC Sheet (质控数据)

**用途**: 测序质控指标  
**关键字段**:

```
列名                    类型      非空率    说明
────────────────────────────────────────────────
Sample                 object    52%      样本名称或质控项目名
case                   object    48%      病例样本值
control                object    48%      对照样本值
Quality                object    13%      质控指标名称
Value                  object    13%      质控指标值
```

**关键数据示例**:
- 行1: "Initial bases on target" = 1249816
- 行2: "Average sequencing depth on target" = 907.96

**映射建议**:
- 需要从特定行提取质控数据（如测序深度、覆盖度等）
- 不能用第一行，需要智能查找关键字

---

### 2.2 Variations Sheet (体细胞变异) ⭐⭐⭐⭐⭐

**用途**: 最重要！包含所有体细胞变异数据，对应报告中的"基因变异明细表"

**列数**: 53列  
**数据行数**: 129行（去除表头）

**核心字段映射**:

| Excel列名 | 映射变量名 | 类型 | 说明 |
|-----------|-----------|------|------|
| `Gene_Symbol` | `gene` | string | 基因名称 ✓ |
| `cHGVS` | `variant` | string | cDNA变异 ✓ |
| `pHGVS_S` | `protein` | string | 蛋白质变异(短) ✓ |
| `pHGVS_A` | `protein_full` | string | 蛋白质变异(完整) |
| `Function` | `variant_type` | string | 变异类型 ✓ |
| `Freq(%)` | `af` | float | 变异频率 ✓ |
| `ExIn_ID` | `exon` | string | 外显子编号 ✓ |
| `Tumor_Reads1` | `ref_reads` | int | 参考碱基读数 |
| `Tumor_Reads2` | `alt_reads` | int | 变异碱基读数 |
| `Chr` | `chromosome` | string | 染色体 |
| `Start` | `position` | int | 起始位置 |
| `MType` | `mutation_type` | string | 突变类型 (SNV/Indel) |
| `COSMIC` | `cosmic_id` | string | COSMIC数据库ID |
| `CLNSIG` | `clinvar_sig` | string | ClinVar临床意义 |
| `Drug` | `related_drug` | string | 相关药物 ✓ |
| `Evidence_level` | `evidence_level` | string | 证据等级 ✓ |

**示例数据**:
```
基因: ARID1A
变异: c.3991C>T
蛋白质: p.Q1331*
类型: Nonsense
频率: 0.68%
外显子: EX16
```

**重要发现**:
- ✅ 这个sheet包含了报告"基因变异明细表"所需的所有数据
- ✅ 列名与我们的mapping基本匹配（需要微调）
- ⚠️ 变异频率列名是 `Freq(%)` 而不是 `AF` 或 `变异频率`

---

### 2.3 TMB Sheet (肿瘤突变负荷) ⭐⭐⭐⭐⭐

**用途**: TMB值计算，对应报告中的"TMB/MSI检测结果"

**关键数据位置**:
```
行号    列1                          列2                          列3
────────────────────────────────────────────────────────────────────
1      Var_num                     Bed_size(M,>=50X CDS...)    TMB
2      4                           0.528812408447266            7.56
```

**映射关键**:
- TMB值在第2行第3列
- 变异数量在第2行第1列
- 检测区域大小在第2行第2列

**映射建议**:
```yaml
tmb_value:
  sheet: "TMB"
  location: "row=2, col=3"  # 固定位置
  format: "{:.2f}"
```

---

### 2.4 Msisensor Sheet (MSI检测) ⭐⭐⭐⭐⭐

**用途**: MSI状态判定

**关键数据位置**:
```
行号    SOFT          Sites    Somatic_Sites    %        结果
────────────────────────────────────────────────────────────
1      msisensor     22       0                0        -
2      msisensor2    114      3                2.63     MSS
```

**MSI判定逻辑**:
- MSS (Microsatellite Stable): % < 20%
- MSI-L (Low): 20% ≤ % < 40%
- MSI-H (High): % ≥ 40%

**映射建议**:
```yaml
msi_status:
  sheet: "Msisensor"
  row: 2
  column: "Unnamed: 4"  # 或者读取%列并判定
```

---

### 2.5 CtDrug Sheet (化疗药物) ⭐⭐⭐

**用途**: 化疗药物基因型与用药提示

**列名** (中文!):
```
1. 药物
2. 检测基因
3. 检测位点
4. 基因型
5. 用药提示（仅供参考）
6. 等级
7. 用药详细描述
8. (空列)
```

**示例数据**:
```
药物: 顺铂（cisplatin）
检测基因: ABCB1
检测位点: rs10276036
基因型: CC
用药提示: 相比CT或TT基因型，药物敏感性可能较低
等级: 3
```

**映射挑战**:
- ⚠️ 列名是中文！
- ⚠️ 1100行数据，需要过滤和分组

---

### 2.6 Hereditary_tumor Sheet (遗传性肿瘤)

**用途**: 胚系变异，可能影响遗传性肿瘤风险

**关键字段**:
```
Gene_Symbol          基因名
cHGVS               cDNA变异
Function            功能影响
Pathogenic_grade    致病性等级 ⭐
CLNSIG              ClinVar临床意义
```

**示例**:
- 102行遗传变异数据
- 包含致病性评级和临床意义

---

## 📍 三、关键数据位置总结

### 3.1 患者基本信息 ❌

**问题**: Excel中**没有**患者基本信息！

以下字段在Excel中**找不到**:
- ❌ 患者姓名
- ❌ 样本编号 (文件名中有: MLF2509307001T_MLB2509307001)
- ❌ 性别
- ❌ 年龄
- ❌ 医院
- ❌ 报告日期

**解决方案**:
1. 从**文件名**提取样本编号
2. 患者信息可能在**另外的Excel文件**或**数据库**中
3. 或者需要**人工输入**补充

---

### 3.2 检测结果数据 ✅

| 数据项 | Sheet | 位置 | 状态 |
|--------|-------|------|------|
| TMB值 | TMB | row=2, col=3 | ✅ 明确 |
| MSI状态 | Msisensor | row=2, col=5 | ✅ 明确 |
| 变异数量 | Variations | count(rows) | ✅ 计算 |
| 基因列表 | Variations | col="Gene_Symbol" | ✅ 提取 |
| 化疗药物 | CtDrug | 全表 | ✅ 过滤 |

---

## 🔧 四、Mapping配置更新建议

### 4.1 需要添加的同义词

```yaml
# Variations sheet 的列名
gene:
  synonyms: 
    - "基因"
    - "Gene_Symbol"  # ✅ 新增
    
variant:
  synonyms:
    - "变异"
    - "cHGVS"  # ✅ 新增
    
protein:
  synonyms:
    - "蛋白质"
    - "pHGVS_S"  # ✅ 新增
    - "pHGVS_A"
    
af:
  synonyms:
    - "变异频率"
    - "Freq(%)"  # ✅ 新增 (注意括号)
    
variant_type:
  synonyms:
    - "变异类型"
    - "Function"  # ✅ 新增
```

### 4.2 表格数据映射

```yaml
table_data:
  variants:
    sheet_name: "Variations"  # ✅ 精确匹配
    required: true
    columns:
      gene:
        synonyms: ["Gene_Symbol", "基因"]
      variant:
        synonyms: ["cHGVS", "变异"]
      protein:
        synonyms: ["pHGVS_S", "蛋白质变异"]
      af:
        synonyms: ["Freq(%)", "变异频率"]
      exon:
        synonyms: ["ExIn_ID", "外显子"]
      variant_type:
        synonyms: ["Function", "变异类型"]
      drug:
        synonyms: ["Drug", "相关药物"]
```

### 4.3 特殊数据提取

```yaml
# TMB值 - 需要从固定位置读取
tmb_value:
  sheet: "TMB"
  extraction_type: "fixed_position"
  row: 2
  column: 3  # 第3列
  
# MSI状态 - 需要从固定位置读取
msi_status:
  sheet: "Msisensor"
  extraction_type: "fixed_position"
  row: 2
  column: 5  # 或者读取%值并判定
```

---

## ⚠️ 五、发现的问题与挑战

### 5.1 患者信息缺失 ❌

**问题**: Excel中完全没有患者基本信息

**影响**: 
- 报告第一页无法填充
- 需要额外的数据源

**解决方案**:
1. **短期**: 从文件名提取样本编号，其他字段标记为"待补充"
2. **中期**: 寻找包含患者信息的其他文件
3. **长期**: 建立患者信息数据库，通过样本编号关联

### 5.2 数据分散在多个Sheet ⚠️

**问题**: 
- 变异数据在 Variations
- TMB在 TMB sheet
- MSI在 Msisensor sheet
- 化疗药物在 CtDrug sheet

**解决方案**: 需要实现**多sheet数据整合**逻辑

### 5.3 中文列名 ⚠️

**位置**: CtDrug sheet使用中文列名

**影响**: 映射配置需要支持中文同义词

**解决方案**: 
```yaml
drug_name:
  synonyms: ["药物", "Drug"]
gene:
  synonyms: ["检测基因", "Gene"]
```

### 5.4 数据位置不固定 ⚠️

**问题**: 
- QC数据：质控指标分散在不同行，需要按内容查找
- TMB/MSI：固定在第2行，但需要特殊处理

**解决方案**: 实现两种提取模式:
1. **表格模式**: 遍历所有行（Variations, CtDrug等）
2. **键值模式**: 按关键字查找（QC, TMB, MSI等）

---

## 📊 六、优先级数据映射计划

### 优先级1 (本周完成) - 核心检测结果

1. ✅ **Variations表** → 基因变异明细表
   - 129行变异数据
   - 映射到报告表格

2. ✅ **TMB值** → TMB/MSI结果
   - 从TMB sheet第2行第3列提取

3. ✅ **MSI状态** → TMB/MSI结果
   - 从Msisensor sheet第2行提取

### 优先级2 (下周) - 药物提示

4. ⏳ **CtDrug表** → 化疗药物表格
   - 1100行数据需要过滤

5. ⏳ **Drug列** (Variations) → 靶向药物提示
   - 从变异表提取相关药物

### 优先级3 (后续) - 补充信息

6. ⏳ **Hereditary_tumor** → 遗传变异表
7. ⏳ **Cnv/Fusion** → CNV和融合基因

---

## 🎯 七、下一步行动

### ✅ 立即完成 (今天)

1. **更新mapping.yaml**
   - 添加 `Gene_Symbol`, `cHGVS`, `Freq(%)` 等同义词
   - 更新 variants 表的 sheet_name 为 "Variations"
   - 添加中文列名支持

2. **实现样本编号提取**
   - 从文件名提取: `MLF2509307001T_MLB2509307001`
   - 更新 ExcelReader 添加文件名解析

3. **实现固定位置数据提取**
   - 为TMB值实现 get_cell_value(sheet, row, col)
   - 为MSI状态实现类似逻辑

### 📅 本周计划

4. **测试Variations表映射**
   - 验证129行数据都能正确提取
   - 确认列名匹配正确

5. **创建最小可用模板**
   - 包含: 基本信息 + 变异明细表 + TMB/MSI结果
   - 先不追求完美，能用就行

6. **生成第一份可用报告**
   - 数据完整性: ≥60%（有变异数据即可）
   - 与真实报告对比关键字段

---

## 📈 八、预期改进效果

### 当前状态
- ❌ 数据完整性: 36% (11个字段中4个有值)
- ❌ 变异数据: 0行
- ❌ TMB/MSI: 空

### Week 1 目标
- ✅ 数据完整性: ≥60% (核心检测数据全覆盖)
- ✅ 变异数据: 129行 (与Excel一致)
- ✅ TMB值: 7.56 Muts/Mb
- ✅ MSI状态: MSS

### 成功标准
1. 报告中能显示129行变异数据 ✓
2. TMB值正确: 7.56 ✓
3. MSI状态正确: MSS ✓
4. 样本编号从文件名提取成功 ✓

---

**文档版本**: 1.0  
**最后更新**: 2025-10-24  
**下次更新**: 完成mapping.yaml更新后

