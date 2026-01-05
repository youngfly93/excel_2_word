from reportgen.core.template_contract import TemplateContractValidator
from reportgen.models.report_data import ReportData


class TestTemplateContractValidator:
    def test_missing_required_fields(self):
        contract = {"required_fields": ["patient_name", "sample_id"], "checks": []}
        rd = ReportData(context={"patient_name": "张三"})
        v = TemplateContractValidator(contract).validate(rd, template_vars=[])
        assert any("sample_id" in x.message for x in v)

    def test_missing_template_vars_with_optional(self):
        contract = {"optional_template_vars": ["hospital"], "checks": []}
        rd = ReportData(context={"patient_name": "张三", "sample_id": "S1"})
        template_vars = ["patient_name", "sample_id", "hospital", "summary_variants", "row.gene"]
        v = TemplateContractValidator(contract).validate(rd, template_vars=template_vars)
        assert any(x.code == "missing_template_variables" for x in v)
        # optional var is ignored; summary_variants is missing -> should appear
        assert "summary_variants" in v[0].message

    def test_count_equals_table_len(self):
        contract = {
            "checks": [
                {
                    "type": "count_equals_table_len",
                    "field": "total_variants_count",
                    "table": "summary_variants",
                }
            ]
        }
        rd = ReportData(
            context={
                "total_variants_count": 2,
                "summary_variants": [{"gene": "TP53"}],
            }
        )
        v = TemplateContractValidator(contract).validate(rd, template_vars=[])
        assert any(x.code == "count_mismatch" for x in v)

    def test_reference_numbering(self):
        contract = {
            "checks": [
                {"type": "reference_numbering", "table": "references", "number_key": "number", "text_key": "text"}
            ]
        }
        rd = ReportData(
            context={
                "references": [
                    {"number": 1, "text": "A"},
                    {"number": 3, "text": "B"},
                ]
            }
        )
        v = TemplateContractValidator(contract).validate(rd, template_vars=[])
        assert any(x.code == "reference_numbering_invalid" for x in v)
