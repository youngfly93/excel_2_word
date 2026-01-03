# Tasks: Excel到Docx自动化报告生成系统

**Input**: Design documents from `/specs/001-excel-docx-automation/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are included based on TDD approach defined in plan.md (test coverage ≥ 80% required)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `reportgen/`, `tests/` at repository root
- Paths shown below follow the single project structure from plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project root directory structure (reportgen/, tests/, config/, templates/, data/)
- [ ] T002 Create requirements.txt with dependencies: docxtpl>=0.16.0, pandas>=1.5.0, openpyxl>=3.0.0, PyYAML>=6.0, python-dateutil>=2.8.0, click>=8.0.0
- [ ] T003 [P] Create requirements-dev.txt with dev dependencies: pytest>=7.0.0, pytest-cov>=4.0.0, pytest-mock, flake8, pylint, pytest-benchmark
- [ ] T004 [P] Create setup.py for package installation configuration
- [ ] T005 [P] Create README.md with project overview and quickstart reference
- [ ] T006 [P] Create .gitignore for Python project (ignore data/, __pycache__, *.pyc, .pytest_cache, etc.)
- [ ] T007 [P] Create reportgen/__init__.py as package marker
- [ ] T008 [P] Create reportgen/__version__.py with version="1.0.0"
- [ ] T009 [P] Create config/mapping.yaml based on contracts/mapping-schema.yaml
- [ ] T010 [P] Create config/project_types.yaml with 3 project type definitions (crc_301_msi, crc_358_msi, lung_methylation)
- [ ] T011 [P] Create config/settings.yaml based on contracts/config-schema.yaml
- [ ] T012 [P] Create tests/__init__.py and tests/conftest.py with pytest fixtures
- [ ] T013 [P] Create tests/fixtures/ directory with placeholder for test data

**Checkpoint**: Project structure ready - development can now begin

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T014 [P] Create reportgen/utils/__init__.py
- [ ] T015 [P] Create reportgen/utils/logger.py implementing StructuredLogger class with JSON logging
- [ ] T016 [P] Create reportgen/utils/validators.py with file path validation, field validation functions
- [ ] T017 [P] Create reportgen/utils/file_utils.py with file existence check, directory creation helpers
- [ ] T018 [P] Create reportgen/config/__init__.py
- [ ] T019 Create reportgen/config/loader.py with ConfigLoader class to load YAML configs (depends on T015 for logging)
- [ ] T020 [P] Create reportgen/models/__init__.py
- [ ] T021 [P] Create tests/unit/__init__.py for unit test organization
- [ ] T022 [P] Write unit test for ConfigLoader in tests/unit/test_config_loader.py
- [ ] T023 [P] Write unit test for validators in tests/unit/test_validators.py
- [ ] T024 [P] Write unit test for file_utils in tests/unit/test_file_utils.py
- [ ] T025 [P] Write unit test for StructuredLogger in tests/unit/test_logger.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - 单个报告生成 (Priority: P1) 🎯 MVP

**Goal**: 从Excel读取单个患者数据，填充docx模板生成终版报告

**Independent Test**: 使用MLF2509307001T_MLB2509307001.result.xlsx生成一份完整报告，验证关键字段填充正确

### Tests for User Story 1 (TDD - Write First) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T026 [P] [US1] Write unit test for ExcelDataSource in tests/unit/test_excel_reader.py (test load, get_sheet, validate methods)
- [ ] T027 [P] [US1] Write unit test for FieldMapping in tests/unit/test_field_mapper.py (test synonym matching, value formatting, validation)
- [ ] T028 [P] [US1] Write unit test for DataCleaner in tests/unit/test_data_cleaner.py (test date normalization, numeric cleaning, text sanitization)
- [ ] T029 [P] [US1] Write unit test for ReportData in tests/unit/test_report_data.py (test validation, to_template_context)
- [ ] T030 [P] [US1] Write unit test for DocxTemplateWrapper in tests/unit/test_template_renderer.py (test load, render, validate_context)
- [ ] T031 [US1] Write integration test for single report generation in tests/integration/test_end_to_end.py (full Excel → Docx flow)

### Implementation for User Story 1

**Models** (can run in parallel):
- [ ] T032 [P] [US1] Create reportgen/models/excel_data.py implementing ExcelDataSource class (file_path, sheets, load(), get_sheet(), validate())
- [ ] T033 [P] [US1] Create reportgen/models/mapping.py implementing FieldMapping class (variable_name, synonyms, match_column(), format_value())
- [ ] T034 [P] [US1] Create reportgen/models/report_data.py implementing ReportData class (patient_info, project_info, variants, validate(), to_template_context())

**Core Logic**:
- [ ] T035 [P] [US1] Create reportgen/core/__init__.py
- [ ] T036 [US1] Create reportgen/core/excel_reader.py implementing ExcelReader class to load Excel and extract data using pandas (depends on T032)
- [ ] T037 [US1] Create reportgen/core/field_mapper.py implementing FieldMapper class to map Excel columns to variables using mapping config (depends on T033)
- [ ] T038 [US1] Create reportgen/core/data_cleaner.py implementing DataCleaner class with date normalization, numeric cleaning, text sanitization (depends on T036)
- [ ] T039 [US1] Create reportgen/core/template_renderer.py implementing TemplateRenderer class using docxtpl to render template (depends on T034)
- [ ] T040 [US1] Create reportgen/core/report_generator.py implementing ReportGenerator class to coordinate Excel→Data→Template→Docx flow (depends on T036, T037, T038, T039)

**CLI for User Story 1**:
- [ ] T041 [US1] Create reportgen/cli.py with Click framework, implement `reportgen generate` command (depends on T040)
- [ ] T042 [US1] Add --excel, --output, --template, --mapping, --log, --verbose, --dry-run options to generate command
- [ ] T043 [US1] Implement error handling in CLI with user-friendly messages (no Python stack traces)
- [ ] T044 [US1] Add progress indicators and status messages to generate command

**Validation & Testing**:
- [ ] T045 [US1] Run all unit tests for User Story 1, verify 100% pass rate
- [ ] T046 [US1] Run integration test with MLF2509307001T_MLB2509307001.result.xlsx, verify report generation succeeds
- [ ] T047 [US1] Manually verify generated report: patient name, sample ID, variants table, MSI/TMB values correct
- [ ] T048 [US1] Run linter (flake8, pylint) on all US1 code, fix all errors
- [ ] T049 [US1] Measure test coverage for US1 modules, ensure ≥ 80%

**Checkpoint**: User Story 1 (MVP) complete - single report generation working end-to-end

---

## Phase 4: User Story 4 - 模板变量化与字段映射管理 (Priority: P2)

**Goal**: 支持灵活的字段映射配置，支持同义词，无需代码修改

**Independent Test**: 修改mapping.yaml添加新同义词，系统能正确识别并填充

### Tests for User Story 4 (TDD - Write First) ⚠️

- [ ] T050 [P] [US4] Write unit test for MappingConfigValidator in tests/unit/test_mapping_validator.py (test YAML parsing, synonym validation)
- [ ] T051 [US4] Write integration test for config reload in tests/integration/test_config_changes.py (modify mapping.yaml, verify recognition)

### Implementation for User Story 4

- [ ] T052 [P] [US4] Create reportgen/models/mapping_config.py implementing MappingConfig class to represent entire mapping.yaml structure
- [ ] T053 [US4] Extend reportgen/config/loader.py to add load_mapping_config() method with validation (depends on T052)
- [ ] T054 [US4] Implement mapping config validation in reportgen/utils/validators.py: check required fields, synonym lists, data types
- [ ] T055 [US4] Add CLI command `reportgen validate config` to validate mapping.yaml format and completeness
- [ ] T056 [US4] Add detailed error messages for mapping config errors (show line number, field name, expected format)
- [ ] T057 [US4] Update reportgen/core/field_mapper.py to reload config if changed (optional: add file watcher)

**Validation & Testing**:
- [ ] T058 [US4] Run all unit tests for User Story 4, verify 100% pass rate
- [ ] T059 [US4] Run integration test: modify mapping.yaml, generate report, verify new synonym recognized
- [ ] T060 [US4] Test edge case: invalid YAML syntax, verify clear error message
- [ ] T061 [US4] Test edge case: missing required field in mapping, verify validation catches it
- [ ] T062 [US4] Run linter on all US4 code, fix all errors
- [ ] T063 [US4] Measure test coverage, ensure ≥ 80%

**Checkpoint**: User Story 4 complete - flexible field mapping configuration working

---

## Phase 5: User Story 2 - 批量报告生成 (Priority: P2)

**Goal**: 批量处理多个样本，生成汇总日志和统计

**Independent Test**: 处理包含10个样本的Excel，生成10份报告，汇总日志显示成功/失败统计

### Tests for User Story 2 (TDD - Write First) ⚠️

- [ ] T064 [P] [US2] Write unit test for BatchProcessor in tests/unit/test_batch_processor.py (test multi-sample processing, error handling)
- [ ] T065 [US2] Write integration test for batch processing in tests/integration/test_batch_processing.py (test 10 samples end-to-end)

### Implementation for User Story 2

**Models**:
- [ ] T066 [P] [US2] Create reportgen/models/batch_result.py implementing BatchResult class (success_count, failed_count, summary)

**Core Logic**:
- [ ] T067 [US2] Create reportgen/core/batch_processor.py implementing BatchProcessor class to handle multiple samples (depends on T040)
- [ ] T068 [US2] Implement error recovery in BatchProcessor: continue on error, collect error details per sample
- [ ] T069 [US2] Implement progress tracking in BatchProcessor: show progress bar, current sample, estimated time remaining
- [ ] T070 [US2] Implement summary statistics: success/failure counts, average processing time, missing fields summary
- [ ] T071 [US2] Implement output organization: create subdirectories by date or project type

**CLI for User Story 2**:
- [ ] T072 [US2] Add `reportgen batch` command to CLI (depends on T067)
- [ ] T073 [US2] Add --excel with glob pattern support (e.g., "*.xlsx"), --output, --max-workers, --continue-on-error, --summary options
- [ ] T074 [US2] Implement progress bar display using click.progressbar or tqdm
- [ ] T075 [US2] Implement summary report generation to JSON file (include all BatchResult data)
- [ ] T076 [US2] Add parallel processing support using concurrent.futures.ProcessPoolExecutor (optional, max-workers parameter)

**Validation & Testing**:
- [ ] T077 [US2] Run all unit tests for User Story 2, verify 100% pass rate
- [ ] T078 [US2] Run integration test with 10-sample Excel file, verify all 10 reports generated correctly
- [ ] T079 [US2] Test batch processing with one failed sample (missing required field), verify continues with others
- [ ] T080 [US2] Test batch processing with 50 samples, verify completes in < 5 minutes
- [ ] T081 [US2] Verify summary.json contains correct statistics and failed sample details
- [ ] T082 [US2] Run linter on all US2 code, fix all errors
- [ ] T083 [US2] Measure test coverage, ensure ≥ 80%

**Checkpoint**: User Story 2 complete - batch processing and summary reporting working

---

## Phase 6: User Story 3 - 多项目类型自动识别 (Priority: P3)

**Goal**: 自动识别项目类型（301基因、358基因、肺癌甲基化），选择对应模板

**Independent Test**: 使用3种不同项目类型的Excel，验证自动识别正确且应用对应模板

### Tests for User Story 3 (TDD - Write First) ⚠️

- [ ] T084 [P] [US3] Write unit test for ProjectTypeDetector in tests/unit/test_project_type.py (test keyword matching, score calculation)
- [ ] T085 [US3] Write integration test for multi-project-type processing in tests/integration/test_project_types.py (test 3 different types)

### Implementation for User Story 3

**Models**:
- [ ] T086 [P] [US3] Create reportgen/models/project_type.py implementing ProjectType class (id, name, keywords, template_path, calculate_match_score())

**Core Logic**:
- [ ] T087 [US3] Create reportgen/core/project_detector.py implementing ProjectTypeDetector class to identify project type from Excel data
- [ ] T088 [US3] Implement keyword-based matching algorithm: calculate match score, select highest score above threshold
- [ ] T089 [US3] Load project type definitions from config/project_types.yaml in ProjectTypeDetector
- [ ] T090 [US3] Update reportgen/core/report_generator.py to auto-select template based on detected project type (depends on T087)
- [ ] T091 [US3] Implement fallback to default template if no project type matches (log warning)

**CLI for User Story 3**:
- [ ] T092 [US3] Update `reportgen generate` and `reportgen batch` to support automatic project type detection (no --template required)
- [ ] T093 [US3] Add --project-type option to manually override auto-detection
- [ ] T094 [US3] Add verbose logging to show detected project type and selected template

**Template Management**:
- [ ] T095 [P] [US3] Add `reportgen template list` command to show all available templates and their project types
- [ ] T096 [P] [US3] Add `reportgen template add` command to register new template with project type
- [ ] T097 [P] [US3] Add `reportgen template verify` command to validate template file integrity

**Validation & Testing**:
- [ ] T098 [US3] Run all unit tests for User Story 3, verify 100% pass rate
- [ ] T099 [US3] Run integration test with 301-gene Excel, verify crc_301_msi template selected
- [ ] T100 [US3] Run integration test with 358-gene Excel, verify crc_358_msi template selected
- [ ] T101 [US3] Run integration test with lung-methylation Excel, verify lung_methylation template selected
- [ ] T102 [US3] Test edge case: ambiguous project name, verify highest-score template selected
- [ ] T103 [US3] Test edge case: unrecognized project type, verify default template used with warning
- [ ] T104 [US3] Verify project type identification accuracy = 100% for known types
- [ ] T105 [US3] Run linter on all US3 code, fix all errors
- [ ] T106 [US3] Measure test coverage, ensure ≥ 80%

**Checkpoint**: User Story 3 complete - automatic project type detection and template selection working

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories, final quality checks

### 代码质量与合规性 (按宪章要求)

- [ ] T107 [P] Run flake8 on entire reportgen/ codebase, fix all errors and warnings
- [ ] T108 [P] Run pylint on entire reportgen/ codebase, fix all errors, achieve score ≥ 8.0/10
- [ ] T109 [P] Verify all functions have docstrings (PEP 257 compliant)
- [ ] T110 [P] Verify cyclomatic complexity < 10 for all functions (use radon or similar tool)
- [ ] T111 Code review: check for hardcoded values, ensure all configs externalized

### 测试与验证 (按宪章要求)

- [ ] T112 [P] Run full test suite (all unit + integration tests), verify 100% pass rate
- [ ] T113 Measure overall test coverage with pytest-cov, verify ≥ 85% coverage
- [ ] T114 [P] Create tests/fixtures/sample_excel.xlsx with脱敏测试数据 (3 samples, different project types)
- [ ] T115 [P] Create tests/fixtures/sample_template.docx based on real template structure
- [ ] T116 Run regression tests: use MLF2509307001T_MLB2509307001.result.xlsx, compare output with baseline
- [ ] T117 Add performance benchmark tests using pytest-benchmark for core functions (excel_reader, template_renderer)
- [ ] T118 Verify all test data is desensitized (no real patient names or IDs)

### 性能与监控 (按宪章要求)

- [ ] T119 Run performance test: single report generation, verify < 10 seconds
- [ ] T120 Run performance test: Excel parsing 2MB file, verify < 5 seconds
- [ ] T121 Run performance test: batch process 50 samples, verify < 5 minutes
- [ ] T122 Run memory profiling: verify single sample uses < 500MB peak memory
- [ ] T123 [P] Implement performance logging: record duration for each phase (load, map, render, save)
- [ ] T124 [P] Add performance metrics to JSON logs (file_size, processing_time, memory_used)

### 用户体验与安全 (按宪章要求)

- [ ] T125 Review all error messages, ensure they are clear and actionable (no Python stack traces in normal output)
- [ ] T126 Add user-facing documentation: update README.md with installation, usage examples, troubleshooting
- [ ] T127 [P] Implement CLI --help for all commands with clear descriptions and examples
- [ ] T128 [P] Add `reportgen validate all` command to check config, templates, and test Excel in one go
- [ ] T129 [P] Add `reportgen init` command to create config files and directory structure from scratch
- [ ] T130 Implement data privacy checks: verify logs don't contain patient_name in production mode (mask_sensitive_data=true)
- [ ] T131 Add file permission checks: verify write access to output directory before processing
- [ ] T132 Add disk space check: verify sufficient disk space before batch processing

### 最终验证

- [ ] T133 Run `reportgen validate all` on production-like setup, ensure all checks pass
- [ ] T134 Execute complete end-to-end test: init → generate single → batch → validate, verify all commands work
- [ ] T135 Verify all宪章合规性检查点 passed (reference plan.md Constitution Check section)
- [ ] T136 Generate final test coverage report (HTML format), review uncovered lines
- [ ] T137 Create release notes documenting features, usage, known limitations

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational (Phase 2) completion
  - User Story 1 (Phase 3): Can start after Foundational - No dependencies on other stories
  - User Story 4 (Phase 4): Can start after Foundational - Enhances US1 but independent
  - User Story 2 (Phase 5): Depends on US1 (reuses ReportGenerator) - Should start after US1
  - User Story 3 (Phase 6): Depends on US1 (extends template selection) - Should start after US1
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Independent after Foundational - MVP
- **User Story 4 (P2)**: Independent after Foundational - Can develop in parallel with US1
- **User Story 2 (P2)**: Depends on US1's ReportGenerator - Start after US1 complete
- **User Story 3 (P3)**: Depends on US1's template rendering - Start after US1 complete

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD)
- Models can be developed in parallel (marked [P])
- Core logic depends on models being complete
- CLI depends on core logic being complete
- Validation happens after implementation

### Parallel Opportunities

**Setup Phase**:
- T002-T013 (requirements, docs, configs, test setup) can all run in parallel

**Foundational Phase**:
- T014-T021 (utils, config, models setup) can run in parallel
- T022-T025 (unit tests) can run in parallel after T014-T021

**User Story 1**:
- T026-T030 (unit tests) can run in parallel
- T032-T034 (models) can run in parallel after tests written
- T036-T039 (core logic) have dependencies, run sequentially
- T045-T049 (validation) run sequentially after implementation

**User Story 4**:
- T050-T051 (tests) can run in parallel
- T052-T054 can run in parallel after tests

**User Story 2**:
- T064-T065 (tests) can run in parallel
- T077-T083 (validation) run after implementation

**User Story 3**:
- T084-T085 (tests) can run in parallel
- T095-T097 (template management commands) can run in parallel
- T099-T106 (validation) run after implementation

**Polish Phase**:
- T107-T111 (code quality) can run in parallel
- T112-T118 (testing) can run in parallel
- T119-T124 (performance) can run in parallel
- T125-T132 (UX/security) can run in parallel

---

## Parallel Example: User Story 1 Core Implementation

```bash
# After tests are written and models are complete:

