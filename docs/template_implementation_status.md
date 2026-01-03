# Jinja2 Template Implementation Status

## Completed Implementations

### 1. Main Variant Table Loop (lines 7588-7857)
- **Loop**: `{% for row in variants %}...{% endfor %}`
- **Variables**: `row.gene`, `row.transcript`, `row.chromosome`, `row.exon`, `row.cHGVS`, `row.pHGVS`, `row.mutation_type`, `row.frequency`, `row.gene_class`, `row.clinical_significance`, `row.benefit_drugs`, `row.caution_drugs`

### 2. Summary Variant Table Loop (lines 11478-11972)
- **Loop**: `{% for row in summary_variants %}...{% endfor %}`
- **Variables**: `row.gene`, `row.transcript`, `row.chromosome`, `row.exon`, `row.cHGVS`, `row.pHGVS`, `row.mutation_type`, `row.frequency`

### 3. Undetected Genes Loop (lines 12033-12359)
- **Loop**: `{% for gene in undetected_genes %}...{% endfor %}`
- **Variables**: `gene.name`, `gene.transcript`, `gene.chromosome`

## Sections Analyzed - Implementation Notes

### 4. Targeted Drug Table (lines 12550-14467)
- **Status**: Static reference data
- **Recommendation**: Keep as-is, no templating needed
- **Reason**: This is a fixed list of FDA/NMPA approved drugs for colorectal cancer

### 5. Immune Gene Tables (I类/II类)
- **Status**: Static reference data filtered by data layer
- **Recommendation**: Keep as-is, filtering done at data preparation
- **Reason**: The template shows all immune genes; data layer filters which ones have variants

### 6. CNV/Fusion Detection Table (lines 15700-17700)
- **Status**: Static gene list with detection status - ANALYZED
- **Complexity**: MEDIUM - complex vMerge structure requires careful handling
- **Structure**:
  - Column 1: Gene name (with vertical merge for multi-row genes)
  - Column 2: Detection type (融合/扩增/突变/外显子X)
  - Column 3: Result (未检出 or detected value)

- **Detailed Gene/Detection Mapping**:
  | Gene | Detection Type | Variable Name |
  |------|---------------|---------------|
  | ALK | 融合 (fusion) | `cnv_ALK_fusion` |
  | ROS1 | 融合 (fusion) | `cnv_ROS1_fusion` |
  | RET | 融合 (fusion) | `cnv_RET_fusion` |
  | ERBB2 (HER2) | 突变 (mutation) | `cnv_ERBB2_mutation` |
  | ERBB2 (HER2) | 扩增 (amplification) | `cnv_ERBB2_amplification` |
  | PIK3CA | 外显子10 (exon10) | `cnv_PIK3CA_exon10` |
  | PIK3CA | 外显子21 (exon21) | `cnv_PIK3CA_exon21` |
  | MET | 外显子14跳跃 (exon14skip) | `cnv_MET_exon14skip` |
  | MET | 扩增 (amplification) | `cnv_MET_amplification` |
  | NRAS | 外显子2/3/4 | `cnv_NRAS_exon2/3/4` |
  | KRAS | 外显子2/3/4 | `cnv_KRAS_exon2/3/4` |
  | BRAF | 外显子11/15 | `cnv_BRAF_exon11/15` |

- **vMerge Complexity**: Genes with multiple detection types use vertical cell merge
  - First row: `<w:vMerge w:val="restart"/>` - starts merge
  - Subsequent rows: `<w:vMerge w:val="continue"/>` - continues merge

- **Recommendation**: Keep static structure, replace result values with variables
- **Implementation**: Deferred to data layer phase

- **Data Layer Interface**:
  ```python
  cnv_fusion_results = {
      "cnv_ALK_fusion": "未检出",  # or "检出" with details
      "cnv_ROS1_fusion": "未检出",
      "cnv_RET_fusion": "未检出",
      "cnv_ERBB2_mutation": "未检出",
      "cnv_ERBB2_amplification": "未检出",
      "cnv_PIK3CA_exon10": "未检出",
      "cnv_PIK3CA_exon21": "未检出",
      "cnv_MET_exon14skip": "未检出",
      "cnv_MET_amplification": "未检出",
      "cnv_NRAS_exon2": "未检出",
      "cnv_NRAS_exon3": "未检出",
      "cnv_NRAS_exon4": "未检出",
      "cnv_KRAS_exon2": "未检出",
      "cnv_KRAS_exon3": "未检出",
      "cnv_KRAS_exon4": "未检出",
      "cnv_BRAF_exon11": "未检出",
      "cnv_BRAF_exon15": "未检出",
  }
  ```

