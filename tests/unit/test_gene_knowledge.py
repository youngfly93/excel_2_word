"""Tests for gene knowledge module."""

import pytest
from pathlib import Path

from reportgen.knowledge import GeneKnowledgeProvider, MutationDescriptionGenerator

# 动态获取项目根目录（tests/unit/ -> tests/ -> project root）
PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestMutationDescriptionGenerator:
    """Tests for MutationDescriptionGenerator class."""

    @pytest.fixture
    def generator(self):
        return MutationDescriptionGenerator()

    def test_parse_c_hgvs_substitution(self, generator):
        """Test parsing substitution variants."""
        result = generator._parse_c_hgvs("c.844C>T")
        assert result["position"] == "844"
        assert result["ref"] == "C"
        assert result["alt"] == "T"
        assert result["variant_type"] == "substitution"

    def test_parse_c_hgvs_deletion(self, generator):
        """Test parsing deletion variants."""
        result = generator._parse_c_hgvs("c.1234delA")
        assert result["position"] == "1234"
        assert result["variant_type"] == "deletion"

    def test_parse_c_hgvs_insertion(self, generator):
        """Test parsing insertion variants."""
        result = generator._parse_c_hgvs("c.1234_1235insATG")
        assert result["variant_type"] == "insertion"

    def test_parse_c_hgvs_duplication(self, generator):
        """Test parsing duplication variants."""
        result = generator._parse_c_hgvs("c.1234dupA")
        assert result["variant_type"] == "duplication"

    def test_parse_c_hgvs_delins(self, generator):
        """Test parsing delins variants."""
        result = generator._parse_c_hgvs("c.1234_1236delinsATG")
        assert result["variant_type"] == "delins"

    def test_parse_p_hgvs_missense(self, generator):
        """Test parsing missense protein change."""
        result = generator._parse_p_hgvs("p.R282W")
        assert result["position"] == "282"
        assert result["ref_aa"] == "R"
        assert result["alt_aa"] == "W"
        assert result["mutation_type"] == "missense"

    def test_parse_p_hgvs_nonsense(self, generator):
        """Test parsing nonsense (stop) protein change."""
        result = generator._parse_p_hgvs("p.R282*")
        assert result["position"] == "282"
        assert result["mutation_type"] == "nonsense"

    def test_parse_p_hgvs_frameshift(self, generator):
        """Test parsing frameshift protein change."""
        result = generator._parse_p_hgvs("p.L300fs")
        assert result["mutation_type"] == "frameshift"

    def test_generate_missense_description(self, generator):
        """Test generating description for missense mutation."""
        desc = generator.generate("TP53", "c.844C>T", "p.R282W", 45.5)
        assert "TP53" in desc
        assert "c.844C>T" in desc
        assert "R282W" in desc or "282" in desc
        assert "45.5" in desc or "45.50" in desc

    def test_generate_nonsense_description(self, generator):
        """Test generating description for nonsense mutation."""
        desc = generator.generate("APC", "c.4348C>T", "p.R1450*", 30.0)
        assert "APC" in desc
        assert "无义突变" in desc or "终止" in desc

    def test_generate_frameshift_description(self, generator):
        """Test generating description for frameshift mutation."""
        desc = generator.generate("BRCA1", "c.5382_5383insC", "p.L1795fs", 25.0)
        assert "BRCA1" in desc
        assert "移码" in desc

    def test_generate_with_no_p_hgvs(self, generator):
        """Test generating description without protein change."""
        desc = generator.generate("NRAS", "c.181C>A", "--", 20.0)
        assert "NRAS" in desc
        assert "c.181C>A" in desc


