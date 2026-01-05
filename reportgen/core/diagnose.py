"""
环境自检 / 一键诊断

为“依赖治理 + 环境自检”提供可复用的核心逻辑，供 CLI `reportgen diagnose` 调用。
"""

from __future__ import annotations

import platform
import sys
import ssl
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportgen.config.loader import ConfigLoader
from reportgen.core.template_contract import TemplateContractValidator, select_contract
from reportgen.core.template_renderer import TemplateRenderer
from reportgen.core.template_bridge_358 import enhance_report_data
from reportgen.core.report_generator import ReportGenerator


@dataclass(frozen=True)
class DiagnoseResult:
    ok: bool
    summary: List[str]
    details: Dict[str, Any]


def _pkg_version(name: str) -> Optional[str]:
    try:
        return metadata.version(name)
    except Exception:
        return None


def run_diagnose(
    *,
    config_dir: str,
    template_path: str,
    excel_path: Optional[str] = None,
    log_file: Optional[str] = None,
    log_level: str = "INFO",
) -> DiagnoseResult:
    summary: List[str] = []
    details: Dict[str, Any] = {}
    ok = True

    cfg_dir = Path(config_dir)
    tpl = Path(template_path)

    # --- Environment ---
    details["python"] = {"version": sys.version.split()[0], "executable": sys.executable}
    details["platform"] = platform.platform()
    details["packages"] = {
        "pandas": _pkg_version("pandas"),
        "openpyxl": _pkg_version("openpyxl"),
        "docxtpl": _pkg_version("docxtpl"),
        "python-docx": _pkg_version("python-docx"),
        "xlrd": _pkg_version("xlrd"),
        "jinja2": _pkg_version("jinja2"),
        "requests": _pkg_version("requests"),
        "urllib3": _pkg_version("urllib3"),
    }

    # Known compatibility footgun: urllib3 v2 + LibreSSL
    try:
        if (details["packages"].get("urllib3") or "").startswith("2") and "LibreSSL" in ssl.OPENSSL_VERSION:
            summary.append(
                "检测到 urllib3 v2 + LibreSSL：建议使用 requirements.txt 中的 `urllib3<2` 以避免告警/兼容问题"
            )
    except Exception:
        pass

    # --- Paths ---
    required_files = {
        "mapping": cfg_dir / "mapping.yaml",
        "settings": cfg_dir / "settings.yaml",
        "filtering": cfg_dir / "filtering.yaml",
        "template_contracts": cfg_dir / "template_contracts.yaml",
    }
    details["paths"] = {k: str(v) for k, v in required_files.items()}

    missing = [k for k, p in required_files.items() if not p.exists()]
    if missing:
        ok = False
        summary.append(f"缺少配置文件: {missing}")

    if not tpl.exists():
        ok = False
        summary.append(f"模板文件不存在: {tpl}")

    # --- Contract selection + template scan ---
    loader = ConfigLoader(config_dir=str(cfg_dir), log_file=log_file, log_level=log_level)
    contracts_cfg = loader.load_template_contracts_config()
    contract = select_contract(contracts_cfg, str(tpl))
    details["contract"] = {"selected": contract.get("id") if isinstance(contract, dict) else None}

    renderer = TemplateRenderer(log_file=log_file, log_level=log_level)
    template_vars = renderer.get_template_variables(str(tpl)) if tpl.exists() else []
    loop_item_vars = renderer.get_template_loop_item_variables(str(tpl)) if tpl.exists() else set()
    details["template"] = {
        "path": str(tpl),
        "vars_count": len(template_vars),
        "loop_item_vars": sorted(loop_item_vars),
    }

    # --- Knowledge base paths (optional, but enabled ones should exist in production) ---
    try:
        settings = loader.load_settings_config()
    except Exception:
        settings = {}
    kb_checks: Dict[str, Dict[str, Any]] = {}
    if isinstance(settings, dict):
        kb = settings.get("knowledge_bases", {}) if isinstance(settings.get("knowledge_bases", {}), dict) else {}
        base = cfg_dir.parent
        for key in [
            "targeted_drug_db",
            "immune_gene_list",
            "gene_knowledge_db",
            "cancer_type_genes",
            "gene_transcript_db",
        ]:
            cfg = kb.get(key, {}) if isinstance(kb, dict) else {}
            enabled = bool(cfg.get("enabled", False)) if isinstance(cfg, dict) else False
            path = (cfg.get("path") if isinstance(cfg, dict) else None) if enabled else None
            p = None
            exists = None
            if path:
                p = Path(str(path))
                if not p.is_absolute():
                    p = base / p
                exists = p.exists()
                if enabled and not exists:
                    ok = False
                    summary.append(f"知识库文件缺失（已启用）: {key} -> {p}")
            kb_checks[key] = {"enabled": enabled, "path": str(p) if p else None, "exists": exists}
    details["knowledge_bases"] = kb_checks

    # --- Optional: build ReportData and run contract validation ---
    if excel_path is not None:
        xls = Path(excel_path)
        if not xls.exists():
            ok = False
            summary.append(f"Excel 文件不存在: {xls}")
        else:
            generator = ReportGenerator(
                config_dir=str(cfg_dir), log_file=log_file, log_level=log_level
            )
            excel_data = generator.excel_reader.read(str(xls), include_tables=True)
            report_data = generator.field_mapper.map(excel_data)
            report_data = generator.data_cleaner.validate_and_clean(report_data)
            report_data = enhance_report_data(
                report_data,
                excel_data,
                field_mapper=generator.field_mapper,
                gene_knowledge_provider=generator.gene_knowledge_provider,
                cancer_type_gene_provider=generator.cancer_type_gene_provider,
                base_path=str(cfg_dir.parent),
            )

            details["report_data"] = {
                "fields": len([k for k, v in report_data.context.items() if not isinstance(v, list)]),
                "tables": len([k for k, v in report_data.context.items() if isinstance(v, list)]),
                "validation_errors": list(report_data.validation_errors),
            }

            if isinstance(contract, dict) and contract:
                violations = TemplateContractValidator(contract).validate(
                    report_data, template_vars=template_vars, loop_item_vars=loop_item_vars
                )
                details["contract"]["violations"] = [v.message for v in violations]
                if violations:
                    ok = False
                    summary.append(f"模板契约校验失败: {len(violations)} 项")
            else:
                details["contract"]["violations"] = []

    if ok and not summary:
        summary.append("诊断通过")

    return DiagnoseResult(ok=ok, summary=summary, details=details)
