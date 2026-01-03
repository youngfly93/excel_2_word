import yaml

from reportgen.core.project_detector import ProjectDetector


def test_detect_uses_detection_field_text_when_filename_has_no_keywords(tmp_path):
    mapping = {
        "schema_version": "1.0",
        "single_values": {
            "project_name": {
                "synonyms": ["项目名称"],
                "type": "string",
                "required": False,
            }
        },
        "table_data": {},
    }
    (tmp_path / "mapping.yaml").write_text(
        yaml.safe_dump(mapping, allow_unicode=True), encoding="utf-8"
    )

    project_types = {
        "schema_version": "1.0",
        "project_types": [
            {"id": "crc_301", "name": "301", "keywords": ["301"], "template": "t301.docx", "priority": 1},
            {"id": "crc_358", "name": "358", "keywords": ["358"], "template": "t358.docx", "priority": 10},
        ],
        "default": {"template": "default.docx", "match_threshold": 0.6, "detection_field": "project_name", "case_sensitive": False},
    }
    (tmp_path / "project_types.yaml").write_text(
        yaml.safe_dump(project_types, allow_unicode=True), encoding="utf-8"
    )

    detector = ProjectDetector(config_dir=str(tmp_path))
    excel_single_values = {"项目名称": "结直肠癌358基因检测"}

    result = detector.detect("no_keywords_in_filename.xlsx", excel_data=excel_single_values)
    assert result["detected"] is True
    assert result["project_type"] == "crc_358"


def test_detect_breaks_ties_by_priority(tmp_path):
    mapping = {"schema_version": "1.0", "single_values": {}, "table_data": {}}
    (tmp_path / "mapping.yaml").write_text(
        yaml.safe_dump(mapping, allow_unicode=True), encoding="utf-8"
    )

    project_types = {
        "schema_version": "1.0",
        "project_types": [
            {"id": "low", "name": "low", "keywords": ["x"], "template": "low.docx", "priority": 1},
            {"id": "high", "name": "high", "keywords": ["x"], "template": "high.docx", "priority": 10},
        ],
        "default": {"template": "default.docx", "match_threshold": 0.6, "detection_field": "project_name", "case_sensitive": False},
    }
    (tmp_path / "project_types.yaml").write_text(
        yaml.safe_dump(project_types, allow_unicode=True), encoding="utf-8"
    )

    detector = ProjectDetector(config_dir=str(tmp_path))
    result = detector.detect("x_in_filename.xlsx")
    assert result["detected"] is True
    assert result["project_type"] == "high"


def test_detect_supports_keyword_groups_with_and_logic(tmp_path):
    mapping = {"schema_version": "1.0", "single_values": {}, "table_data": {}}
    (tmp_path / "mapping.yaml").write_text(
        yaml.safe_dump(mapping, allow_unicode=True), encoding="utf-8"
    )

    project_types = {
        "schema_version": "1.0",
        "project_types": [
            {
                "id": "mlf_result",
                "name": "MLF result",
                "keyword_groups": [
                    {"any": ["mlf", "mlb"], "weight": 1},
                    {"any": ["result"], "weight": 1},
                ],
                "template": "t.docx",
                "priority": 1,
            }
        ],
        "default": {
            "template": "default.docx",
            "match_threshold": 0.6,
            "detection_field": "project_name",
            "case_sensitive": False,
        },
    }
    (tmp_path / "project_types.yaml").write_text(
        yaml.safe_dump(project_types, allow_unicode=True), encoding="utf-8"
    )

    detector = ProjectDetector(config_dir=str(tmp_path))

    # 只命中其中一组（result），权重得分=0.5 < 0.6，不应误识别
    result = detector.detect("only_result.xlsx")
    assert result["detected"] is False

    # 两组都命中（mlf + result），得分=1.0，应识别成功
    result = detector.detect("mlf_result.xlsx")
    assert result["detected"] is True
    assert result["project_type"] == "mlf_result"


def test_detect_supports_regex_patterns_in_keyword_groups(tmp_path):
    mapping = {"schema_version": "1.0", "single_values": {}, "table_data": {}}
    (tmp_path / "mapping.yaml").write_text(
        yaml.safe_dump(mapping, allow_unicode=True), encoding="utf-8"
    )

    project_types = {
        "schema_version": "1.0",
        "project_types": [
            {
                "id": "crc_358",
                "name": "358",
                "keyword_groups": [
                    {"any": [{"type": "regex", "pattern": r"(^|\D)358(\D|$)"}]}
                ],
                "template": "t358.docx",
                "priority": 1,
            }
        ],
        "default": {
            "template": "default.docx",
            "match_threshold": 0.6,
            "detection_field": "project_name",
            "case_sensitive": False,
        },
    }
    (tmp_path / "project_types.yaml").write_text(
        yaml.safe_dump(project_types, allow_unicode=True), encoding="utf-8"
    )

    detector = ProjectDetector(config_dir=str(tmp_path))

    result = detector.detect("abc_358_def.xlsx")
    assert result["detected"] is True

    # 358 前后都是数字时，不应匹配
    result = detector.detect("abc12358def.xlsx")
    assert result["detected"] is False
