import yaml

from reportgen.core.field_mapper import FieldMapper
from reportgen.core.template_bridge_358 import enhance_report_data
from reportgen.models.excel_data import ExcelDataSource
from reportgen.models.report_data import ReportData
from reportgen.utils.hgvs_utils import format_variant_site, infer_variant_type_cn


def test_infer_variant_type_cn_from_c_hgvs():
    assert infer_variant_type_cn("c.844C>T") == "点突变"
    assert infer_variant_type_cn("c.123_124del") == "缺失突变"
    assert infer_variant_type_cn("c.123_124dup") == "重复突变"
    assert infer_variant_type_cn("c.123_124insA") == "插入突变"
    assert infer_variant_type_cn("c.123_124delinsTT") == "缺失插入突变"


def test_format_variant_site_combines_c_and_p_with_comma_newline():
    assert format_variant_site("c.1A>T", "p.R1W") == "c.1A>T,\np.R1W"
    assert format_variant_site("c.1A>T", "") == "c.1A>T"
    assert format_variant_site("c.1A>T", "--") == "c.1A>T"
    assert format_variant_site(None, "p.R1W") == "p.R1W"


def test_build_variants_2_1_uses_c_hgvs_for_type_and_locus(tmp_path):
    # minimal mapping config required by FieldMapper
    mapping = {
        "schema_version": "1.0",
        "single_values": {},
        "table_data": {},
    }
    (tmp_path / "mapping.yaml").write_text(
        yaml.safe_dump(mapping, allow_unicode=True), encoding="utf-8"
    )

    # ExcelDataSource requires a path that exists.
    excel_path = tmp_path / "dummy.xlsx"
    excel_path.write_bytes(b"")

    excel_data = ExcelDataSource(
        file_path=str(excel_path),
        table_data={
            "Variations": [
                {
                    "ExistIn552": "Ⅱ类",
                    "Gene_Symbol": "TP53",
                    "Transcript": "NM_000546.6",
                    "Chr": "chr17",
                    "ExIn_ID": "EX2",
                    "cHGVS": "c.1_2delinsTT",
                    "pHGVS_S": "p.A1B",
                    "Freq(%)": "12.3",
                }
            ]
        },
        sheet_names=["Variations"],
    )

    mapper = FieldMapper(config_dir=str(tmp_path))
    rows = mapper._build_variants_2_1(excel_data, ReportData())
    assert len(rows) == 1
    assert rows[0]["var_type_cn"] == "缺失插入突变"
    assert rows[0]["locus"] == "c.1_2delinsTT,\np.A1B"


def test_template_bridge_358_uses_field_mapper_drug_lookup(tmp_path):
    class DummyMapper:
        def __init__(self):
            self.calls = []

        def _lookup_targeted_drugs_for_variant(self, gene: str, *, c_point: str, p_point: str, variant_level: str = ""):
            self.calls.append((gene, c_point, p_point, variant_level))
            return "BEN", "CAU", 100.0

    excel_path = tmp_path / "dummy2.xlsx"
    excel_path.write_bytes(b"")
    excel_data = ExcelDataSource(
        file_path=str(excel_path),
        table_data={
            "Variations": [
                {
                    "ExistInsmall358": 1,
                    "ExistIn552": "Ⅱ类",
                    "Gene_Symbol": "TP53",
                    "Transcript": "NM_000546.6",
                    "Chr": "chr17",
                    "ExIn_ID": "EX2",
                    "cHGVS": "c.1A>T",
                    "pHGVS_S": "p.A1B",
                    "Freq(%)": "12.3",
                }
            ]
        },
        sheet_names=["Variations"],
    )

    dummy = DummyMapper()
    report_data = ReportData()
    enhanced = enhance_report_data(report_data, excel_data, field_mapper=dummy)

    variants = enhanced.get_table("variants")
    assert len(variants) == 1
    assert variants[0]["benefit_drugs"] == "BEN"
    assert variants[0]["caution_drugs"] == "CAU"
    expected = ("TP53", "c.1A>T", "p.A1B", "Ⅱ类")
    assert expected in dummy.calls
    assert all(call == expected for call in dummy.calls)