# Launch core logic tasks (have dependencies, run sequentially):
Task T036: Create excel_reader.py (depends on ExcelDataSource model)
  ↓
Task T037: Create field_mapper.py (depends on FieldMapping model)  
  ↓
Task T038: Create data_cleaner.py (depends on excel_reader)
  ↓
Task T039: Create template_renderer.py (depends on ReportData model)
  ↓
Task T040: Create report_generator.py (coordinates all above)

# But unit tests for each can be written in parallel:
Task T026, T027, T028, T029, T030 - all in parallel
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T013)
2. Complete Phase 2: Foundational (T014-T025) - CRITICAL
3. Complete Phase 3: User Story 1 (T026-T049) - MVP!
4. **STOP and VALIDATE**: Test with real Excel file, verify report generation works
5. Can deploy/demo if ready

### Incremental Delivery

1. Foundation → Setup (T001-T013) + Foundational (T014-T025)
2. MVP → User Story 1 (T026-T049) - Deploy/Demo
3. Enhanced Config → User Story 4 (T050-T063) - Deploy/Demo
4. Batch Processing → User Story 2 (T064-T083) - Deploy/Demo
5. Auto Detection → User Story 3 (T084-T106) - Deploy/Demo
6. Production Ready → Polish (T107-T137) - Final Release

