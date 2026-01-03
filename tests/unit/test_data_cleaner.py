import pytest

from reportgen.core.data_cleaner import DataCleaner
from reportgen.models.report_data import ReportData


def test_clean_preserves_newlines_and_removes_tabs():
    report_data = ReportData(
        context={"note": "line1  \nline2\t\tmore\n\n\nline3"}
    )

    cleaner = DataCleaner()
    cleaner.clean(report_data)

    cleaned = report_data.get_field("note")
    assert "\n" in cleaned
    assert "\t" not in cleaned
    assert "line1" in cleaned
    assert "line2" in cleaned
    assert "line3" in cleaned
    # 连续空行最多保留2行
    assert "\n\n\n" not in cleaned


def test_validate_and_clean_records_missing_required_fields():
    report_data = ReportData(context={})

    cleaner = DataCleaner()
    cleaner.validate_and_clean(report_data)

    assert "缺失必填字段: sample_id" in report_data.validation_errors
    assert "缺失必填字段: report_date" in report_data.validation_errors

