"""
Unit and integration tests for ReportOrchestrator.

测试覆盖:
1. 配置加载
2. 数据提取和验证
3. 报告生成流程
4. 端到端集成测试

使用Mock避免实际API调用和文件操作
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.orchestrator import ReportOrchestrator
from src.config_loader import TemplateConfig
from src.ai_generator import APIConfig
from src.models import SDGResponse, CompanyImpactData, ImpactMechanism
from datetime import datetime


# ==================== Fixtures ====================

@pytest.fixture
def api_config():
    """测试用API配置"""
    return APIConfig(
        endpoint="https://test.api.com",
        api_key="test-key",
        model_name="claude-sonnet-4-5"
    )


@pytest.fixture
def config_path():
    """配置文件路径"""
    return "config/template_mapping.yaml"


@pytest.fixture
def sample_sdg_response():
    """示例SDG问卷响应"""
    return SDGResponse(
        timestamp=datetime.now(),
        company_name="TestCompany",
        contact_name="John Doe",
        sdg_goals="Goal 1, Goal 2",
        implementation_description="Implementation plan description"
    )


@pytest.fixture
def sample_impact_data():
    """示例影响评估数据"""
    mechanisms = [
        ImpactMechanism(
            stakeholder_affected="Employees",
            mechanism="Training programs",
            driving_variable="Participation rate",
            type_of_impact="Positive",
            positive_negative="Positive",
            method="Survey",
            value=100.0,
            unit="people"
        )
    ]

    return CompanyImpactData(
        company_name="TestCompany",
        sdg_questionnaire_response="Response 1",
        alternative_scenario="Alternative scenario description",
        stakeholders=["Employees", "Customers"],
        mechanisms=mechanisms
    )


# ==================== 配置加载测试 ====================

class TestTemplateConfig:
    """测试配置加载"""

    def test_load_config_success(self, config_path):
        """测试成功加载配置"""
        config = TemplateConfig(config_path)

        assert config is not None
        assert len(config.get_insert_rules()) > 0
        assert config.template_info is not None

    def test_get_template_path(self, config_path):
        """测试获取模板路径"""
        config = TemplateConfig(config_path)
        template_path = config.get_template_path()

        assert template_path is not None
        assert "影响评估方法论" in template_path

    def test_get_insert_rules(self, config_path):
        """测试获取插入规则"""
        config = TemplateConfig(config_path)
        rules = config.get_insert_rules()

        assert len(rules) == 4  # 配置文件中有4条规则
        assert rules[0].name == "Company Overview"

    def test_get_output_filename(self, config_path):
        """测试生成输出文件名"""
        config = TemplateConfig(config_path)
        filename = config.get_output_filename("TestCo", "20240101")

        assert "TestCo" in filename
        assert "20240101" in filename
        assert filename.endswith(".docx")


# ==================== ReportOrchestrator基础测试 ====================

class TestReportOrchestratorInit:
    """测试ReportOrchestrator初始化"""

    @patch('src.orchestrator.DataExtractor')
    @patch('src.orchestrator.AITextGenerator')
    def test_initialization(
        self,
        mock_ai_generator,
        mock_data_extractor,
        config_path,
        api_config
    ):
        """测试初始化"""
        orchestrator = ReportOrchestrator(
            data_dir=".",
            config_path=config_path,
            api_config=api_config
        )

        assert orchestrator is not None
        assert orchestrator.config is not None
        assert orchestrator.data_extractor is not None
        assert orchestrator.ai_generator is not None


# ==================== 数据验证测试 ====================

class TestDataValidation:
    """测试数据验证"""

    @patch('src.orchestrator.DataExtractor')
    @patch('src.orchestrator.AITextGenerator')
    def test_validate_data_success(
        self,
        mock_ai_generator,
        mock_data_extractor,
        config_path,
        api_config,
        sample_sdg_response,
        sample_impact_data
    ):
        """测试成功的数据验证"""
        orchestrator = ReportOrchestrator(
            data_dir=".",
            config_path=config_path,
            api_config=api_config
        )

        result = orchestrator._validate_data(
            sample_sdg_response,
            sample_impact_data
        )

        assert result.is_valid is True
        assert len(result.errors) == 0

    @patch('src.orchestrator.DataExtractor')
    @patch('src.orchestrator.AITextGenerator')
    def test_validate_data_name_mismatch(
        self,
        mock_ai_generator,
        mock_data_extractor,
        config_path,
        api_config,
        sample_sdg_response,
        sample_impact_data
    ):
        """测试公司名称不匹配的情况"""
        # 修改一个公司名称使其不匹配
        sample_impact_data.company_name = "DifferentCompany"

        orchestrator = ReportOrchestrator(
            data_dir=".",
            config_path=config_path,
            api_config=api_config
        )

        result = orchestrator._validate_data(
            sample_sdg_response,
            sample_impact_data
        )

        assert result.is_valid is False
        assert len(result.errors) > 0


# ==================== 辅助方法测试 ====================

class TestHelperMethods:
    """测试辅助方法"""

    @patch('src.orchestrator.DataExtractor')
    @patch('src.orchestrator.AITextGenerator')
    def test_find_sdg_response(
        self,
        mock_ai_generator,
        mock_data_extractor,
        config_path,
        api_config,
        sample_sdg_response
    ):
        """测试查找SDG响应"""
        orchestrator = ReportOrchestrator(
            data_dir=".",
            config_path=config_path,
            api_config=api_config
        )

        responses = [sample_sdg_response]
        found = orchestrator._find_sdg_response(responses, "TestCompany")

        assert found is not None
        assert found.company_name == "TestCompany"

    @patch('src.orchestrator.DataExtractor')
    @patch('src.orchestrator.AITextGenerator')
    def test_fill_template(
        self,
        mock_ai_generator,
        mock_data_extractor,
        config_path,
        api_config
    ):
        """测试模板填充"""
        orchestrator = ReportOrchestrator(
            data_dir=".",
            config_path=config_path,
            api_config=api_config
        )

        template = "Company: {name}, Type: {type}"
        data = {"name": "TestCo", "type": "Tech"}

        result = orchestrator._fill_template(template, data)

        assert "Company: TestCo" in result
        assert "Type: Tech" in result


# ==================== 完整流程测试(Mock) ====================

class TestReportGenerationMocked:
    """测试报告生成(使用Mock)"""

    @patch('src.orchestrator.WordTemplateHandler')
    @patch('src.orchestrator.DataExtractor')
    @patch('src.orchestrator.AITextGenerator')
    def test_generate_report_mocked(
        self,
        mock_ai_generator_class,
        mock_data_extractor_class,
        mock_template_handler_class,
        config_path,
        api_config,
        sample_sdg_response,
        sample_impact_data
    ):
        """测试完整的报告生成流程(Mock)"""

        # 配置DataExtractor Mock
        mock_data_extractor = MagicMock()
        mock_data_extractor.extract_sdg_questionnaire.return_value = [sample_sdg_response]
        mock_data_extractor.extract_impact_mechanisms.return_value = [sample_impact_data]
        mock_data_extractor_class.return_value = mock_data_extractor

        # 配置AITextGenerator Mock
        mock_ai_generator = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.metrics = {"generated_text": "AI generated content"}
        mock_result.traceability_map = []
        mock_result.validation_errors = []

        mock_ai_generator.generate_text.return_value = mock_result
        mock_ai_generator.get_total_usage.return_value = MagicMock(
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            estimated_cost=0.001
        )
        mock_ai_generator_class.return_value = mock_ai_generator

        # 配置WordTemplateHandler Mock
        mock_template_handler = MagicMock()
        mock_template_handler.find_paragraph_by_text_and_style.return_value = MagicMock()
        mock_template_handler.document.paragraphs = [MagicMock()]
        mock_template_handler_class.return_value = mock_template_handler

        # 创建orchestrator
        orchestrator = ReportOrchestrator(
            data_dir=".",
            config_path=config_path,
            api_config=api_config,
            base_dir=os.getcwd()
        )

        # 生成报告
        result = orchestrator.generate_report(
            company_name="TestCompany",
            output_path="output/test_report.docx"
        )

        # 验证结果
        assert result.success is True
        assert result.output_path is not None
        assert len(result.validation_errors) == 0

        # 验证调用
        mock_data_extractor.extract_sdg_questionnaire.assert_called_once()
        mock_data_extractor.extract_impact_mechanisms.assert_called_once()
        mock_template_handler.save_document.assert_called_once()


# ==================== 错误处理测试 ====================

class TestErrorHandling:
    """测试错误处理"""

    @patch('src.orchestrator.WordTemplateHandler')
    @patch('src.orchestrator.DataExtractor')
    @patch('src.orchestrator.AITextGenerator')
    def test_company_not_found(
        self,
        mock_ai_generator_class,
        mock_data_extractor_class,
        mock_template_handler_class,
        config_path,
        api_config,
        sample_sdg_response
    ):
        """测试公司数据未找到的情况"""

        # 配置DataExtractor Mock - 返回空列表
        mock_data_extractor = MagicMock()
        mock_data_extractor.extract_sdg_questionnaire.return_value = []
        mock_data_extractor.extract_impact_mechanisms.return_value = []
        mock_data_extractor_class.return_value = mock_data_extractor

        mock_ai_generator_class.return_value = MagicMock()

        orchestrator = ReportOrchestrator(
            data_dir=".",
            config_path=config_path,
            api_config=api_config
        )

        # 尝试生成报告
        result = orchestrator.generate_report(
            company_name="NonExistentCompany",
            output_path="output/test.docx"
        )

        # 应该失败
        assert result.success is False
        assert len(result.validation_errors) > 0
