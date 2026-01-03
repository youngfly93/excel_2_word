# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Excel到Docx自动化报告生成系统** - An automated medical report generation system that extracts genetic testing data from Excel result files and populates docx templates using Jinja2 templating to generate standardized medical reports.

**Tech Stack**: Python 3.9+, docxtpl (python-docx-template), pandas, openpyxl, Click CLI framework

**Current Status**: Development (v1.0.0) on branch `001-excel-docx-automation`

## Essential Commands

### Installation & Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Development installation (editable mode)
pip install -e .

# Install dev dependencies (testing, linting)
pip install -r requirements-dev.txt

# Initialize project directories
reportgen init
```

### Core CLI Operations
```bash
# Generate single report
reportgen generate \
  --excel data/input/sample.xlsx \
  --template templates/aligned_template.docx \
  --output data/output/

# Generate with auto-detect project type (no template needed)
reportgen generate \
  --excel data/input/sample.xlsx \
  --output data/output/ \
  --auto-detect

# Strict mode (fail on missing critical fields)
reportgen generate -e sample.xlsx -t template.docx -o output/ --strict

# Validate template file
reportgen validate --template templates/template.docx

# Validate and show all template variables
reportgen validate -t templates/template.docx --show-vars

# Check template-mapping alignment
reportgen validate -t templates/template.docx --check-mapping

# Show help
reportgen --help
```

### Batch Processing
```bash
# Batch generate reports (standalone script)
python scripts/batch_generate_reports.py
python scripts/batch_generate_reports.py data/input data/output
```

### Testing & Quality
```bash
# Run all tests
pytest tests/

# Run tests with coverage report
pytest tests/ --cov=reportgen --cov-report=html

# Run specific test file
pytest tests/unit/test_config_loader.py -v

# Run performance benchmarks
pytest tests/ --benchmark-only

# Code formatting
black reportgen/
isort reportgen/

# Linting
flake8 reportgen/
pylint reportgen/
```

## Architecture Overview

### Data Flow Pipeline
The system follows a 5-stage pipeline orchestrated by `ReportGenerator` in reportgen/core/report_generator.py:

1. **Project Detection** (`ProjectDetector`) - Auto-detects project type (301-gene, 358-gene, lung methylation) from Excel content
2. **Excel Reading** (`ExcelReader`) - Extracts raw data from Excel sheets with configurable skip_rows and filtering
3. **Field Mapping** (`FieldMapper`) - Maps Excel columns to template variables using synonym-based configuration
4. **Data Cleaning** (`DataCleaner`) - Validates and normalizes data types, dates, and formats
5. **Template Rendering** (`TemplateRenderer`) - Uses docxtpl to populate Jinja2-templated docx files
6. **Output Generation** - Saves final reports with auto-generated filenames

### Configuration System
All configuration lives in `config/` directory:

- **`mapping.yaml`** - Core field mapping configuration with synonym support
  - `single_values`: Maps Excel columns → template variables (e.g., "患者姓名", "姓名" → `patient_name`)
  - `table_data`: Maps Excel sheets → template table loops (e.g., "Variations" sheet → `variants` table)
  - Supports data types, validation rules, format templates, default values

- **`project_types.yaml`** - Auto-detection rules for different report types (301-gene, 358-gene, lung methylation)

- **`settings.yaml`** - Global system settings

- **`filtering.yaml`** - Data filtering rules for variations, CNV, fusion data (frequency thresholds, clinical significance keywords)

- **`patient_info.yaml`** - Patient information field definitions

### Key Architectural Patterns

**Synonym-Based Mapping**: The field mapper supports flexible column name matching. Add new synonyms to `mapping.yaml` without code changes:
```yaml
patient_name:
  synonyms: ["患者姓名", "姓名", "病人姓名", "患者名"]
  type: string
  required: true
