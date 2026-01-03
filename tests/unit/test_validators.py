"""
validators模块单元测试
"""

import pytest
from pathlib import Path
from reportgen.utils.validators import (
    validate_file_path,
    validate_excel_file,
    validate_docx_file,
    validate_field_value,
    validate_directory_writable,
    validate_patient_name,
    validate_sample_id
)


class TestValidateFilePath:
    """validate_file_path函数测试"""
    
    def test_empty_path(self):
        """测试空路径"""
        is_valid, error = validate_file_path('', must_exist=False)
        assert not is_valid
        assert "不能为空" in error
    
    def test_nonexistent_file_must_exist(self, tmp_path):
        """测试不存在的文件（must_exist=True）"""
        file_path = tmp_path / 'nonexistent.txt'
        is_valid, error = validate_file_path(str(file_path), must_exist=True)
        
        assert not is_valid
        assert "不存在" in error
    
    def test_nonexistent_file_may_exist(self, tmp_path):
        """测试不存在的文件（must_exist=False）"""
        file_path = tmp_path / 'future.txt'
        is_valid, error = validate_file_path(str(file_path), must_exist=False)
        
        assert is_valid
        assert error is None
    
    def test_valid_file(self, tmp_path):
        """测试有效文件"""
        file_path = tmp_path / 'test.txt'
        file_path.write_text('test content')
        
        is_valid, error = validate_file_path(str(file_path))
        assert is_valid
        assert error is None
    
    def test_directory_not_file(self, tmp_path):
        """测试目录（不是文件）"""
        is_valid, error = validate_file_path(str(tmp_path), must_exist=True)
        
        assert not is_valid
        assert "不是文件" in error
    
    def test_file_extension_match(self, tmp_path):
        """测试文件扩展名匹配"""
        file_path = tmp_path / 'test.xlsx'
        file_path.write_text('test')
        
        is_valid, error = validate_file_path(
            str(file_path),
            file_extensions=['.xlsx', '.xls']
        )
        
        assert is_valid
    
    def test_file_extension_mismatch(self, tmp_path):
        """测试文件扩展名不匹配"""
        file_path = tmp_path / 'test.txt'
        file_path.write_text('test')
        
        is_valid, error = validate_file_path(
            str(file_path),
            file_extensions=['.xlsx']
        )
        
        assert not is_valid
        assert "不支持的文件格式" in error


class TestValidateExcelFile:
    """validate_excel_file函数测试"""
    
    def test_valid_excel(self, tmp_path):
        """测试有效的Excel文件"""
        excel_file = tmp_path / 'test.xlsx'
        excel_file.write_bytes(b'x' * 1024)  # 1KB文件
        
        is_valid, error = validate_excel_file(str(excel_file))
        assert is_valid
    
    def test_empty_excel(self, tmp_path):
        """测试空Excel文件"""
        excel_file = tmp_path / 'empty.xlsx'
        excel_file.write_bytes(b'')
        
        is_valid, error = validate_excel_file(str(excel_file))
        
        assert not is_valid
        assert "为空" in error
    
    def test_excel_too_large(self, tmp_path):
        """测试过大的Excel文件"""
        excel_file = tmp_path / 'large.xlsx'
        # 创建101MB文件
        excel_file.write_bytes(b'x' * (101 * 1024 * 1024))
        
        is_valid, error = validate_excel_file(str(excel_file))
        
        assert not is_valid
        assert "过大" in error


class TestValidateDocxFile:
    """validate_docx_file函数测试"""
    
    def test_valid_docx(self, tmp_path):
        """测试有效的Docx文件"""
        docx_file = tmp_path / 'template.docx'
        docx_file.write_bytes(b'test content')
        
        is_valid, error = validate_docx_file(str(docx_file))
        assert is_valid
    
    def test_wrong_extension(self, tmp_path):
        """测试错误的文件扩展名"""
        file_path = tmp_path / 'document.doc'
        file_path.write_text('test')
        
        is_valid, error = validate_docx_file(str(file_path))
        
        assert not is_valid
        assert "不支持的文件格式" in error