### Parallel Team Strategy

With multiple developers:

1. **Developer A**: Setup (T001-T013) → Foundational (T014-T025)
2. Once Foundational complete:
   - **Developer A**: User Story 1 (T026-T049)
   - **Developer B**: User Story 4 (T050-T063) - Can start in parallel
3. After US1 complete:
   - **Developer A**: User Story 2 (T064-T083)
   - **Developer B**: User Story 3 (T084-T106) - Can start in parallel
4. Both developers: Polish phase (T107-T137) together

---

## Task Summary

**Total Tasks**: 137

**Tasks by Phase**:
- Phase 1 (Setup): 13 tasks
- Phase 2 (Foundational): 12 tasks
- Phase 3 (User Story 1 - P1): 24 tasks
- Phase 4 (User Story 4 - P2): 14 tasks
- Phase 5 (User Story 2 - P2): 20 tasks
- Phase 6 (User Story 3 - P3): 23 tasks
- Phase 7 (Polish): 31 tasks

**Tasks by User Story**:
- US1 (单个报告生成): 24 tasks - MVP scope
- US4 (字段映射管理): 14 tasks
- US2 (批量报告生成): 20 tasks
- US3 (项目类型识别): 23 tasks
- Infrastructure (Setup + Foundational + Polish): 56 tasks

**Parallel Opportunities**: 58 tasks marked [P] can run in parallel (42% of total)

**Independent Test Criteria**:
- US1: Generate report from MLF2509307001T_MLB2509307001.result.xlsx, verify key fields correct
- US2: Process 10-sample Excel, verify 10 reports generated with summary statistics
- US3: Process 3 different project types, verify correct template selection for each
- US4: Modify mapping.yaml synonym, verify new column name recognized

**Suggested MVP Scope**: Phase 1 (Setup) + Phase 2 (Foundational) + Phase 3 (User Story 1) = **49 tasks**

---

## Notes

- [P] tasks = different files or independent modules, no blocking dependencies
- [Story] label maps task to specific user story for traceability
- All tests follow TDD: write test first → verify it fails → implement → verify it passes
- Each user story should be independently testable and deployable
- File paths are relative to repository root
- Commit after completing each task or logical group
- Stop at any checkpoint to validate story independently
- Performance tests run in Phase 7 to verify all stories meet performance goals together

