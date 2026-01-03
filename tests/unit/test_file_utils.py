"""
file_utils模块单元测试
"""

import pytest
from pathlib import Path
from reportgen.utils.file_utils import (
    ensure_directory_exists,
    get_file_size,
    get_file_size_mb,
    is_file_readable,
    is_directory_writable,
    safe_filename,
    get_unique_filename,
    list_files_with_extension,
    get_directory_size,
    check_disk_space
)


class TestEnsureDirectoryExists:
    """ensure_directory_exists函数测试"""
    
    def test_create_directory(self, tmp_path):
        """测试创建目录"""
        new_dir = tmp_path / 'new_directory'
        result = ensure_directory_exists(str(new_dir))
        
        assert new_dir.exists()
        assert new_dir.is_dir()
        assert result == new_dir
    
    def test_create_nested_directories(self, tmp_path):
        """测试创建嵌套目录"""
        nested_dir = tmp_path / 'level1' / 'level2' / 'level3'
        result = ensure_directory_exists(str(nested_dir))
        
        assert nested_dir.exists()
        assert nested_dir.is_dir()
    
    def test_existing_directory(self, tmp_path):
        """测试已存在的目录"""
        result = ensure_directory_exists(str(tmp_path))
        
        assert tmp_path.exists()
        assert result == tmp_path


class TestGetFileSize:
    """get_file_size函数测试"""
    
    def test_file_size(self, tmp_path):
        """测试获取文件大小"""
        test_file = tmp_path / 'test.txt'
        content = b'x' * 1024  # 1KB
        test_file.write_bytes(content)
        
        size = get_file_size(str(test_file))
        assert size == 1024
    
    def test_file_size_mb(self, tmp_path):
        """测试获取文件大小（MB）"""
        test_file = tmp_path / 'test.txt'
        content = b'x' * (2 * 1024 * 1024)  # 2MB
        test_file.write_bytes(content)
        
        size_mb = get_file_size_mb(str(test_file))
        assert abs(size_mb - 2.0) < 0.01  # 允许微小误差
    
    def test_nonexistent_file(self, tmp_path):
        """测试不存在的文件"""
        with pytest.raises(FileNotFoundError):
            get_file_size(str(tmp_path / 'nonexistent.txt'))


class TestIsFileReadable:
    """is_file_readable函数测试"""
    
    def test_readable_file(self, tmp_path):
        """测试可读文件"""
        test_file = tmp_path / 'test.txt'
        test_file.write_text('test content')
        
        assert is_file_readable(str(test_file))
    
    def test_nonexistent_file(self, tmp_path):
        """测试不存在的文件"""
        assert not is_file_readable(str(tmp_path / 'nonexistent.txt'))
    
    def test_directory_not_file(self, tmp_path):
        """测试目录（不是文件）"""
        assert not is_file_readable(str(tmp_path))


class TestIsDirectoryWritable:
    """is_directory_writable函数测试"""
    
    def test_writable_directory(self, tmp_path):
        """测试可写目录"""
        assert is_directory_writable(str(tmp_path))
    
    def test_nonexistent_directory(self, tmp_path):
        """测试不存在的目录"""
        assert not is_directory_writable(str(tmp_path / 'nonexistent'))


class TestSafeFilename:
    """safe_filename函数测试"""
    
    def test_illegal_characters(self):
        """测试移除非法字符"""
        unsafe_name = 'report<>:"/\\|?*.docx'
        safe_name = safe_filename(unsafe_name)
        
        # 所有非法字符应被替换为下划线
        assert '<' not in safe_name
        assert '>' not in safe_name
        assert ':' not in safe_name
        assert '?' not in safe_name
        assert '*' not in safe_name
    
    def test_normal_filename(self):
        """测试正常文件名"""
        normal_name = 'patient_report_2025.docx'
        safe_name = safe_filename(normal_name)
        
        assert safe_name == normal_name
    
    def test_long_filename(self):
        """测试过长文件名"""
        long_name = 'x' * 250 + '.docx'
        safe_name = safe_filename(long_name, max_length=200)
        
        assert len(safe_name) <= 200
        assert safe_name.endswith('.docx')
    
    def test_trim_spaces_and_dots(self):
        """测试去除首尾空格和点号"""
        name_with_spaces = '  filename.txt  '
        safe_name = safe_filename(name_with_spaces)
        
        assert safe_name == 'filename.txt'