class TestValidateFieldValue:
    """validate_field_value函数测试"""
    
    def test_required_field_missing(self):
        """测试必填字段缺失"""
        is_valid, error = validate_field_value(
            None, 'patient_name', 'string', required=True
        )
        
        assert not is_valid
        assert "缺失必填字段" in error
    
    def test_optional_field_missing(self):
        """测试可选字段缺失"""
        is_valid, error = validate_field_value(
            None, 'hospital', 'string', required=False
        )
        
        assert is_valid
    
    def test_string_type_valid(self):
        """测试字符串类型有效值"""
        is_valid, error = validate_field_value(
            '张三', 'patient_name', 'string', required=True
        )
        
        assert is_valid
    
    def test_string_type_too_long(self):
        """测试字符串过长"""
        long_string = 'x' * 501
        is_valid, error = validate_field_value(
            long_string, 'notes', 'string'
        )
        
        assert not is_valid
        assert "长度超过限制" in error
    
    def test_int_type_valid(self):
        """测试整数类型有效值"""
        is_valid, error = validate_field_value(
            55, 'age', 'int'
        )
        
        assert is_valid
    
    def test_int_type_min_value(self):
        """测试整数最小值约束"""
        is_valid, error = validate_field_value(
            -1, 'age', 'int', min_value=0
        )
        
        assert not is_valid
        assert "小于最小值" in error
    
    def test_float_type_valid(self):
        """测试浮点数类型有效值"""
        is_valid, error = validate_field_value(
            45.5, 'af', 'float'
        )
        
        assert is_valid
    
    def test_float_type_max_value(self):
        """测试浮点数最大值约束"""
        is_valid, error = validate_field_value(
            150.0, 'af', 'float', max_value=100.0
        )
        
        assert not is_valid
        assert "大于最大值" in error
    
    def test_date_type_valid(self):
        """测试日期类型有效值"""
        is_valid, error = validate_field_value(
            '2025-10-24', 'report_date', 'date'
        )
        
        assert is_valid
    
    def test_date_type_invalid_format(self):
        """测试日期类型无效格式"""
        is_valid, error = validate_field_value(
            '2025/10/24', 'report_date', 'date'
        )
        
        assert not is_valid
        assert "日期格式" in error


class TestValidateDirectoryWritable:
    """validate_directory_writable函数测试"""
    
    def test_writable_directory(self, tmp_path):
        """测试可写目录"""
        is_valid, error = validate_directory_writable(str(tmp_path))
        assert is_valid
    
    def test_nonexistent_directory(self, tmp_path):
        """测试不存在的目录"""
        dir_path = tmp_path / 'nonexistent'
        is_valid, error = validate_directory_writable(str(dir_path))
        
        assert not is_valid
        assert "不存在" in error
    
    def test_file_not_directory(self, tmp_path):
        """测试文件（不是目录）"""
        file_path = tmp_path / 'test.txt'
        file_path.write_text('test')
        
        is_valid, error = validate_directory_writable(str(file_path))
        
        assert not is_valid
        assert "不是目录" in error


class TestValidatePatientName:
    """validate_patient_name函数测试"""
    
    def test_valid_name(self):
        """测试有效的患者姓名"""
        is_valid, error = validate_patient_name('张三')
        assert is_valid
    
    def test_empty_name(self):
        """测试空姓名"""
        is_valid, error = validate_patient_name('')
        assert not is_valid
        assert "不能为空" in error
    
    def test_name_too_long(self):
        """测试姓名过长"""
        long_name = 'x' * 51
        is_valid, error = validate_patient_name(long_name)
        
        assert not is_valid
        assert "过长" in error


class TestValidateSampleId:
    """validate_sample_id函数测试"""
    
    def test_valid_sample_id(self):
        """测试有效的样本编号"""
        is_valid, error = validate_sample_id('TEST-2025-0001')
        assert is_valid
    
    def test_empty_sample_id(self):
        """测试空样本编号"""
        is_valid, error = validate_sample_id('')
        assert not is_valid
        assert "不能为空" in error


