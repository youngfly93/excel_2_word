"""Pytest配置和通用fixtures"""

import pytest
import os
from pathlib import Path


@pytest.fixture
def fixtures_dir():
    """返回测试fixtures目录路径"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_excel_path(fixtures_dir):
    """返回示例Excel文件路径"""
    return fixtures_dir / "sample_excel.xlsx"


@pytest.fixture
def sample_template_path(fixtures_dir):
    """返回示例模板文件路径"""
    return fixtures_dir / "sample_template.docx"


@pytest.fixture
def temp_output_dir(tmp_path):
    """创建临时输出目录"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def sample_patient_data():
    """返回示例患者数据"""
    return {
        "patient_name": "测试患者001",
        "sample_id": "TEST-2025-0001",
        "gender": "男",
        "age": 55,
        "hospital": "测试医院",
        "report_date": "2025-10-24",
    }


@pytest.fixture
def sample_variant_data():
    """返回示例变异数据"""
    return [
        {
            "gene": "TP53",
            "variant": "c.742C>T",
            "protein": "p.R248W",
            "af": 45.5,
            "depth": 1200,
            "type": "SNV",
        },
        {
            "gene": "KRAS",
            "variant": "c.35G>A",
            "protein": "p.G12D",
            "af": 38.2,
            "depth": 1500,
            "type": "SNV",
        },
    ]

