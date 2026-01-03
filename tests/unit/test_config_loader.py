"""
ConfigLoader单元测试
"""

import pytest
import yaml
from pathlib import Path
from reportgen.config.loader import ConfigLoader


class TestConfigLoader:
    """ConfigLoader类的单元测试"""
    
    def test_init(self, tmp_path):
        """测试初始化"""
        loader = ConfigLoader(config_dir=str(tmp_path))
        assert loader.config_dir == tmp_path
    
    def test_load_yaml_success(self, tmp_path):
        """测试成功加载YAML文件"""
        # 创建测试YAML文件
        test_file = tmp_path / 'test.yaml'
        test_data = {'key1': 'value1', 'key2': {'nested': 'value2'}}
        
        with open(test_file, 'w', encoding='utf-8') as f:
            yaml.dump(test_data, f)
        
        loader = ConfigLoader(config_dir=str(tmp_path))
        result = loader.load_yaml(str(test_file))
        
        assert result == test_data
    
    def test_load_yaml_file_not_found(self, tmp_path):
        """测试加载不存在的文件"""
        loader = ConfigLoader(config_dir=str(tmp_path))
        
        with pytest.raises(FileNotFoundError):
            loader.load_yaml(str(tmp_path / 'nonexistent.yaml'))
    
    def test_load_yaml_invalid_format(self, tmp_path):
        """测试加载无效YAML格式"""
        # 创建无效的YAML文件
        test_file = tmp_path / 'invalid.yaml'
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("invalid: yaml: : content")
        
        loader = ConfigLoader(config_dir=str(tmp_path))
        
        with pytest.raises(yaml.YAMLError):
            loader.load_yaml(str(test_file))
    
    def test_load_mapping_config(self, tmp_path):
        """测试加载映射配置"""
        # 创建mapping.yaml
        mapping_data = {
            'single_values': {
                'patient_name': {
                    'synonyms': ['患者姓名', '姓名'],
                    'type': 'string',
                    'required': True
                }
            },
            'table_data': {
                'variants': {
                    'sheet_name': '变异明细',
                    'columns': {}
                }
            }
        }
        
        mapping_file = tmp_path / 'mapping.yaml'
        with open(mapping_file, 'w', encoding='utf-8') as f:
            yaml.dump(mapping_data, f)
        
        loader = ConfigLoader(config_dir=str(tmp_path))
        config = loader.load_mapping_config()
        
        assert 'single_values' in config
        assert 'table_data' in config
        assert 'patient_name' in config['single_values']
    
    def test_load_project_types_config(self, tmp_path):
        """测试加载项目类型配置"""
        # 创建project_types.yaml
        types_data = {
            'project_types': [
                {
                    'id': 'crc_301',
                    'name': '结直肠癌301基因',
                    'keywords': ['301', '基因'],
                    'template': 'template.docx'
                }
            ]
        }
        
        types_file = tmp_path / 'project_types.yaml'
        with open(types_file, 'w', encoding='utf-8') as f:
            yaml.dump(types_data, f)
        
        loader = ConfigLoader(config_dir=str(tmp_path))
        config = loader.load_project_types_config()
        
        assert 'project_types' in config
        assert len(config['project_types']) == 1
    
    def test_load_settings_config_missing_file(self, tmp_path):
        """测试加载不存在的设置文件"""
        loader = ConfigLoader(config_dir=str(tmp_path))
        config = loader.load_settings_config()
        
        # 应该返回空字典而不是抛出异常
        assert config == {}
    
    def test_get_mapping_for_variable(self, tmp_path):
        """测试获取变量映射"""
        mapping_data = {
            'single_values': {
                'patient_name': {
                    'synonyms': ['患者姓名'],
                    'type': 'string'
                }
            },
            'table_data': {}
        }
        
        mapping_file = tmp_path / 'mapping.yaml'
        with open(mapping_file, 'w', encoding='utf-8') as f:
            yaml.dump(mapping_data, f)
        
        loader = ConfigLoader(config_dir=str(tmp_path))
        mapping = loader.get_mapping_for_variable('patient_name')
        
        assert mapping is not None
        assert mapping['type'] == 'string'
    
    def test_get_project_types(self, tmp_path):
        """测试获取项目类型列表"""
        types_data = {
            'project_types': [
                {'id': 'type1', 'name': 'Type 1'},
                {'id': 'type2', 'name': 'Type 2'}
            ]
        }
        
        types_file = tmp_path / 'project_types.yaml'
        with open(types_file, 'w', encoding='utf-8') as f:
            yaml.dump(types_data, f)
        
        loader = ConfigLoader(config_dir=str(tmp_path))
        types = loader.get_project_types()
        
        assert len(types) == 2
        assert types[0]['id'] == 'type1'
    
    def test_get_setting(self, tmp_path):
        """测试获取设置值"""
        settings_data = {
            'logging': {
                'level': 'DEBUG'
            },
            'simple_key': 'value'
        }
        
        settings_file = tmp_path / 'settings.yaml'
        with open(settings_file, 'w', encoding='utf-8') as f:
            yaml.dump(settings_data, f)
        
        loader = ConfigLoader(config_dir=str(tmp_path))
        
        # 测试嵌套键
        assert loader.get_setting('logging.level') == 'DEBUG'
        
        # 测试简单键
        assert loader.get_setting('simple_key') == 'value'
        
        # 测试不存在的键（使用默认值）
        assert loader.get_setting('nonexistent', 'default') == 'default'
    
    def test_validate_mapping_config(self, tmp_path):
        """测试验证映射配置"""
        # 创建有效的配置
        mapping_data = {
            'single_values': {
                'patient_name': {
                    'synonyms': ['患者姓名'],
                    'type': 'string',
                    'required': True
                }
            },
            'table_data': {
                'variants': {
                    'sheet_name': '变异明细',
                    'columns': {
                        'gene': {
                            'synonyms': ['基因'],
                            'type': 'string'
                        }
                    }
                }
            }
        }
        
        mapping_file = tmp_path / 'mapping.yaml'
        with open(mapping_file, 'w', encoding='utf-8') as f:
            yaml.dump(mapping_data, f)
        
        loader = ConfigLoader(config_dir=str(tmp_path))
        is_valid, errors = loader.validate_mapping_config()
        
        assert is_valid
        assert len(errors) == 0