class TestGeneKnowledgeProvider:
    """Tests for GeneKnowledgeProvider class."""

    @pytest.fixture
    def base_path(self):
        """Return base path for test data."""
        return PROJECT_ROOT

    @pytest.fixture
    def config(self, base_path):
        """Return test configuration."""
        return {
            "enabled": True,
            "gene_knowledge_db": {
                "enabled": True,
                "path": "2025.12.10/示例：+++自建肠癌基因数据库.xlsx",
                "sheets": {
                    "gene_analysis": "基因变异解析",
                    "drug_analysis": "用药提示解析",
                },
                "columns": {
                    "gene_name": "基因名称",
                    "gene_intro": "基因简介",
                    "mutation_analysis": "基因变异解析",
                },
            },
            "gene_transcript_db": {
                "enabled": True,
                "path": "2025.12.12/3-基因-转录本号-染色体信息.xls",
                "columns": {
                    "gene_name": "Genename",
                    "transcript": "Transcriptid",
                    "chromosome": "Chr",
                },
            },
        }

    @pytest.fixture
    def provider(self, config):
        """Create GeneKnowledgeProvider instance."""
        return GeneKnowledgeProvider(config)

    def test_provider_init(self, provider):
        """Test provider initialization."""
        assert provider is not None
        assert provider._loaded is False

    def test_load_with_valid_path(self, provider, base_path):
        """Test loading knowledge base with valid path."""
        result = provider.load(str(base_path))
        assert result is True
        assert provider._loaded is True

    def test_get_gene_intro(self, provider, base_path):
        """Test getting gene intro."""
        provider.load(str(base_path))
        intro = provider.get_gene_intro("KRAS")
        # Should return a non-empty string for a known gene
        assert isinstance(intro, str)

    def test_get_gene_analysis(self, provider, base_path):
        """Test getting gene analysis."""
        provider.load(str(base_path))
        analysis = provider.get_gene_analysis("TP53")
        assert isinstance(analysis, str)
        # 示例知识库中“基因变异解析”内容可能分散在 Unnamed:* 列；应能回填出非空解析文本
        assert "TP53基因编码的蛋白" in analysis or len(analysis.strip()) > 0

    def test_get_gene_transcript_info(self, provider, base_path):
        """Test getting gene transcript info."""
        provider.load(str(base_path))
        info = provider.get_gene_transcript_info("KRAS")
        assert isinstance(info, dict)
        if info:  # If found
            assert "name" in info or "transcript" in info or "chromosome" in info

    def test_build_gene_knowledge_section(self, provider, base_path):
        """Test building gene knowledge section."""
        provider.load(str(base_path))
        section = provider.build_gene_knowledge_section(
            gene="TP53",
            c_hgvs="c.844C>T",
            p_hgvs="p.R282W",
            frequency=38.5,
            has_drug=True,
            cancer_type="结直肠癌",
        )
        assert "gene" in section
        assert section["gene"] == "TP53"
        assert "header" in section
        assert "TP53" in section["header"]
        assert "mutation_desc" in section
        # 示例库可能含 {XX癌 ...} 占位符；应在构建章节时替换
        assert "{XX癌" not in section.get("mutation_analysis", "")

    def test_build_all_gene_knowledge_sections(self, provider, base_path):
        """Test building all gene knowledge sections."""
        provider.load(str(base_path))

        variants = [
            {
                "gene": "KRAS",
                "cHGVS": "c.35G>A",
                "pHGVS": "p.G12D",
                "frequency": "38.5%",
                "benefit_drugs": "西妥昔单抗",
                "caution_drugs": "--",
            },
            {
                "gene": "TP53",
                "cHGVS": "c.844C>T",
                "pHGVS": "p.R282W",
                "frequency": "45.5%",
                "benefit_drugs": "--",
                "caution_drugs": "--",
            },
        ]

        sections = provider.build_all_gene_knowledge_sections(variants)
        assert isinstance(sections, list)
        assert len(sections) == 2

        # Check first section
        assert sections[0]["gene"] == "KRAS"
        assert sections[0]["has_drug"] is True

        # Check second section
        assert sections[1]["gene"] == "TP53"
        assert sections[1]["has_drug"] is False


class TestGeneKnowledgeIntegration:
    """Integration tests for gene knowledge module."""

    @pytest.fixture
    def base_path(self):
        return PROJECT_ROOT

    def test_full_workflow(self, base_path):
        """Test full workflow from config to section generation."""
        config = {
            "enabled": True,
            "gene_knowledge_db": {
                "enabled": True,
                "path": "2025.12.10/示例：+++自建肠癌基因数据库.xlsx",
                "sheets": {
                    "gene_analysis": "基因变异解析",
                },
                "columns": {
                    "gene_name": "基因名称",
                    "gene_intro": "基因简介",
                    "mutation_analysis": "基因变异解析",
                },
            },
        }

        provider = GeneKnowledgeProvider(config)
        result = provider.load(str(base_path))

        if result:  # Only test if data exists
            # Generate a mutation description
            desc_gen = MutationDescriptionGenerator()
            desc = desc_gen.generate("KRAS", "c.35G>A", "p.G12D", 35.0)
            assert "KRAS" in desc
            assert "35" in desc

            # Build a knowledge section
            section = provider.build_gene_knowledge_section(
                gene="KRAS",
                c_hgvs="c.35G>A",
                p_hgvs="p.G12D",
                frequency=35.0,
                has_drug=True,
            )
            assert section["gene"] == "KRAS"
            assert "header_color" in section