def test_template_bridge_358_normalizes_kras_atm_drug_tips(tmp_path):
    kras_benefit = (
        "Avutometinib+Defactinib（C）\n"
        "司美替尼（C）\n"
        "曲美替尼+Navitoclax（C）\n"
        "帕尼单抗+曲美替尼（C）\n"
        "贝美替尼+哌柏西利（C）\n"
        "BI 1701963（C）\n"
        "BI 1701963+曲美替尼（C）\n"
        "PD0325901+哌柏西利（C）\n"
        "奈拉替尼+曲美替尼（C）\n"
        "福巴替尼+贝美替尼（C）\n"
        "依维莫司+Avutometinib（C）\n"
        "GH35（C）\n"
        "RMC-6236（C）\n"
        "PD0325901（D）"
    )
    atm_benefit = (
        "奥拉帕利（C）\n"
        "芦卡帕利（C）\n"
        "尼拉帕利（C）\n"
        "他拉唑帕利（C）\n"
        "AZD6738+奥拉帕利（C）\n"
        "阿维鲁单抗+他拉唑帕利（C）\n"
        "LY2606368（C）\n"
        "盐酸可泮利塞+奥拉帕利+度伐利尤单抗（C）\n"
        "奥拉帕利+帕博利珠单抗（C）\n"
        "帕米帕利+替雷利珠单抗（C）\n"
        "芦卡帕利+阿替利珠单抗（C）\n"
        "他拉唑帕利+阿替利珠单抗（C）Tuvusertib+Peposertib（C）"
    )

    class DummyMapper:
        def _lookup_targeted_drugs_for_variant(
            self, gene: str, *, c_point: str, p_point: str, variant_level: str = ""
        ):
            if gene == "KRAS":
                return kras_benefit, "--", 100.0
            if gene == "ATM":
                return atm_benefit, "--", 100.0
            return "--", "--", 0.0

    excel_path = tmp_path / "dummy3.xlsx"
    excel_path.write_bytes(b"")
    excel_data = ExcelDataSource(
        file_path=str(excel_path),
        table_data={
            "Variations": [
                {
                    "ExistInsmall358": 1,
                    "ExistIn552": "Ⅰ类",
                    "Gene_Symbol": "KRAS",
                    "Transcript": "NM_004985.5",
                    "Chr": "chr12",
                    "ExIn_ID": "EX2",
                    "cHGVS": "c.35G>A",
                    "pHGVS_S": "p.G12D",
                    "Freq(%)": "12.3",
                },
                {
                    "ExistInsmall358": 1,
                    "ExistIn552": "Ⅱ类",
                    "Gene_Symbol": "ATM",
                    "Transcript": "NM_000051.4",
                    "Chr": "chr11",
                    "ExIn_ID": "EX2",
                    "cHGVS": "c.1A>T",
                    "pHGVS_S": "p.A1B",
                    "Freq(%)": "12.3",
                },
            ]
        },
        sheet_names=["Variations"],
    )

    enhanced = enhance_report_data(ReportData(), excel_data, field_mapper=DummyMapper())
    variants = enhanced.get_table("variants")
    assert {v["gene"] for v in variants} == {"KRAS", "ATM"}

    kras = next(v for v in variants if v["gene"] == "KRAS")
    assert kras["benefit_drugs"] == (
        "司美替尼（C）\n"
        "曲美替尼+Navitoclax（C）\n"
        "帕尼单抗+曲美替尼（C）\n"
        "贝美替尼+哌柏西利（C）\n"
        "BI 1701963（C）\n"
        "BI 1701963+曲美替尼（C）\n"
        "PD0325901+哌柏西利（C）\n"
        "奈拉替尼+曲美替尼（C）\n"
        "福巴替尼+贝美替尼（C） Defactinib+Avutometinib（C）\n"
        "依维莫司+Avutometinib（C）\n"
        "RMC-6236（C）\n"
        "PD0325901（D）"
    )

    atm = next(v for v in variants if v["gene"] == "ATM")
    assert "Tuvusertib+Peposertib（C）" not in atm["benefit_drugs"]
    assert atm["benefit_drugs"].endswith("他拉唑帕利+阿替利珠单抗（C）")
