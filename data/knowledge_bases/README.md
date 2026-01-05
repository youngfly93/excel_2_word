# Knowledge Bases (Offline)

This project can load optional offline “knowledge bases” to improve report content consistency:

1) **Targeted drug tips DB** (`knowledge_bases.targeted_drug_db`)
   - Used to map gene/variant → “潜在获益靶向药物 / 可能耐药或慎重药物”.

2) **Immune gene list** (`knowledge_bases.immune_gene_list`)
   - Used to summarize detected variants into “免疫治疗正相关/负相关/超进展相关基因”.

3) **Variant insights DB** (`knowledge_bases.variant_insights_db`)
   - Used to add a variant-level one-liner into `gene_knowledge_sections` (e.g., hotspots/domains/mechanisms).

## Public sources (from `data_get.md`)

- CIViC data releases: https://civicdb.org/releases (CC0)
- CGI biomarkers (TSV): https://www.cancergenomeinterpreter.org/data/biomarkers/cgi_biomarkers_latest.tsv (CC0)

## How to build

1. Download raw TSVs into `data/knowledge_bases/raw/` (or use your own mirror).
2. Run:

   `python3 tools/knowledge_bases/build_public_kb.py`

3. The outputs will be written to `data/knowledge_bases/processed/`.

> Note: These sources are for internal automation and traceability. They are not medical advice.
