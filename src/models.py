"""
Data models for Case 3 Automation Agent.

This module contains all Pydantic models for data validation and type safety.
根据 PROJECT_PLAN.md 第7节定义的完整数据模型。
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ValidationInfo


# ==================== SDG问卷响应模型 ====================

class SDGResponse(BaseModel):
    """SDG问卷调查响应数据

    数据来源: SDG问卷调查_完整中文版.xlsx / SDG questionnaire (Responses).xlsx
    工作表: Form Responses 1
    数据规模: 146行 × 5列
    """
    timestamp: datetime = Field(description="问卷提交时间")
    company_name: str = Field(description="公司名称", min_length=1)
    contact_name: str = Field(description="联系人姓名", min_length=1)
    sdg_goals: str = Field(description="致力的联合国可持续发展目标（长文本）")
    implementation_description: str = Field(
        description="如何实现这些目标的描述",
        min_length=10
    )

    @field_validator('company_name', 'contact_name')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """验证字段不为空"""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


# ==================== 影响机制模型 ====================

class ImpactMechanism(BaseModel):
    """影响机制数据（单条机制记录）

    数据来源: Mechanisms.xlsx 各公司工作表的机制数据区（Row 14+）
    字段数: 8个字段
    """
    stakeholder_affected: str = Field(description="受影响的利益相关者")
    mechanism: str = Field(description="影响机制描述")
    driving_variable: Optional[str] = Field(default=None, description="驱动变量")
    type_of_impact: Optional[str] = Field(default=None, description="影响类型")
    positive_negative: Optional[str] = Field(default=None, description="正向/负向影响")
    method: Optional[str] = Field(default=None, description="计算方法")
    value: Optional[float] = Field(default=None, description="影响价值（数值）")
    unit: Optional[str] = Field(default=None, description="单位")


# ==================== 公司影响评估数据模型 ====================

class CompanyImpactData(BaseModel):
    """单个公司的完整影响评估数据

    数据来源: Mechanisms.xlsx 中的单个工作表
    整合了公司信息、利益相关者和影响机制数据
    """
    company_name: str = Field(description="公司名称（工作表名）")
    sdg_questionnaire_response: Optional[str] = Field(
        default=None,
        description="SDG问卷响应引用（Row 1）"
    )
    alternative_scenario: Optional[str] = Field(
        default=None,
        description="替代情景描述（Row 3）"
    )
    stakeholders: List[str] = Field(
        default_factory=list,
        description="利益相关者列表（Rows 6-11）"
    )
    mechanisms: List[ImpactMechanism] = Field(
        default_factory=list,
        description="影响机制列表（Row 14+）"
    )

    # 注释掉非空验证以支持优雅降级（当没有影响评估机制数据时）
    # @field_validator('mechanisms')
    # @classmethod
    # def validate_mechanisms_not_empty(cls, v: List[ImpactMechanism]) -> List[ImpactMechanism]:
    #     """验证至少有一个影响机制"""
    #     if not v:
    #         raise ValueError("At least one mechanism is required")
    #     return v


# ==================== 报告数据模型 ====================

class ReportData(BaseModel):
    """完整的报告数据（整合SDG问卷和影响机制）

    用于生成影响评估报告的完整数据结构
    """
    company_name: str = Field(description="公司名称")
    sdg_response: SDGResponse = Field(description="SDG问卷响应数据")
    impact_data: CompanyImpactData = Field(description="影响评估数据")
    methodology_principles: List[str] = Field(
        default_factory=list,
        description="方法论原则（从方法论文档提取）"
    )

    @field_validator('company_name')
    @classmethod
    def validate_company_name_matches(cls, v: str, info: ValidationInfo) -> str:
        """验证公司名称在SDG响应和影响数据中一致"""
        if info.data and 'sdg_response' in info.data:
            if v != info.data['sdg_response'].company_name:
                raise ValueError("Company name mismatch between fields")
        return v


# ==================== 验证结果模型 ====================

class ValidationError(BaseModel):
    """验证错误详情"""
    field: str = Field(description="字段名")
    error_type: str = Field(description="错误类型")
    message: str = Field(description="错误消息")


class ValidationResult(BaseModel):
    """数据验证结果"""
    is_valid: bool = Field(description="是否通过验证")
    errors: List[ValidationError] = Field(
        default_factory=list,
        description="验证错误列表"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="警告信息列表"
    )


# ==================== 生成结果模型 ====================

class CitationInfo(BaseModel):
    """引用信息（可追溯性）"""
    statement: str = Field(description="具体陈述")
    source_file: str = Field(description="源文件名")
    source_sheet: Optional[str] = Field(default=None, description="工作表名")
    source_row: Optional[int] = Field(default=None, description="行号")
    source_column: Optional[str] = Field(default=None, description="列名")


class GenerationResult(BaseModel):
    """报告生成结果"""
    success: bool = Field(description="是否成功生成")
    output_path: Optional[str] = Field(default=None, description="输出文件路径")
    validation_errors: List[str] = Field(
        default_factory=list,
        description="验证错误列表"
    )
    traceability_map: List[CitationInfo] = Field(
        default_factory=list,
        description="可追溯性映射（内容->数据源）"
    )
    metrics: dict = Field(
        default_factory=dict,
        description="性能指标（时间、Token使用等）"
    )


# ==================== 模型导出 ====================

__all__ = [
    'SDGResponse',
    'ImpactMechanism',
    'CompanyImpactData',
    'ReportData',
    'ValidationError',
    'ValidationResult',
    'CitationInfo',
    'GenerationResult',
]
