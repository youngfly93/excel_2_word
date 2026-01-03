"""
logger模块单元测试
"""

import pytest
import json
import logging
from pathlib import Path
from reportgen.utils.logger import StructuredLogger, get_logger


class TestStructuredLogger:
    """StructuredLogger类的单元测试"""
    
    def test_init_default(self):
        """测试默认初始化"""
        logger = StructuredLogger()
        
        assert logger.logger.name == 'reportgen'
        assert logger.logger.level == logging.INFO
    
    def test_init_with_level(self):
        """测试指定日志级别初始化"""
        logger = StructuredLogger(level='DEBUG')
        
        assert logger.logger.level == logging.DEBUG
    
    def test_init_with_log_file(self, tmp_path):
        """测试指定日志文件初始化"""
        log_file = tmp_path / 'test.log'
        logger = StructuredLogger(log_file=str(log_file))
        
        # 检查日志文件是否创建
        logger.info("Test message")
        
        assert log_file.exists()
    
    def test_log_event_json_format(self, tmp_path):
        """测试JSON格式的事件日志"""
        log_file = tmp_path / 'events.log'
        logger = StructuredLogger(
            log_file=str(log_file),
            console_output=False,
            json_format=True
        )
        
        logger.log_event(
            'test_event',
            level='INFO',
            key1='value1',
            key2=123
        )
        
        # 读取日志文件
        log_content = log_file.read_text()
        log_entry = json.loads(log_content.strip())
        
        assert log_entry['event_type'] == 'test_event'
        assert log_entry['key1'] == 'value1'
        assert log_entry['key2'] == 123
        assert 'timestamp' in log_entry
    
    def test_log_event_text_format(self, tmp_path):
        """测试文本格式的事件日志"""
        log_file = tmp_path / 'events.log'
        logger = StructuredLogger(
            log_file=str(log_file),
            console_output=False,
            json_format=False
        )
        
        logger.log_event(
            'test_event',
            level='INFO',
            key1='value1'
        )
        
        # 读取日志文件
        log_content = log_file.read_text()
        
        assert 'test_event' in log_content
        assert 'key1=value1' in log_content
    
    def test_info_method(self, tmp_path):
        """测试info方法"""
        log_file = tmp_path / 'info.log'
        logger = StructuredLogger(
            log_file=str(log_file),
            console_output=False,
            json_format=True
        )
        
        logger.info("Info message", extra_field="extra_value")
        
        log_content = log_file.read_text()
        log_entry = json.loads(log_content.strip())
        
        assert log_entry['level'] == 'INFO'
        assert log_entry['message'] == 'Info message'
        assert log_entry['extra_field'] == 'extra_value'
    
    def test_debug_method(self, tmp_path):
        """测试debug方法"""
        log_file = tmp_path / 'debug.log'
        logger = StructuredLogger(
            log_file=str(log_file),
            console_output=False,
            json_format=True,
            level='DEBUG'
        )
        
        logger.debug("Debug message")
        
        log_content = log_file.read_text()
        log_entry = json.loads(log_content.strip())
        
        assert log_entry['level'] == 'DEBUG'
        assert log_entry['message'] == 'Debug message'
    
    def test_warning_method(self, tmp_path):
        """测试warning方法"""
        log_file = tmp_path / 'warning.log'
        logger = StructuredLogger(
            log_file=str(log_file),
            console_output=False,
            json_format=True
        )
        
        logger.warning("Warning message")
        
        log_content = log_file.read_text()
        log_entry = json.loads(log_content.strip())
        
        assert log_entry['level'] == 'WARNING'
        assert log_entry['message'] == 'Warning message'
    
    def test_error_method(self, tmp_path):
        """测试error方法"""
        log_file = tmp_path / 'error.log'
        logger = StructuredLogger(
            log_file=str(log_file),
            console_output=False,
            json_format=True
        )
        
        logger.error("Error message", error_code=500)
        
        log_content = log_file.read_text()
        log_entry = json.loads(log_content.strip())
        
        assert log_entry['level'] == 'ERROR'
        assert log_entry['message'] == 'Error message'
        assert log_entry['error_code'] == 500
    
    def test_critical_method(self, tmp_path):
        """测试critical方法"""
        log_file = tmp_path / 'critical.log'
        logger = StructuredLogger(
            log_file=str(log_file),
            console_output=False,
            json_format=True
        )
        
        logger.critical("Critical message")
        
        log_content = log_file.read_text()
        log_entry = json.loads(log_content.strip())
        
        assert log_entry['level'] == 'CRITICAL'
        assert log_entry['message'] == 'Critical message'
    
    def test_multiple_log_entries(self, tmp_path):
        """测试多条日志记录"""
        log_file = tmp_path / 'multiple.log'
        logger = StructuredLogger(
            log_file=str(log_file),
            console_output=False,
            json_format=True
        )
        
        logger.info("First message")
        logger.warning("Second message")
        logger.error("Third message")
        
        log_content = log_file.read_text()
        log_lines = log_content.strip().split('\n')
        
        assert len(log_lines) == 3
        
        # 验证每条日志
        for line in log_lines:
            log_entry = json.loads(line)
            assert 'timestamp' in log_entry
            assert 'level' in log_entry
            assert 'message' in log_entry


class TestGetLogger:
    """get_logger工厂函数测试"""
    
    def test_get_logger_default(self):
        """测试默认参数"""
        logger = get_logger()
        
        assert isinstance(logger, StructuredLogger)
        assert logger.logger.name == 'reportgen'
    
    def test_get_logger_with_params(self, tmp_path):
        """测试带参数"""
        log_file = tmp_path / 'factory.log'
        logger = get_logger(
            name='test_logger',
            log_file=str(log_file),
            level='DEBUG'
        )
        
        assert isinstance(logger, StructuredLogger)
        assert logger.logger.name == 'test_logger'
        assert logger.logger.level == logging.DEBUG
        
        # 验证日志文件创建
        logger.info("Test message")
        assert log_file.exists()


