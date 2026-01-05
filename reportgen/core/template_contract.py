"""
模板契约（Template Contract）校验

目标：避免“变量缺失/关键表格为空/关键统计不一致，但仍然生成成功”的静默失败。

该模块提供基于 YAML 配置的校验器：
- 校验模板变量是否在上下文中提供（支持 optional 列表）
- 校验关键字段/表格是否满足最小要求
- 校验关键统计与表格行数的一致性
- 校验参考文献编号格式（连续编号、文本非空）
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from reportgen.models.report_data import ReportData


@dataclass(frozen=True)
class ContractViolation:
    """一次契约违规。"""

    code: str
    message: str


def select_contract(
    contracts_config: Dict[str, Any], template_path: str
) -> Optional[Dict[str, Any]]:
    """从 contracts 配置中选择与模板匹配的一条契约。"""
    contracts = contracts_config.get("contracts", []) if isinstance(contracts_config, dict) else []
    if not isinstance(contracts, list):
        return None

    template_path_norm = str(template_path).replace("\\", "/")
    template_name = Path(template_path).name

    for c in contracts:
        if not isinstance(c, dict):
            continue
        globs = c.get("template_globs", []) or c.get("templates", []) or []
        if not globs:
            return c
        if isinstance(globs, str):
            globs = [globs]
        if any(
            fnmatch(template_name, str(pat)) or fnmatch(template_path_norm, str(pat))
            for pat in globs
        ):
            return c

    return None


class TemplateContractValidator:
    """根据单条契约配置校验 ReportData。"""

    def __init__(self, contract: Dict[str, Any]):
        self.contract = contract or {}

    def validate(
        self,
        report_data: ReportData,
        *,
        template_vars: Optional[Sequence[str]] = None,
        loop_item_vars: Optional[Iterable[str]] = None,
    ) -> List[ContractViolation]:
        violations: List[ContractViolation] = []

        violations.extend(self._validate_required_fields(report_data))
        violations.extend(self._validate_checks(report_data))

        if template_vars is not None:
            violations.extend(
                self._validate_template_vars(
                    report_data, template_vars, loop_item_vars=loop_item_vars
                )
            )

        return violations

    # -------------------- checks --------------------
    def _validate_required_fields(self, report_data: ReportData) -> List[ContractViolation]:
        required_fields = self.contract.get("required_fields", []) or []
        if isinstance(required_fields, str):
            required_fields = [required_fields]

        violations: List[ContractViolation] = []
        for field in required_fields:
            key = str(field)
            value = report_data.get_field(key, None)
            if _is_empty(value):
                violations.append(
                    ContractViolation(
                        code="missing_required_field",
                        message=f"契约校验：必填字段缺失或为空：{key}",
                    )
                )
        return violations

    def _validate_template_vars(
        self,
        report_data: ReportData,
        template_vars: Sequence[str],
        *,
        loop_item_vars: Optional[Iterable[str]] = None,
    ) -> List[ContractViolation]:
        optional = self.contract.get("optional_template_vars", []) or []
        if isinstance(optional, str):
            optional = [optional]
        optional_set = {str(x) for x in optional}
        loop_item_set = {str(x) for x in (loop_item_vars or []) if str(x).strip()}

        # 仅校验顶层变量（row.* 属于循环行字段，无法在此统一判断）
        top_vars = [
            v
            for v in template_vars
            if isinstance(v, str)
            and not v.startswith("row.")
            and not v.startswith("row[")
        ]

        missing: List[str] = []
        ctx = report_data.get_template_context()

        for var in top_vars:
            if var in optional_set:
                continue
            root = var.split(".", 1)[0].strip()
            # 跳过循环局部变量（如 {%p for ref in numbered_references %} 中的 ref）
            if root and root in loop_item_set:
                continue
            if var in ctx and ctx.get(var) is not None:
                continue
            if root and root in ctx and ctx.get(root) is not None:
                continue
            missing.append(var)

        if not missing:
            return []

        # 去重并排序，避免输出过长
        uniq = sorted(set(missing))
        preview = uniq[:20]
        suffix = f"（还有 {len(uniq) - 20} 个）" if len(uniq) > 20 else ""
        return [
            ContractViolation(
                code="missing_template_variables",
                message=f"契约校验：模板变量缺失：{preview}{suffix}",
            )
        ]

    def _validate_checks(self, report_data: ReportData) -> List[ContractViolation]:
        checks = self.contract.get("checks", []) or []
        if not isinstance(checks, list):
            return []

        violations: List[ContractViolation] = []
        for chk in checks:
            if not isinstance(chk, dict):
                continue
            chk_type = str(chk.get("type", "")).strip()
            if not chk_type:
                continue

            if chk_type == "count_equals_table_len":
                violations.extend(self._check_count_equals_table_len(report_data, chk))
            elif chk_type == "nonempty_table_if_field_gt":
                violations.extend(self._check_nonempty_table_if_field_gt(report_data, chk))
            elif chk_type == "table_min_rows":
                violations.extend(self._check_table_min_rows(report_data, chk))
            elif chk_type == "reference_numbering":
                violations.extend(self._check_reference_numbering(report_data, chk))
            else:
                # unknown check type: ignore (forward compatible)
                continue

        return violations

    def _check_count_equals_table_len(
        self, report_data: ReportData, chk: Dict[str, Any]
    ) -> List[ContractViolation]:
        field = str(chk.get("field", "")).strip()
        table = str(chk.get("table", "")).strip()
        if not field or not table:
            return []

        expected = _to_int(report_data.get_field(field, None))
        rows = report_data.get_table(table) or []
        actual = len(rows)
        if expected is None:
            return [
                ContractViolation(
                    code="count_field_missing_or_invalid",
                    message=f"契约校验：统计字段无法解析为数字：{field}",
                )
            ]
        if expected != actual:
            return [
                ContractViolation(
                    code="count_mismatch",
                    message=f"契约校验：统计不一致：{field}={expected} 但 {table} 行数={actual}",
                )
            ]
        return []

    def _check_nonempty_table_if_field_gt(
        self, report_data: ReportData, chk: Dict[str, Any]
    ) -> List[ContractViolation]:
        table = str(chk.get("table", "")).strip()
        field = str(chk.get("field", "")).strip()
        threshold = _to_int(chk.get("threshold", 0)) or 0
        if not table or not field:
            return []

        field_val = _to_int(report_data.get_field(field, None))
        if field_val is None:
            return []
        if field_val > threshold and len(report_data.get_table(table) or []) == 0:
            return [
                ContractViolation(
                    code="unexpected_empty_table",
                    message=(
                        f"契约校验：关键表格为空：{table}（{field}={field_val} > {threshold}）"
                    ),
                )
            ]
        return []

    def _check_table_min_rows(
        self, report_data: ReportData, chk: Dict[str, Any]
    ) -> List[ContractViolation]:
        table = str(chk.get("table", "")).strip()
        min_rows = _to_int(chk.get("min_rows", 0)) or 0
        if not table:
            return []
        actual = len(report_data.get_table(table) or [])
        if actual < min_rows:
            return [
                ContractViolation(
                    code="table_too_small",
                    message=f"契约校验：表格行数不足：{table} 行数={actual} < {min_rows}",
                )
            ]
        return []

    def _check_reference_numbering(
        self, report_data: ReportData, chk: Dict[str, Any]
    ) -> List[ContractViolation]:
        table = str(chk.get("table", "references")).strip() or "references"
        number_key = str(chk.get("number_key", "number")).strip() or "number"
        text_key = str(chk.get("text_key", "text")).strip() or "text"

        refs = report_data.get_table(table) or []
        if not refs:
            # 参考文献可能为空（例如无相关位点/知识库关闭），不在此强制
            return []

        numbers: List[int] = []
        for idx, r in enumerate(refs, start=1):
            if not isinstance(r, dict):
                return [
                    ContractViolation(
                        code="invalid_references_table",
                        message=f"契约校验：参考文献表格式错误：{table} 第{idx}行不是字典",
                    )
                ]
            num = _to_int(r.get(number_key))
            txt = r.get(text_key)
            if num is None or _is_empty(txt):
                return [
                    ContractViolation(
                        code="invalid_reference_item",
                        message=f"契约校验：参考文献条目缺失编号或内容：{table} 第{idx}行",
                    )
                ]
            numbers.append(num)

        expected = list(range(1, len(numbers) + 1))
        if numbers != expected:
            return [
                ContractViolation(
                    code="reference_numbering_invalid",
                    message=f"契约校验：参考文献编号不连续：实际={numbers[:20]}",
                )
            ]
        return []


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        s = str(value).strip()
        if not s or s.lower() in {"nan", "none", "null", "-"}:
            return None
        return int(float(s))
    except Exception:
        return None