### 7. Gene Diagnostic Knowledge Sections (lines 28170-31000+)
- **Status**: Complex - requires data layer support
- **Structure per gene**:
  1. Gene header: `TP53：c.844C>T，p.R282W；67.29%` (dynamic)
  2. 基因简介 (Gene introduction) - static per gene per cancer type
  3. 基因变异说明 (Mutation description) - dynamic, based on detected mutation
  4. 基因变异解析 (Mutation analysis) - semi-static, collected from database
  5. 药物疗效临床解析 (Drug efficacy) - for genes with drug associations

- **Implementation Options**:

  **Option A: Loop with pre-rendered content**
  ```python
  gene_knowledge_sections = [
      {
          "header": "TP53：c.844C>T，p.R282W；67.29%",
          "header_color": "FF0000",  # red for Class I genes
          "intro": "TP53基因是重要的抑癌基因之一...",
          "mutation_desc": "该样本检出TP53基因c.844C>T，p.R282W错义突变...",
          "mutation_analysis": "TP53基因编码的蛋白p53全长393个氨基酸...",
          "drug_analysis": "一项临床I期研究评估了AZD1775..."
      },
      ...
  ]
  ```
  Template: `{% for section in gene_knowledge_sections %}...{% endfor %}`

  **Option B: Conditional includes per gene**
  ```jinja2
  {% if 'TP53' in detected_genes %}
  {{ TP53_header }}
  基因简介：
  {{ TP53_intro }}
  基因变异说明：
  {{ TP53_mutation_desc }}
  ...
  {% endif %}
  ```

- **Recommended Approach**: Option A with data layer preparing complete sections
- **Complexity**: HIGH - requires significant data layer work

### 8. General CRC Diagnostic Knowledge (line 42639+)
- **Status**: Static reference content
- **Recommendation**: Keep as-is
- **Reason**: General colorectal cancer information, same for all reports

## Data Structure Requirements

```python
context = {
    # Patient info
    "patient_name": str,
    "gender": str,
    "age": str,
    "sample_id": str,
    "pathological_diagnosis": str,
    "specimen_type": str,
    "report_date": str,
    "received_date": str,

    # Main variant table
    "variants": [
        {
            "gene": str,
            "transcript": str,
            "chromosome": str,
            "exon": str,
            "cHGVS": str,
            "pHGVS": str,
            "mutation_type": str,
            "frequency": str,
            "gene_class": str,  # Ⅰ类, Ⅱ类, Ⅲ类
            "clinical_significance": str,
            "benefit_drugs": str,
            "caution_drugs": str
        }
    ],

    # Summary variant table
    "summary_variants": [
        {
            "gene": str,
            "transcript": str,
            "chromosome": str,
            "exon": str,
            "cHGVS": str,
            "pHGVS": str,
            "mutation_type": str,
            "frequency": str,
            "benefit_drugs": str,
            "caution_drugs": str
        }
    ],

    # Undetected genes
    "undetected_genes": [
        {
            "name": str,
            "transcript": str,
            "chromosome": str
        }
    ],

    # Gene knowledge sections (for future implementation)
    "gene_knowledge_sections": [
        {
            "header": str,
            "header_color": str,  # FF0000 for red, 0000FF for blue
            "intro": str,
            "mutation_desc": str,
            "mutation_analysis": str,
            "drug_analysis": str  # optional
        }
    ]
}
```

## Template Files

- **v4 Template**: `templates/jinja2_template_358_v4.docx`
- **Test Script**: `scripts/test_template_v4.py`
- **Working Directory**: `/tmp/docx_template_358/word/document.xml`

## Next Steps

### Phase 1: Template Testing (Current)
1. ✅ CNV/Fusion table analyzed - deferred to data layer phase
2. 🔄 Test existing loops with real patient data from Excel
3. Validate template rendering with docxtpl

### Phase 2: Data Layer Implementation
4. Build Excel parser to extract variant data
5. Implement CNV/Fusion result variable replacements
6. Build gene knowledge sections data structure
7. Add HLA typing section (if applicable)

### Phase 3: Integration
8. Create end-to-end report generation pipeline
9. Validate output against reference reports
10. Handle edge cases (no variants, multiple cancers, etc.)

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `test_template_v4.py` | Test template with sample data |
| `add_undetected_genes_loop.py` | Added undetected genes loop |
| `add_cnv_fusion_variables.py` | CNV/Fusion table analysis |
| `implement_cnv_fusion_vars.py` | CNV/Fusion variable replacement (deferred)
