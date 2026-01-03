# Repository Guidelines

## Project Structure

- `reportgen/`: main Python package (`core/`, `models/`, `utils/`, `config/`).
- `config/`: YAML configuration (`mapping.yaml`, `settings.yaml`, `project_types.yaml`).
- `templates/`: `.docx` Word templates used for rendering; keep only sample/sanitized templates in git.
- `data/`: sample inputs/outputs for local testing (use anonymised or synthetic data only).
- `tests/`: `unit/`, `integration/`, `fixtures/` for sample Excel/Docx used by tests.
- Top-level scripts (e.g. `scripts/generate_report.py`, `scripts/batch_generate_reports.py`) and `tools/`: helper workflows; keep idempotent and documented in docstrings.

## Build, Test, and Development

- Install (dev): `python -m venv .venv && source .venv/bin/activate`
- Dependencies: `pip install -r requirements-dev.txt`
- Editable install: `pip install -e .`
- Run tests: `pytest tests`
- Coverage: `pytest tests --cov=reportgen --cov-report=html` (open `htmlcov/index.html`)
- CLI smoke checks: `reportgen generate --help` and `reportgen validate all`

## Coding Style & Naming

- Python 3.9+, 4-space indentation; format with Black (`black reportgen`) and sort imports with isort (`isort reportgen`).
- Linting: `flake8 reportgen`, `pylint reportgen`.
- Naming: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- Keep business logic in `reportgen/core` or `reportgen/models` (avoid heavy logic in CLI entrypoints).

## Testing Guidelines

- Use `pytest`; name files `test_*.py` and tests `test_*`.
- Prefer unit tests for pure logic under `tests/unit/`; end-to-end flows under `tests/integration/`.
- When changing mappings/templates/report generation, add a regression test using fixtures under `tests/fixtures/`.

## Commit & Pull Requests

- Commit messages: imperative and scoped (e.g. `fix: handle empty fusion sheet`, `feat: add HLA QC parser`).
- PRs include: purpose, key changes, reproduction steps, and how you tested (exact commands).
- If configs/templates change, attach an example generated report path (or describe template impacts clearly).

## Configuration & Data Safety

- Never commit real patient identifiers or real reports; use sanitised/synthetic samples.
- Avoid hard-coded environment paths in YAML; prefer env vars or local overrides ignored by git.
