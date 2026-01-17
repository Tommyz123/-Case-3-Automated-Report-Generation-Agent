"""
Configuration Loader for Case 3 Automation Agent.

This module loads and parses the template mapping YAML configuration file.
根据 PROJECT_PLAN.md 第9节 "Word模板配置文件"实现。
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

import yaml
from pydantic import BaseModel, Field, field_validator


# ==================== 配置模型 ====================

class InsertPosition(BaseModel):
    """插入位置配置"""
    method: str = Field(description="插入方法: after_paragraph, after_section, end_of_document")
    target_text: Optional[str] = Field(default=None, description="目标文本")
    target_style: Optional[str] = Field(default=None, description="目标样式")


class DataSource(BaseModel):
    """数据源配置"""
    model: str = Field(description="数据模型名称")
    fields: Optional[List[str]] = Field(default=None, description="字段列表")
    field: Optional[str] = Field(default=None, description="单个字段名")


class StyleConfig(BaseModel):
    """样式配置"""
    preserve_original: bool = Field(default=True, description="保留原始样式")
    font_size: Optional[int] = Field(default=None, description="字体大小")
    font_name: Optional[str] = Field(default=None, description="字体名称")
    header_bold: Optional[bool] = Field(default=None, description="表头加粗")
    header_background: Optional[str] = Field(default=None, description="表头背景色")
    border: Optional[bool] = Field(default=None, description="是否有边框")


class TableColumn(BaseModel):
    """表格列配置"""
    name: str = Field(description="列名")
    field: str = Field(description="字段名")
    width: float = Field(description="列宽(英寸)")
    format: Optional[str] = Field(default=None, description="格式化字符串")


class TableConfig(BaseModel):
    """表格配置"""
    columns: List[TableColumn] = Field(description="列配置列表")
    style: StyleConfig = Field(default_factory=StyleConfig, description="表格样式")


class AIConfig(BaseModel):
    """AI配置"""
    model: str = Field(default="claude-sonnet-4-5", description="模型名称")
    max_tokens: int = Field(default=1000, description="最大tokens")
    temperature: float = Field(default=0.3, description="温度")


class ValidationConfig(BaseModel):
    """验证配置"""
    require_grounding: bool = Field(default=True, description="要求grounding验证")


class InsertRule(BaseModel):
    """插入规则"""
    name: str = Field(description="规则名称")
    insert_position: InsertPosition = Field(description="插入位置")
    content_type: str = Field(
        description="内容类型: template, ai_generated, structured_table, traceability"
    )
    template: Optional[str] = Field(default=None, description="模板字符串")
    prompt_template: Optional[str] = Field(default=None, description="AI prompt模板")
    data_source: DataSource = Field(description="数据源")
    style: Optional[StyleConfig] = Field(default=None, description="样式配置")
    table_config: Optional[TableConfig] = Field(default=None, description="表格配置")
    ai_config: Optional[AIConfig] = Field(default=None, description="AI配置")
    validation: Optional[ValidationConfig] = Field(default=None, description="验证配置")
    format: Optional[Dict[str, Any]] = Field(default=None, description="格式配置")


class TemplateInfo(BaseModel):
    """模板信息"""
    path: str = Field(description="模板文件路径")
    output_dir: str = Field(default="output", description="输出目录")
    backup_original: bool = Field(default=True, description="是否备份原始模板")


class ValidationSettings(BaseModel):
    """验证设置"""
    check_all_placeholders_filled: bool = Field(default=True)
    check_no_hallucination: bool = Field(default=True)
    check_data_consistency: bool = Field(default=True)
    generate_validation_report: bool = Field(default=True)


class OutputSettings(BaseModel):
    """输出设置"""
    filename_pattern: str = Field(
        default="{company_name}_Impact_Assessment_Report_{date}.docx"
    )
    include_metadata: bool = Field(default=True)
    generate_traceability_json: bool = Field(default=True)


# ==================== 配置加载器 ====================

class TemplateConfig:
    """
    模板配置加载器

    负责加载和解析 template_mapping.yaml 文件

    使用示例:
    ```python
    config = TemplateConfig("config/template_mapping.yaml")
    rules = config.get_insert_rules()
    template_path = config.get_template_path()
    ```
    """

    def __init__(self, config_path: str):
        """
        初始化配置加载器

        Args:
            config_path: YAML配置文件路径
        """
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        self._raw_config: Dict[str, Any] = {}

        # 加载配置
        self._load_config()

        # 解析配置
        self.template_info: TemplateInfo
        self.insert_rules: List[InsertRule] = []
        self.validation: ValidationSettings
        self.output: OutputSettings

        self._parse_config()

        self.logger.info(
            f"Loaded template configuration from {config_path} "
            f"with {len(self.insert_rules)} insert rules"
        )

    def _load_config(self):
        """加载YAML配置文件"""
        try:
            config_file = Path(self.config_path)

            if not config_file.exists():
                raise FileNotFoundError(
                    f"Configuration file not found: {self.config_path}"
                )

            with open(config_file, 'r', encoding='utf-8') as f:
                self._raw_config = yaml.safe_load(f)

            self.logger.debug(f"Loaded config file: {self.config_path}")

        except Exception as e:
            self.logger.error(f"Failed to load config: {str(e)}")
            raise ValueError(f"Configuration loading failed: {str(e)}")

    def _parse_config(self):
        """解析配置文件"""
        try:
            # 解析模板信息
            template_data = self._raw_config.get("template", {})
            self.template_info = TemplateInfo(**template_data)

            # 解析插入规则
            rules_data = self._raw_config.get("insert_rules", [])
            self.insert_rules = []

            for rule_data in rules_data:
                try:
                    rule = InsertRule(**rule_data)
                    self.insert_rules.append(rule)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to parse insert rule '{rule_data.get('name')}': {str(e)}"
                    )

            # 解析验证设置
            validation_data = self._raw_config.get("validation", {})
            self.validation = ValidationSettings(**validation_data)

            # 解析输出设置
            output_data = self._raw_config.get("output", {})
            self.output = OutputSettings(**output_data)

        except Exception as e:
            self.logger.error(f"Failed to parse config: {str(e)}")
            raise ValueError(f"Configuration parsing failed: {str(e)}")

    def get_template_path(self, base_dir: Optional[str] = None) -> str:
        """
        获取模板文件的完整路径

        Args:
            base_dir: 基础目录(默认为配置文件所在目录的父目录)

        Returns:
            str: 模板文件的完整路径
        """
        if base_dir is None:
            # 使用配置文件所在目录的父目录
            base_dir = Path(self.config_path).parent.parent

        template_path = Path(base_dir) / self.template_info.path
        return str(template_path)

    def get_output_dir(self, base_dir: Optional[str] = None) -> str:
        """
        获取输出目录的完整路径

        Args:
            base_dir: 基础目录

        Returns:
            str: 输出目录的完整路径
        """
        if base_dir is None:
            base_dir = Path(self.config_path).parent.parent

        output_dir = Path(base_dir) / self.template_info.output_dir
        return str(output_dir)

    def get_insert_rules(self) -> List[InsertRule]:
        """
        获取所有插入规则

        Returns:
            List[InsertRule]: 插入规则列表
        """
        return self.insert_rules

    def get_insert_rule_by_name(self, name: str) -> Optional[InsertRule]:
        """
        根据名称获取插入规则

        Args:
            name: 规则名称

        Returns:
            Optional[InsertRule]: 插入规则,如果不存在则返回None
        """
        for rule in self.insert_rules:
            if rule.name == name:
                return rule
        return None

    def get_validation_settings(self) -> ValidationSettings:
        """获取验证设置"""
        return self.validation

    def get_output_settings(self) -> OutputSettings:
        """获取输出设置"""
        return self.output

    def get_output_filename(
        self,
        company_name: str,
        date: Optional[str] = None
    ) -> str:
        """
        根据模式生成输出文件名

        Args:
            company_name: 公司名称
            date: 日期字符串(默认使用当前日期)

        Returns:
            str: 输出文件名
        """
        if date is None:
            from datetime import datetime
            date = datetime.now().strftime("%Y%m%d")

        filename = self.output.filename_pattern.format(
            company_name=company_name,
            date=date
        )

        return filename

    def __repr__(self) -> str:
        return (
            f"TemplateConfig(template={self.template_info.path}, "
            f"rules={len(self.insert_rules)})"
        )


__all__ = [
    'TemplateConfig',
    'InsertRule',
    'InsertPosition',
    'DataSource',
    'StyleConfig',
    'TableConfig',
    'TableColumn',
    'AIConfig',
    'ValidationConfig',
    'TemplateInfo',
    'ValidationSettings',
    'OutputSettings'
]
