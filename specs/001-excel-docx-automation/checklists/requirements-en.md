# Requirements Quality Checklist – Excel→Docx Report Generation

Purpose: Unit tests for the English requirements (not implementation). Created by /speckit.checklist.

Meta:
- Feature Dir: /Volumes/KINGSTON/work/minhao/肠癌358基因/specs/001-excel-docx-automation
- Docs: spec.md, plan.md, tasks.md, research.md, data-model.md, contracts/
- Depth: Standard (default)
- Audience: Reviewer (PR)
- Focus: Data→Template mapping (US1), Config-driven mapping (US4), Batch (US2)

## Requirement Completeness
- [ ] CHK001 Are inputs/outputs defined for single-report generation, including required fields, optional fields, and defaults? [Completeness, Spec §US1]
- [ ] CHK002 Are the full set of tables/sections required in the generated report enumerated (variants, MSI/TMB, drug tips, CNV, fusion, HLA, etc.)? [Completeness, Spec §US1, Data-Model]
- [ ] CHK003 Does the spec list all supported project types and their template selection rules? [Completeness, Spec §US3]
- [ ] CHK004 Are CLI command options and combinations fully enumerated, including required/optional flags and examples? [Completeness, Spec §US1, Plan]
- [ ] CHK005 Are logging outputs (fields, structure, rotation/location) specified for all phases (load/map/clean/render)? [Completeness, Spec §US1, Plan]

## Requirement Clarity
- [ ] CHK006 Are mapping rules from Excel columns to template variables expressed unambiguously (synonyms, precedence, formatting)? [Clarity, Spec §US4, Data-Model]
- [ ] CHK007 Are template fidelity requirements stated with measurable anchors (page size, sections, headers/footers, table headers)? [Clarity, Spec §US1]
- [ ] CHK008 Is the rule for constructing output filenames precisely specified with examples and forbidden characters? [Clarity, Spec §US1]
- [ ] CHK009 Are MSI/TMB extraction positions and thresholds precisely defined (cells, fallbacks, units)? [Clarity, Spec §US1]
- [ ] CHK010 Is the definition of “正确/完整的报告” stated with objective criteria (which fields must be non-empty)? [Clarity, Spec §US1, Acceptance]

## Requirement Consistency
- [ ] CHK011 Are CLI options, config keys, and log field names consistent across spec/plan/tasks? [Consistency, Spec §US1, Plan, Tasks]
- [ ] CHK012 Do mapping rules in spec align with mapping.yaml schema (types, synonyms, required)? [Consistency, Spec §US4, Contracts]
- [ ] CHK013 Are section/table names consistent between the spec and the template inventory? [Consistency, Spec §US1]

## Acceptance Criteria Quality
- [ ] CHK014 Do acceptance criteria cover success, partial success (warnings), and failure with measurable pass/fail thresholds? [Acceptance Criteria, Spec §US1]
- [ ] CHK015 Are timing targets for single report and batch explicitly quantified (e.g., <10s, <5min/50 samples)? [Acceptance Criteria, Spec §US2, Plan]
- [ ] CHK016 Are acceptance checks defined for template selection correctness across project types? [Acceptance Criteria, Spec §US3]

## Scenario Coverage
- [ ] CHK017 Are scenarios defined for zero-variants, partial-sheet availability, and missing MSI/TMB? [Coverage, Spec §US1]
- [ ] CHK018 Are batch scenarios defined for continue-on-error, summary stats, and output organization? [Coverage, Spec §US2]
- [ ] CHK019 Are multi-template/project-type routes covered including fallback behavior when detection is ambiguous? [Coverage, Spec §US3]

## Edge Case Coverage
- [ ] CHK020 Are filename collisions, illegal characters, and overly long names handled and specified? [Edge Case, Plan]
- [ ] CHK021 Are extremely large Excel files, empty sheets, and mixed encodings called out with expected handling? [Edge Case, Research]
- [ ] CHK022 Are template variable-not-found and table shape mismatches defined with user-facing guidance? [Edge Case, Spec §US1]

## Non-Functional Requirements
- [ ] CHK023 Are logging verbosity levels and redaction rules for sensitive fields documented? [NFR, Spec §US1, Plan]
- [ ] CHK024 Are privacy constraints (PII in logs/files), local-only processing, and storage policies specified? [NFR, Research, Spec §US1]
- [ ] CHK025 Are performance, memory, and concurrency targets stated with measurement methods? [NFR, Plan]

## Dependencies & Assumptions
- [ ] CHK026 Are external library/runtime requirements (pandas, openpyxl, docxtpl, click) listed with version ranges and substitution policies? [Dependency, Plan]
- [ ] CHK027 Are template source-of-truth and config ownership (who updates mapping.yaml/templates) documented? [Assumption, Spec §US4]
- [ ] CHK028 Is the sample Excel (MLF2509307001T_MLB2509307001.result.xlsx) designated only as demo data with anonymization expectations? [Assumption, Research]

## Ambiguities & Conflicts
- [ ] CHK029 Is precedence among data sources (Excel vs config defaults vs filename inference) explicit and conflict-free? [Ambiguity, Spec §US1, US4]
- [ ] CHK030 Is “自动识别项目类型”优先级与用户手动覆盖（CLI --project-type）规定清晰且无冲突？ [Ambiguity, Spec §US3]
- [ ] CHK031 Are error messages requirements phrased specifically (no raw stack traces in normal output) and consistent across CLI & core? [Conflict/Ambiguity, Spec §US1, Plan]

## Traceability & ID Scheme
- [ ] CHK032 Does the spec define requirement/AC IDs or a cross-reference scheme between spec/plan/tasks for traceability ≥80%? [Traceability, Gap]