```

**Table Data Processing**: Multi-row Excel sheets (Variations, CNV, Fusion, etc.) are extracted as lists of dictionaries and rendered in docx templates using Jinja2 loops.

**Validation & Error Handling**: The system uses a validation error collection pattern - it continues processing but accumulates warnings/errors in `ReportData.validation_errors` for logging.

## Important Implementation Details

### Field Mapping Mechanism
When processing Excel files, the `FieldMapper` (reportgen/core/field_mapper.py):
1. Loads `mapping.yaml` configuration
2. For each template variable, searches Excel columns using all defined synonyms (case-insensitive, whitespace-normalized)
3. Applies type conversions and format templates
4. Uses default values for missing optional fields
5. Records validation errors for missing required fields

### Date Handling
The system auto-detects and normalizes multiple date formats:
- Supported input: "2025-10-24", "2025/10/24", "20251024", "2025.10.%d"
- Output: Unified "YYYY-MM-DD" format
- Located in: reportgen/core/data_cleaner.py

### Template Requirements
docx templates must:
- Use Jinja2 syntax: `{{ variable_name }}` for variables, `{% for item in items %}` for loops
- Place conditional sections using `{% if condition %}`
- Table loops require proper docx table structure with template rows

### Tools Directory
Helper scripts in `tools/` for template development:
- `compare_docx.py` - Compare generated reports against baseline
- `sanitize_docx.py` - Clean up docx files for template creation
- `make_template_from_baseline.py` - Generate templates from reference documents
- `build_aligned_template.py` - Align template structure with mapping config
- `patch_template_section.py` - Patch specific sections in templates

### Root-Level Analysis Scripts
Development/debugging scripts in project root:
- `scripts/batch_generate_reports.py` - Batch process multiple Excel files
- `analyze_excel_source.py` - Inspect Excel structure and data
- `analyze_generated_report.py` - Verify generated report contents
- `inspect_sheets.py` - Debug Excel sheet structure
- `scripts/generate_report.py` - Quick single report generation for testing

## Development Workflow

### Adding New Fields
1. Update `config/mapping.yaml` with new field and synonyms
2. Update docx template with `{{ new_field }}` placeholder
3. Add test case in `tests/unit/test_field_mapper.py`
4. Run tests: `pytest tests/unit/test_field_mapper.py -v`

### Supporting New Project Types
1. Add detection rules to `config/project_types.yaml`
2. Create template variant or use conditional rendering
3. Update `table_data` mappings if new sheets are required

### Testing Strategy
- **Unit tests**: Test individual components (config loader, validators, file utils)
- **Integration tests**: Test complete pipeline with real Excel/template files
- **Fixtures**: Located in `tests/fixtures/` (sample Excel, templates, data)
- **Coverage target**: 80%+

## Project Structure Notes

```
reportgen/               # Main package
├── core/               # Business logic orchestration
│   ├── excel_reader.py      # Excel data extraction
│   ├── field_mapper.py      # Column→variable mapping
│   ├── data_cleaner.py      # Validation & normalization
│   ├── template_renderer.py # docx template rendering
│   ├── project_detector.py  # Project type auto-detection
│   └── report_generator.py  # Pipeline orchestrator
├── models/             # Data models
│   ├── excel_data.py        # Raw Excel data structure
│   ├── report_data.py       # Cleaned report data
│   └── mapping.py           # Mapping configuration models
├── utils/              # Utilities
│   ├── logger.py            # Structured logging
│   ├── validators.py        # Input validation
│   └── file_utils.py        # File operations
└── config/             # Config management
    └── loader.py

config/                 # Configuration files (YAML)
├── mapping.yaml             # Field mappings (synonyms, types)
├── filtering.yaml           # Data filtering rules
├── project_types.yaml       # Project detection rules
├── patient_info.yaml        # Patient field definitions
└── settings.yaml            # Global settings
templates/              # docx template files
data/                   # Data directories
├── input/              # Source Excel files
├── output/             # Generated reports
└── logs/               # Log files
tools/                  # Template development utilities
specs/                  # Feature specifications
└── 001-excel-docx-automation/
    ├── spec.md              # Feature requirements
    ├── plan.md              # Implementation plan
    └── contracts/           # Config schemas
tests/                  # Test suite
├── unit/               # Unit tests
├── integration/        # Integration tests
└── fixtures/           # Test data
```

## Performance Targets

- Excel parsing: < 5 seconds per file
- Single report generation: < 10 seconds
- Batch processing (50 samples): < 5 minutes
- Memory usage: < 500MB per sample

## Critical Files to Understand

1. **reportgen/core/report_generator.py** - Main orchestration logic, entry point for understanding the pipeline
2. **config/mapping.yaml** - Field mapping schema - essential for understanding data transformation
3. **config/filtering.yaml** - Data filtering rules - controls what variations/mutations are included in reports
4. **reportgen/core/field_mapper.py** - Synonym matching and type conversion logic
5. **reportgen/core/project_detector.py** - Auto-detection logic for project types
6. **reportgen/cli.py** - CLI interface and command structure
7. **specs/001-excel-docx-automation/spec.md** - Comprehensive feature requirements and user stories

## Logging & Observability

The system uses structured JSON logging via `reportgen.utils.logger`:
- Log levels: DEBUG (with --verbose), INFO (default), WARNING, ERROR
- Key events logged: excel_reading_started/completed, field_mapping_started/completed, data_cleaning_started/completed, template_rendering_started/completed
- Logs include: timestamps, file paths, record counts, validation errors, processing duration

## Common Pitfalls

1. **Merged Cells in Excel**: The system handles merged cells, but be aware they can cause data extraction issues
2. **Chinese Character Encoding**: Ensure UTF-8 encoding throughout. Use `encoding='utf-8'` for file operations
3. **Docx Template Corruption**: Always validate templates with `reportgen validate` before use
4. **Synonym Matching**: Matching is case-insensitive and whitespace-normalized - test edge cases
5. **Date Format Auto-detection**: While robust, unusual formats may fail - check data_cleaner logs
6. **Filtering Configuration**: Changes to `filtering.yaml` affect which variations appear in reports - test with `--verbose` flag
7. **Skip Rows in Excel**: Table sheets may have header rows to skip - configured in `mapping.yaml` table_data sections

## Core Development Principles (from .cursor/rules/specify-rules.mdc)

- **Code Quality**: Clean, documented, linter-compliant code
- **Testing**: TDD approach, 80%+ coverage requirement
- **User Experience**: Consistent CLI interface, clear error messages, error-tolerant processing
- **Performance**: Meet defined benchmarks (see Performance Targets above)
- **Observability**: Structured logging, audit trails, version tracking in reports
