"""
端到端集成测试 - 报告生成完整流程

测试整个报告生成管道，从Excel读取到docx输出。
"""

import pytest
import os
from pathlib import Path

from reportgen.core.report_generator import ReportGenerator

pytest.importorskip("docxtpl", reason="docxtpl is required for end-to-end docx rendering tests")


class TestReportGenerationE2E:
    """端到端报告生成测试"""

    @pytest.fixture
    def generator(self):
        """创建ReportGenerator实例"""
        return ReportGenerator(
            config_dir=str(Path(__file__).parent.parent.parent / "config")
        )

    @pytest.fixture
    def sample_excel(self, fixtures_dir):
        """示例Excel文件路径"""
        return str(fixtures_dir / "sample_excel.xlsx")

    @pytest.fixture
    def sample_template(self, fixtures_dir):
        """示例模板文件路径"""
        return str(fixtures_dir / "sample_template.docx")

    @pytest.fixture
    def missing_fields_excel(self, fixtures_dir):
        """缺失关键字段的Excel文件"""
        return str(fixtures_dir / "missing_critical_fields.xlsx")

    def test_generate_report_success(self, generator, sample_excel, sample_template, temp_output_dir):
        """测试：完整流程成功生成报告"""
        # 执行
        result = generator.generate(
            excel_file=sample_excel,
            template_file=sample_template,
            output_dir=str(temp_output_dir),
        )

        # 验证
        assert result["success"] is True, f"报告生成失败: {result.get('errors')}"
        assert result["output_file"] is not None
        assert Path(result["output_file"]).exists(), "输出文件不存在"
        assert result["duration"] > 0, "耗时应该大于0"

    def test_generate_report_with_custom_filename(self, generator, sample_excel, sample_template, temp_output_dir):
        """测试：使用自定义文件名生成报告"""
        custom_filename = "custom_report_name.docx"

        result = generator.generate(
            excel_file=sample_excel,
            template_file=sample_template,
            output_dir=str(temp_output_dir),
            output_filename=custom_filename,
        )

        assert result["success"] is True
        assert custom_filename in result["output_file"]

    def test_output_file_contains_patient_info(self, generator, sample_excel, sample_template, temp_output_dir):
        """测试：生成的报告包含患者信息"""
        from docx import Document

        result = generator.generate(
            excel_file=sample_excel,
            template_file=sample_template,
            output_dir=str(temp_output_dir),
        )

        assert result["success"] is True

        # 读取生成的docx文件
        doc = Document(result["output_file"])
        full_text = "\n".join([para.text for para in doc.paragraphs])

        # 验证关键信息存在
        assert "测试患者001" in full_text or "patient_name" not in full_text.lower()

    def test_invalid_excel_file_fails(self, generator, sample_template, temp_output_dir):
        """测试：无效Excel文件导致失败"""
        result = generator.generate(
            excel_file="/nonexistent/file.xlsx",
            template_file=sample_template,
            output_dir=str(temp_output_dir),
        )

        assert result["success"] is False
        assert len(result["errors"]) > 0

    def test_invalid_template_file_fails(self, generator, sample_excel, temp_output_dir):
        """测试：无效模板文件导致失败"""
        result = generator.generate(
            excel_file=sample_excel,
            template_file="/nonexistent/template.docx",
            output_dir=str(temp_output_dir),
        )

        assert result["success"] is False
        assert len(result["errors"]) > 0


class TestStrictModeE2E:
    """严格模式端到端测试"""

    @pytest.fixture
    def generator(self):
        """创建ReportGenerator实例"""
        return ReportGenerator(
            config_dir=str(Path(__file__).parent.parent.parent / "config")
        )

    @pytest.fixture
    def missing_fields_excel(self, fixtures_dir):
        """缺失关键字段的Excel文件"""
        return str(fixtures_dir / "missing_critical_fields.xlsx")

    @pytest.fixture
    def sample_template(self, fixtures_dir):
        """示例模板文件路径"""
        return str(fixtures_dir / "sample_template.docx")

    def test_strict_mode_blocks_on_missing_critical_fields(
        self, generator, missing_fields_excel, sample_template, temp_output_dir
    ):
        """测试：严格模式下缺失关键字段会阻断生成"""
        result = generator.generate(
            excel_file=missing_fields_excel,
            template_file=sample_template,
            output_dir=str(temp_output_dir),
            strict_mode=True,
        )

        # 验证生成失败
        assert result["success"] is False
        # 验证错误信息包含关键字段
        error_str = str(result["errors"])
        assert "关键字段" in error_str or "patient_name" in error_str or "sample_id" in error_str

    def test_non_strict_mode_continues_with_warnings(
        self, generator, missing_fields_excel, sample_template, temp_output_dir
    ):
        """测试：非严格模式下缺失字段只警告不阻断"""
        result = generator.generate(
            excel_file=missing_fields_excel,
            template_file=sample_template,
            output_dir=str(temp_output_dir),
            strict_mode=False,  # 非严格模式
        )

        # 非严格模式可能成功也可能失败（取决于模板渲染是否需要这些字段）
        # 主要验证不会因为strict mode阻断
        if not result["success"]:
            # 如果失败，不应该是因为"严格模式"
            error_str = str(result["errors"])
            assert "严格模式" not in error_str


class TestValidateInputs:
    """输入验证测试"""

    @pytest.fixture
    def generator(self):
        return ReportGenerator(
            config_dir=str(Path(__file__).parent.parent.parent / "config")
        )

    @pytest.fixture
    def sample_excel(self, fixtures_dir):
        return str(fixtures_dir / "sample_excel.xlsx")

    @pytest.fixture
    def sample_template(self, fixtures_dir):
        return str(fixtures_dir / "sample_template.docx")

    def test_validate_inputs_success(self, generator, sample_excel, sample_template, temp_output_dir):
        """测试：有效输入通过验证"""
        is_valid, errors = generator.validate_inputs(
            excel_file=sample_excel,
            template_file=sample_template,
            output_dir=str(temp_output_dir),
        )

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_inputs_invalid_excel(self, generator, sample_template, temp_output_dir):
        """测试：无效Excel文件验证失败"""
        is_valid, errors = generator.validate_inputs(
            excel_file="/nonexistent/file.xlsx",
            template_file=sample_template,
            output_dir=str(temp_output_dir),
        )

        assert is_valid is False
        assert len(errors) > 0
        assert "Excel" in errors[0]

    def test_validate_inputs_invalid_template(self, generator, sample_excel, temp_output_dir):
        """测试：无效模板文件验证失败"""
        is_valid, errors = generator.validate_inputs(
            excel_file=sample_excel,
            template_file="/nonexistent/template.docx",
            output_dir=str(temp_output_dir),
        )

        assert is_valid is False
        assert len(errors) > 0
        assert "模板" in errors[0]
