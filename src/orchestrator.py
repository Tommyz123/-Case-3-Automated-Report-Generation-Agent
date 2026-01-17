"""
Report Orchestrator for Case 3 Automation Agent.

This module coordinates all components to generate complete impact assessment reports.
根据 PROJECT_PLAN.md 第11节 "报告编排器"实现。
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from .config_loader import TemplateConfig, InsertRule
from .data_extractor import DataExtractor
from .template_handler import WordTemplateHandler
from .ai_generator import AITextGenerator, APIConfig
from .models import (
    SDGResponse,
    CompanyImpactData,
    ReportData,
    GenerationResult,
    CitationInfo,
    ValidationResult,
    ValidationError
)


# ==================== 报告编排器 ====================

class ReportOrchestrator:
    """
    报告编排器

    职责:
    1. 协调 DataExtractor, WordTemplateHandler, AITextGenerator
    2. 执行完整的报告生成流程
    3. 实现可追溯性映射
    4. 性能和成本统计

    使用示例:
    ```python
    orchestrator = ReportOrchestrator(
        data_dir=".",
        config_path="config/template_mapping.yaml",
        api_config=api_config
    )

    result = orchestrator.generate_report(company_name="EmergConnect")
    ```
    """

    def __init__(
        self,
        data_dir: str,
        config_path: str,
        api_config: APIConfig,
        base_dir: Optional[str] = None
    ):
        """
        初始化报告编排器

        Args:
            data_dir: 数据文件目录
            config_path: 配置文件路径
            api_config: AI API配置
            base_dir: 基础目录(默认为当前目录)
        """
        self.base_dir = base_dir or os.getcwd()
        self.logger = logging.getLogger(__name__)

        # 初始化组件
        self.logger.info("Initializing ReportOrchestrator...")

        # 1. 加载配置
        self.config = TemplateConfig(config_path)
        self.logger.info(f"Loaded configuration: {len(self.config.get_insert_rules())} rules")

        # 2. 初始化数据提取器
        self.data_extractor = DataExtractor(data_dir)
        self.logger.info("DataExtractor initialized")

        # 3. 初始化AI生成器
        self.ai_generator = AITextGenerator(api_config)
        self.logger.info("AITextGenerator initialized")

        # 4. Word模板处理器(每次生成时初始化)
        self.template_handler: Optional[WordTemplateHandler] = None

        # 性能指标
        self.metrics: Dict[str, Any] = {}

        self.logger.info("ReportOrchestrator initialization complete")

    def generate_report(
        self,
        company_name: str,
        output_path: Optional[str] = None
    ) -> GenerationResult:
        """
        生成完整的影响评估报告

        流程:
        1. 提取数据(SDG问卷 + 影响机制)
        2. 验证数据
        3. 加载Word模板
        4. 根据配置规则填充模板
        5. AI生成自然语言内容
        6. 插入结构化表格
        7. 最终验证
        8. 保存报告
        9. 生成可追溯性JSON

        Args:
            company_name: 公司名称
            output_path: 输出文件路径(可选,默认根据配置生成)

        Returns:
            GenerationResult: 生成结果,包含路径、验证结果、指标等
        """
        start_time = time.time()
        self.logger.info(f"Starting report generation for: {company_name}")

        try:
            # ===== 步骤1: 提取数据 =====
            self.logger.info("Step 1: Extracting data...")
            step1_start = time.time()

            # 提取SDG问卷数据
            all_sdg_responses = self.data_extractor.extract_sdg_questionnaire()
            sdg_response = self._find_sdg_response(all_sdg_responses, company_name)

            # 提取影响机制数据
            all_impact_data = self.data_extractor.extract_impact_mechanisms()
            impact_data = self._find_impact_data(all_impact_data, company_name)

            if not impact_data:
                # 优雅降级: 创建默认的影响评估机制数据
                self.logger.warning(
                    f"No impact mechanism data found for company: {company_name}. "
                    f"Creating default impact data for graceful degradation."
                )
                from .models import CompanyImpactData
                
                impact_data = CompanyImpactData(
                    company_name=company_name,
                    stakeholders=[],  # 空的利益相关者列表
                    mechanisms=[]  # 空的影响机制列表
                )

            # 智能双向匹配逻辑:
            # 如果第一次没找到SDG响应,尝试利用影响机制中的完整公司名再次查找
            # 场景1: 用户输入"公司B" -> Mechanisms找到"公司B/Sparkinity" -> 用这个全名去SDG找
            # 场景2: SDG里的名字(如"Sparkinity")被包含在Mechanism名字(如"公司B/Sparkinity")里
            if not sdg_response and impact_data:
                self.logger.info(
                    f"SDG response not found for '{company_name}', "
                    f"trying intelligent matching with mechanism name: '{impact_data.company_name}'"
                )
                
                # 尝试1: 用Mechanism的完整名字去SDG里找
                sdg_response = self._find_sdg_response(all_sdg_responses, impact_data.company_name)
                
                # 尝试2: 看看SDG里的哪个名字被包含在Mechanism名字里
                if not sdg_response:
                    mechanism_name_lower = impact_data.company_name.lower()
                    for resp in all_sdg_responses:
                        resp_name_lower = resp.company_name.lower()
                        # 检查SDG公司名是否是Mechanism名字的子串
                        if resp_name_lower in mechanism_name_lower:
                            self.logger.info(
                                f"Found SDG response '{resp.company_name}' "
                                f"inside mechanism name '{impact_data.company_name}'"
                            )
                            sdg_response = resp
                            break

            # 优雅降级: 如果仍然找不到SDG响应,创建一个默认的
            if not sdg_response:
                self.logger.warning(
                    f"No SDG questionnaire response found for company: {company_name}. "
                    f"Creating default SDG response for graceful degradation."
                )
                from datetime import datetime
                from .models import SDGResponse
                
                sdg_response = SDGResponse(
                    timestamp=datetime.now(),
                    company_name=impact_data.company_name,
                    contact_name="未提供联系人信息",
                    sdg_goals="未在SDG问卷中找到该公司的可持续发展目标信息",
                    implementation_description="未在SDG问卷中找到该公司的实施描述信息"
                )

            step1_time = time.time() - step1_start
            self.logger.info(f"Data extraction completed in {step1_time:.2f}s")

            # ===== 步骤2: 验证数据 =====
            self.logger.info("Step 2: Validating data...")
            validation_result = self._validate_data(sdg_response, impact_data)

            if not validation_result.is_valid:
                error_msg = "; ".join([e.message for e in validation_result.errors])
                raise ValueError(f"Data validation failed: {error_msg}")

            # ===== 步骤3: 加载Word模板 =====
            self.logger.info("Step 3: Loading Word template...")
            template_path = self.config.get_template_path(self.base_dir)

            self.template_handler = WordTemplateHandler(template_path)
            self.logger.info(f"Loaded template: {template_path}")

            # ===== 步骤4-6: 根据配置规则填充内容 =====
            self.logger.info("Step 4-6: Processing insert rules...")
            traceability_map: List[CitationInfo] = []

            for rule in self.config.get_insert_rules():
                self.logger.info(f"Processing rule: {rule.name}")

                try:
                    citations = self._process_insert_rule(
                        rule,
                        sdg_response,
                        impact_data
                    )
                    traceability_map.extend(citations)

                except Exception as e:
                    self.logger.error(f"Failed to process rule '{rule.name}': {str(e)}")
                    raise

            # ===== 步骤7: 最终验证 =====
            self.logger.info("Step 7: Final validation...")
            # TODO: 实现最终一致性检查

            # ===== 步骤8: 保存报告 =====
            self.logger.info("Step 8: Saving report...")
            if not output_path:
                output_dir = self.config.get_output_dir(self.base_dir)
                os.makedirs(output_dir, exist_ok=True)

                filename = self.config.get_output_filename(company_name)
                output_path = os.path.join(output_dir, filename)

            self.template_handler.save_document(output_path)
            self.logger.info(f"Report saved to: {output_path}")

            # ===== 步骤9: 生成可追溯性JSON =====
            if self.config.output.generate_traceability_json:
                self.logger.info("Step 9: Generating traceability JSON...")
                traceability_path = self._save_traceability_json(
                    company_name,
                    traceability_map,
                    output_path
                )
                self.logger.info(f"Traceability saved to: {traceability_path}")

            # 计算性能指标
            total_time = time.time() - start_time
            token_usage = self.ai_generator.get_total_usage().model_dump()

            self.metrics = {
                "company_name": company_name,
                "total_time": total_time,
                "data_extraction_time": step1_time,
                "rules_processed": len(self.config.get_insert_rules()),
                "ai_token_usage": token_usage,
                "traceability_entries": len(traceability_map)
            }

            # 安全地格式化成本
            estimated_cost = token_usage.get('estimated_cost', 0.0)
            cost_str = f"{estimated_cost:.4f}" if isinstance(estimated_cost, (int, float)) else "N/A"

            self.logger.info(
                f"Report generation completed in {total_time:.2f}s "
                f"(Cost: ${cost_str})"
            )

            return GenerationResult(
                success=True,
                output_path=output_path,
                validation_errors=[],
                traceability_map=traceability_map,
                metrics=self.metrics
            )

        except Exception as e:
            self.logger.error(f"Report generation failed: {str(e)}", exc_info=True)
            return GenerationResult(
                success=False,
                validation_errors=[str(e)],
                metrics=self.metrics
            )

    def _find_sdg_response(
        self,
        all_responses: List[SDGResponse],
        company_name: str
    ) -> Optional[SDGResponse]:
        """查找指定公司的SDG问卷响应（支持模糊匹配）"""
        search_name = company_name.lower()

        # 1. 精确匹配
        for response in all_responses:
            if response.company_name.lower() == search_name:
                return response

        # 2. 包含匹配（搜索词在公司名中，或公司名在搜索词中）
        for response in all_responses:
            resp_name = response.company_name.lower()
            if search_name in resp_name or resp_name in search_name:
                self.logger.info(f"Fuzzy matched SDG response: '{response.company_name}' for search '{company_name}'")
                return response

        return None

    def _find_impact_data(
        self,
        all_data: List[CompanyImpactData],
        company_name: str
    ) -> Optional[CompanyImpactData]:
        """查找指定公司的影响机制数据（支持模糊匹配）"""
        search_name = company_name.lower()

        # 1. 精确匹配
        for data in all_data:
            if data.company_name.lower() == search_name:
                return data

        # 2. 包含匹配
        for data in all_data:
            data_name = data.company_name.lower()
            if search_name in data_name or data_name in search_name:
                self.logger.info(f"Fuzzy matched impact data: '{data.company_name}' for search '{company_name}'")
                return data

        return None

    def _validate_data(
        self,
        sdg_response: SDGResponse,
        impact_data: CompanyImpactData
    ) -> ValidationResult:
        """验证数据完整性和一致性"""
        errors: List[ValidationError] = []
        warnings: List[str] = []

        # 检查公司名称一致性（允许模糊匹配的情况）
        sdg_name = sdg_response.company_name.lower()
        impact_name = impact_data.company_name.lower()
        if sdg_name != impact_name and sdg_name not in impact_name and impact_name not in sdg_name:
            errors.append(ValidationError(
                field="company_name",
                error_type="mismatch",
                message=f"Company name mismatch: '{sdg_response.company_name}' vs '{impact_data.company_name}'"
            ))


        # 警告: 缺少可选字段（优雅降级支持）
        if not impact_data.mechanisms:
            warnings.append("No impact mechanisms found (using graceful degradation)")
        
        if not impact_data.stakeholders:
            warnings.append("No stakeholders defined")

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
        )

    def _process_insert_rule(
        self,
        rule: InsertRule,
        sdg_response: SDGResponse,
        impact_data: CompanyImpactData
    ) -> List[CitationInfo]:
        """
        处理单个插入规则

        根据content_type分别处理:
        - template: 简单模板替换
        - ai_generated: AI生成内容
        - structured_table: 插入表格
        - traceability: 可追溯性附录

        Returns:
            List[CitationInfo]: 生成的引用信息
        """
        citations: List[CitationInfo] = []

        # 查找插入位置
        position = self._find_insert_position(rule.insert_position)

        if not position:
            self.logger.warning(f"Insert position not found for rule: {rule.name}")
            return citations

        # 根据content_type处理
        if rule.content_type == "template":
            citations = self._process_template_rule(rule, position, sdg_response, impact_data)

        elif rule.content_type == "ai_generated":
            citations = self._process_ai_generated_rule(rule, position, sdg_response, impact_data)

        elif rule.content_type == "structured_table":
            citations = self._process_table_rule(rule, position, impact_data)

        elif rule.content_type == "traceability":
            # 可追溯性附录将在最后单独处理
            pass

        else:
            self.logger.warning(f"Unknown content_type: {rule.content_type}")

        return citations

    def _find_insert_position(self, position_config) -> Any:
        """查找Word文档中的插入位置"""
        if not self.template_handler:
            return None

        method = position_config.method

        if method == "after_paragraph":
            return self.template_handler.find_paragraph_by_text_and_style(
                text=position_config.target_text,
                style=position_config.target_style
            )

        elif method == "after_section":
            paragraphs = self.template_handler.find_paragraphs_by_style(
                style=position_config.target_style
            )
            # 查找匹配的段落
            for p in paragraphs:
                if position_config.target_text and position_config.target_text in p.text:
                    return p
            return None

        elif method == "end_of_document":
            # 返回最后一个段落
            if self.template_handler.document.paragraphs:
                return self.template_handler.document.paragraphs[-1]
            return None

        return None

    def _process_template_rule(
        self,
        rule: InsertRule,
        position: Any,
        sdg_response: SDGResponse,
        impact_data: CompanyImpactData
    ) -> List[CitationInfo]:
        """处理模板类型的规则"""
        citations: List[CitationInfo] = []

        # 准备数据
        data = self._extract_data_for_rule(rule, sdg_response, impact_data)

        # 填充模板
        content = self._fill_template(rule.template or "", data)

        # 插入到Word文档
        if position:
            self.template_handler.insert_text_after(
                position=position,
                text=content,
                preserve_style=True
            )

        # 记录引用
        for field_name, field_value in data.items():
            citations.append(CitationInfo(
                statement=f"{field_name}: {field_value}",
                source_file="SDG问卷调查_完整中文版.xlsx",
                source_column=field_name
            ))

        return citations

    def _process_ai_generated_rule(
        self,
        rule: InsertRule,
        position: Any,
        sdg_response: SDGResponse,
        impact_data: CompanyImpactData
    ) -> List[CitationInfo]:
        """处理AI生成类型的规则"""
        # 准备数据
        data = self._extract_data_for_rule(rule, sdg_response, impact_data)

        # AI生成内容
        source_data = {
            "company_name": impact_data.company_name,
            "source_file": "Mechanisms.xlsx",
            **data
        }

        result = self.ai_generator.generate_text(
            prompt_template=rule.prompt_template or "",
            data=data,
            source_data=source_data,
            validate_grounding=rule.validation.require_grounding if rule.validation else True
        )

        if not result.success:
            raise ValueError(f"AI generation failed: {result.validation_errors}")

        generated_text = result.metrics.get("generated_text", "")

        # 插入到Word文档
        if position:
            self.template_handler.insert_text_after(
                position=position,
                text=generated_text,
                preserve_style=True
            )

        return result.traceability_map

    def _process_table_rule(
        self,
        rule: InsertRule,
        position: Any,
        impact_data: CompanyImpactData
    ) -> List[CitationInfo]:
        """处理结构化表格类型的规则"""
        citations: List[CitationInfo] = []

        if not rule.table_config:
            return citations

        # 获取机制数据
        mechanisms = impact_data.mechanisms

        # 准备表格数据
        table_data = []
        header_row = [col.name for col in rule.table_config.columns]
        table_data.append(header_row)

        for mechanism in mechanisms:
            row = []
            for col in rule.table_config.columns:
                value = getattr(mechanism, col.field, "")

                # 格式化数值
                if col.format and isinstance(value, (int, float)):
                    value = col.format.format(value)

                row.append(str(value) if value is not None else "")

            table_data.append(row)

            # 记录引用
            citations.append(CitationInfo(
                statement=f"Mechanism: {mechanism.mechanism}",
                source_file="Mechanisms.xlsx",
                source_sheet=impact_data.company_name
            ))

        # 插入表格
        if position and self.template_handler:
            rows = len(table_data)
            cols = len(table_data[0]) if table_data else 0
            
            self.template_handler.insert_table_after(
                position=position,
                rows=rows,
                cols=cols,
                data=table_data,
                style_config=rule.table_config.style.model_dump() if rule.table_config.style else None
            )

        return citations

    def _extract_data_for_rule(
        self,
        rule: InsertRule,
        sdg_response: SDGResponse,
        impact_data: CompanyImpactData
    ) -> Dict[str, Any]:
        """提取规则所需的数据"""
        data: Dict[str, Any] = {}

        model_name = rule.data_source.model

        if model_name == "SDGResponse":
            source_obj = sdg_response
        elif model_name == "CompanyImpactData":
            source_obj = impact_data
        else:
            self.logger.warning(f"Unknown model: {model_name}")
            return data

        # 提取字段
        if rule.data_source.fields:
            for field_name in rule.data_source.fields:
                value = getattr(source_obj, field_name, None)
                data[field_name] = value

        elif rule.data_source.field:
            field_name = rule.data_source.field
            value = getattr(source_obj, field_name, None)
            data[field_name] = value

        # 添加数据来源状态说明
        status_lines = []

        # 检查SDG数据是否为默认值
        if sdg_response.contact_name == "未提供联系人信息":
            status_lines.append("⚠️ SDG问卷数据: 使用默认值（未找到该公司的SDG问卷响应）")
        else:
            status_lines.append("✓ SDG问卷数据: 来自真实问卷响应")

        # 检查影响评估数据是否为默认值
        if not impact_data.mechanisms:
            status_lines.append("⚠️ 影响评估数据: 使用默认值（未找到该公司的影响评估机制数据）")
        else:
            status_lines.append(f"✓ 影响评估数据: 包含 {len(impact_data.mechanisms)} 个影响机制")

        data['data_source_status'] = '\n'.join(status_lines)

        return data
    def _fill_template(self, template: str, data: Dict[str, Any]) -> str:
        """填充模板"""
        content = template

        for key, value in data.items():
            placeholder = "{" + key + "}"
            if isinstance(value, list):
                value_str = ", ".join(str(v) for v in value)
            else:
                value_str = str(value) if value is not None else ""

            content = content.replace(placeholder, value_str)

        return content

    def _save_traceability_json(
        self,
        company_name: str,
        traceability_map: List[CitationInfo],
        report_path: str
    ) -> str:
        """保存可追溯性JSON文件"""
        # 生成JSON文件路径
        json_path = report_path.replace(".docx", "_traceability.json")

        # 构建JSON数据
        traceability_data = {
            "company_name": company_name,
            "report_path": report_path,
            "generated_at": datetime.now().isoformat(),
            "citations": [c.model_dump() for c in traceability_map]
        }

        # 保存JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(traceability_data, f, ensure_ascii=False, indent=2)

        return json_path

    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return self.metrics


__all__ = ['ReportOrchestrator']