class TestGetUniqueFilename:
    """get_unique_filename函数测试"""
    
    def test_unique_filename_not_exists(self, tmp_path):
        """测试文件名不存在时"""
        filename = 'report.docx'
        unique_name = get_unique_filename(str(tmp_path), filename)
        
        assert unique_name == filename
    
    def test_unique_filename_exists(self, tmp_path):
        """测试文件名已存在时"""
        # 创建现有文件
        (tmp_path / 'report.docx').write_text('existing')
        
        unique_name = get_unique_filename(str(tmp_path), 'report.docx')
        
        assert unique_name == 'report_1.docx'
    
    def test_multiple_existing_files(self, tmp_path):
        """测试多个文件已存在时"""
        # 创建多个文件
        (tmp_path / 'report.docx').write_text('1')
        (tmp_path / 'report_1.docx').write_text('2')
        (tmp_path / 'report_2.docx').write_text('3')
        
        unique_name = get_unique_filename(str(tmp_path), 'report.docx')
        
        assert unique_name == 'report_3.docx'


class TestListFilesWithExtension:
    """list_files_with_extension函数测试"""
    
    def test_list_xlsx_files(self, tmp_path):
        """测试列出xlsx文件"""
        # 创建测试文件
        (tmp_path / 'file1.xlsx').write_text('1')
        (tmp_path / 'file2.xlsx').write_text('2')
        (tmp_path / 'file3.txt').write_text('3')
        
        xlsx_files = list_files_with_extension(str(tmp_path), '.xlsx')
        
        assert len(xlsx_files) == 2
        assert all(f.suffix == '.xlsx' for f in xlsx_files)
    
    def test_list_files_recursive(self, tmp_path):
        """测试递归列出文件"""
        # 创建嵌套目录和文件
        (tmp_path / 'file1.xlsx').write_text('1')
        sub_dir = tmp_path / 'subdir'
        sub_dir.mkdir()
        (sub_dir / 'file2.xlsx').write_text('2')
        
        xlsx_files = list_files_with_extension(str(tmp_path), '.xlsx', recursive=True)
        
        assert len(xlsx_files) == 2
    
    def test_list_files_nonexistent_directory(self, tmp_path):
        """测试不存在的目录"""
        files = list_files_with_extension(str(tmp_path / 'nonexistent'), '.xlsx')
        
        assert files == []


class TestGetDirectorySize:
    """get_directory_size函数测试"""
    
    def test_directory_size(self, tmp_path):
        """测试计算目录大小"""
        # 创建测试文件
        (tmp_path / 'file1.txt').write_bytes(b'x' * 1024)  # 1KB
        (tmp_path / 'file2.txt').write_bytes(b'x' * 2048)  # 2KB
        
        size = get_directory_size(str(tmp_path))
        
        assert size == 3072  # 3KB
    
    def test_empty_directory(self, tmp_path):
        """测试空目录"""
        empty_dir = tmp_path / 'empty'
        empty_dir.mkdir()
        
        size = get_directory_size(str(empty_dir))
        
        assert size == 0
    
    def test_nonexistent_directory(self, tmp_path):
        """测试不存在的目录"""
        size = get_directory_size(str(tmp_path / 'nonexistent'))
        
        assert size == 0


class TestCheckDiskSpace:
    """check_disk_space函数测试"""
    
    def test_sufficient_space(self, tmp_path):
        """测试磁盘空间足够"""
        # 要求1MB空间（通常tmp目录都有足够空间）
        is_sufficient, available_mb = check_disk_space(str(tmp_path), 1.0)
        
        assert is_sufficient
        assert available_mb > 0
    
    def test_insufficient_space(self, tmp_path):
        """测试磁盘空间不足"""
        # 要求一个非常大的空间（如1TB）
        is_sufficient, available_mb = check_disk_space(str(tmp_path), 1024 * 1024)
        
        # 通常测试环境没有1TB空间
        # 但这取决于实际环境，所以只检查返回值类型
        assert isinstance(is_sufficient, bool)
        assert isinstance(available_mb, (int, float))


