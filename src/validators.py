"""
验证器模块
提供数据一致性验证、可追溯性验证和AI幻觉检测功能
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import re
from .models import (
    ReportData,
    ImpactMechanism,
    CitationInfo,
    ValidationResult,
    ValidationError
)


@dataclass
class ConsistencyCheckResult:
    """一致性检查结果"""
    is_consistent: bool
    inconsistencies: List[str]
    checked_values: Dict[str, List[Any]]


@dataclass
class TraceabilityCheckResult:
    """可追溯性检查结果"""
    total_values: int
    traceable_values: int
    traceability_rate: float
    untraceable_items: List[str]


@dataclass
class HallucinationCheckResult:
    """幻觉检测结果"""
    total_statements: int
    hallucination_count: int
    hallucination_rate: float
    hallucinations: List[Dict[str, str]]


class DataConsistencyValidator:
    """数据一致性验证器"""
    
    def __init__(self):
        """初始化验证器"""
        pass
    
    def validate_consistency(
        self,
        report_data: ReportData,
        generated_content: Dict[str, str]
    ) -> ConsistencyCheckResult:
        """
        验证同一数据在报告不同位置的一致性
        
        Args:
            report_data: 源数据
            generated_content: 生成的报告内容(章节名->内容)
            
        Returns:
            ConsistencyCheckResult: 一致性检查结果
        """
        inconsistencies = []
        checked_values = {}
        
        # 1. 验证公司名称一致性
        company_name = report_data.company_name
        checked_values['company_name'] = []
        
        for section, content in generated_content.items():
            # 在内容中查找公司名称
            if company_name in content:
                checked_values['company_name'].append({
                    'section': section,
                    'value': company_name
                })
        
        # 2. 验证数值一致性(从影响机制中提取)
        for mechanism in report_data.impact_data.mechanisms:
            if mechanism.value is not None:
                value_key = f"value_{mechanism.stakeholder_affected}_{mechanism.mechanism}"
                checked_values[value_key] = []
                
                # 在生成内容中查找该数值
                for section, content in generated_content.items():
                    # 查找数值(支持不同格式: 123, 123.45, 123,456等)
                    value_pattern = re.escape(str(mechanism.value))
                    if re.search(value_pattern, content):
                        checked_values[value_key].append({
                            'section': section,
                            'value': mechanism.value
                        })
        
        # 3. 检查是否有不一致的情况
        for key, occurrences in checked_values.items():
            if len(occurrences) > 1:
                # 检查所有出现的值是否一致
                values = [occ['value'] for occ in occurrences]
                if len(set(str(v) for v in values)) > 1:
                    inconsistencies.append(
                        f"数值 '{key}' 在不同章节中不一致: {occurrences}"
                    )
        
        is_consistent = len(inconsistencies) == 0
        
        return ConsistencyCheckResult(
            is_consistent=is_consistent,
            inconsistencies=inconsistencies,
            checked_values=checked_values
        )
    
    def validate_numerical_accuracy(
        self,
        report_data: ReportData,
        generated_content: Dict[str, str]
    ) -> ValidationResult:
        """
        验证数值计算的正确性
        
        Args:
            report_data: 源数据
            generated_content: 生成的报告内容
            
        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []
        
        # 提取所有源数据中的数值
        source_values = set()
        for mechanism in report_data.impact_data.mechanisms:
            if mechanism.value is not None:
                source_values.add(mechanism.value)
        
        # 在生成内容中查找数值
        for section, content in generated_content.items():
            # 使用正则表达式提取所有数值
            numbers = re.findall(r'\b\d+(?:\.\d+)?\b', content)
            
            for num_str in numbers:
                try:
                    num = float(num_str)
                    # 检查该数值是否在源数据中
                    if num not in source_values and num > 10:  # 忽略小数字(可能是序号等)
                        warnings.append(
                            f"在 {section} 中发现数值 {num},但未在源数据中找到"
                        )
                except ValueError:
                    continue
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=[ValidationError(
                field=section,
                error_type="numerical_accuracy",
                message=msg
            ) for msg in errors],
            warnings=warnings
        )


class TraceabilityValidator:
    """可追溯性验证器"""
    
    def __init__(self):
        """初始化验证器"""
        pass
    
    def validate_traceability(
        self,
        report_data: ReportData,
        citations: List[CitationInfo]
    ) -> TraceabilityCheckResult:
        """
        验证所有数值可追溯到源数据
        
        Args:
            report_data: 源数据
            citations: 引用信息列表
            
        Returns:
            TraceabilityCheckResult: 可追溯性检查结果
        """
        # 提取所有源数据中的关键值
        source_items = []
        
        # 1. 公司名称
        source_items.append(report_data.company_name)
        
        # 2. SDG目标
        source_items.append(report_data.sdg_response.sdg_goals)
        
        # 3. 实施描述
        source_items.append(report_data.sdg_response.implementation_description)
        
        # 4. 替代情景
        if report_data.impact_data.alternative_scenario:
            source_items.append(report_data.impact_data.alternative_scenario)
        
        # 5. 利益相关者
        source_items.extend(report_data.impact_data.stakeholders)
        
        # 6. 影响机制的所有值
        for mechanism in report_data.impact_data.mechanisms:
            if mechanism.value is not None:
                source_items.append(str(mechanism.value))
            source_items.append(mechanism.mechanism)
            source_items.append(mechanism.stakeholder_affected)
        
        total_values = len(source_items)
        
        # 检查每个源项是否有对应的引用
        traceable_count = 0
        untraceable_items = []
        
        for item in source_items:
            # 检查是否在citations中
            is_traceable = any(
                str(item) in citation.statement
                for citation in citations
            )
            
            if is_traceable:
                traceable_count += 1
            else:
                # 某些项可能不需要引用(如公司名称在标题中)
                # 只标记重要的未追溯项
                if isinstance(item, (int, float)) or len(str(item)) > 50:
                    untraceable_items.append(str(item)[:100])
        
        traceability_rate = traceable_count / total_values if total_values > 0 else 0
        
        return TraceabilityCheckResult(
            total_values=total_values,
            traceable_values=traceable_count,
            traceability_rate=traceability_rate,
            untraceable_items=untraceable_items
        )
    
    def validate_statement_grounding(
        self,
        statements: List[str],
        report_data: ReportData
    ) -> TraceabilityCheckResult:
        """
        验证所有关键陈述有数据支撑
        
        Args:
            statements: 关键陈述列表
            report_data: 源数据
            
        Returns:
            TraceabilityCheckResult: 可追溯性检查结果
        """
        total_statements = len(statements)
        grounded_count = 0
        ungrounded_statements = []
        
        # 构建源数据文本集合
        source_texts = [
            report_data.company_name,
            report_data.sdg_response.sdg_goals,
            report_data.sdg_response.implementation_description,
        ]
        
        if report_data.impact_data.alternative_scenario:
            source_texts.append(report_data.impact_data.alternative_scenario)
        
        source_texts.extend(report_data.impact_data.stakeholders)
        
        for mechanism in report_data.impact_data.mechanisms:
            source_texts.append(mechanism.mechanism)
            source_texts.append(mechanism.stakeholder_affected)
            if mechanism.value is not None:
                source_texts.append(str(mechanism.value))
        
        # 检查每个陈述是否有数据支撑
        for statement in statements:
            is_grounded = False
            
            # 检查陈述中是否包含源数据的关键信息
            for source_text in source_texts:
                # 简单的包含检查(可以改进为更复杂的语义匹配)
                if len(str(source_text)) > 5 and str(source_text).lower() in statement.lower():
                    is_grounded = True
                    break
            
            if is_grounded:
                grounded_count += 1
            else:
                ungrounded_statements.append(statement[:100])
        
        grounding_rate = grounded_count / total_statements if total_statements > 0 else 0
        
        return TraceabilityCheckResult(
            total_values=total_statements,
            traceable_values=grounded_count,
            traceability_rate=grounding_rate,
            untraceable_items=ungrounded_statements
        )


class HallucinationDetector:
    """AI幻觉检测器"""
    
    def __init__(self):
        """初始化检测器"""
        # 定义一些常见的幻觉模式
        self.hallucination_patterns = [
            r'根据我们的分析',  # AI可能编造的短语
            r'众所周知',
            r'研究表明',
            r'专家认为',
        ]
    
    def detect_hallucinations(
        self,
        generated_content: Dict[str, str],
        report_data: ReportData
    ) -> HallucinationCheckResult:
        """
        检查生成内容是否包含未提供的信息(幻觉)
        
        Args:
            generated_content: 生成的报告内容
            report_data: 源数据
            
        Returns:
            HallucinationCheckResult: 幻觉检测结果
        """
        hallucinations = []
        total_statements = 0
        
        # 构建源数据关键词集合
        source_keywords = self._extract_keywords_from_data(report_data)
        
        for section, content in generated_content.items():
            # 将内容分割为句子
            sentences = self._split_into_sentences(content)
            total_statements += len(sentences)
            
            for sentence in sentences:
                # 检查是否包含幻觉模式
                for pattern in self.hallucination_patterns:
                    if re.search(pattern, sentence):
                        hallucinations.append({
                            'section': section,
                            'sentence': sentence[:200],
                            'reason': f'包含可疑短语: {pattern}'
                        })
                        break
                
                # 检查是否包含不在源数据中的具体数值或事实
                # (这里简化处理,实际应该更复杂)
                numbers = re.findall(r'\b\d+(?:\.\d+)?\b', sentence)
                for num_str in numbers:
                    try:
                        num = float(num_str)
                        if num > 10 and not self._is_number_in_source(num, report_data):
                            hallucinations.append({
                                'section': section,
                                'sentence': sentence[:200],
                                'reason': f'包含未在源数据中的数值: {num}'
                            })
                            break
                    except ValueError:
                        continue
        
        hallucination_count = len(hallucinations)
        hallucination_rate = hallucination_count / total_statements if total_statements > 0 else 0
        
        return HallucinationCheckResult(
            total_statements=total_statements,
            hallucination_count=hallucination_count,
            hallucination_rate=hallucination_rate,
            hallucinations=hallucinations
        )
    
    def validate_with_grounding(
        self,
        generated_text: str,
        source_data: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        使用Grounding验证机制检查生成文本
        
        Args:
            generated_text: 生成的文本
            source_data: 源数据字典
            
        Returns:
            Tuple[bool, List[str]]: (是否通过验证, 问题列表)
        """
        issues = []
        
        # 1. 检查关键事实是否来自源数据
        sentences = self._split_into_sentences(generated_text)
        
        for sentence in sentences:
            # 提取句子中的关键信息
            # (简化处理,实际应该使用NLP技术)
            
            # 检查数值
            numbers = re.findall(r'\b\d+(?:\.\d+)?\b', sentence)
            for num_str in numbers:
                try:
                    num = float(num_str)
                    if num > 10:  # 忽略小数字
                        # 检查该数值是否在源数据中
                        found = False
                        for key, value in source_data.items():
                            if isinstance(value, (int, float)) and abs(value - num) < 0.01:
                                found = True
                                break
                            elif isinstance(value, str) and num_str in value:
                                found = True
                                break
                        
                        if not found:
                            issues.append(f"数值 {num} 未在源数据中找到: {sentence[:100]}")
                except ValueError:
                    continue
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    def _extract_keywords_from_data(self, report_data: ReportData) -> set:
        """从源数据中提取关键词"""
        keywords = set()
        
        # 添加公司名称
        keywords.add(report_data.company_name.lower())
        
        # 添加利益相关者
        for stakeholder in report_data.impact_data.stakeholders:
            keywords.add(stakeholder.lower())
        
        # 添加机制关键词
        for mechanism in report_data.impact_data.mechanisms:
            keywords.add(mechanism.stakeholder_affected.lower())
            keywords.add(mechanism.mechanism.lower())
        
        return keywords
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """将文本分割为句子"""
        # 简单的句子分割(可以改进)
        sentences = re.split(r'[。.!?;]\s*', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _is_number_in_source(self, number: float, report_data: ReportData) -> bool:
        """检查数值是否在源数据中"""
        for mechanism in report_data.impact_data.mechanisms:
            if mechanism.value is not None and abs(mechanism.value - number) < 0.01:
                return True
        return False


class ValidationReportGenerator:
    """验证报告生成器"""
    
    def __init__(self):
        """初始化生成器"""
        pass
    
    def generate_validation_report(
        self,
        consistency_result: ConsistencyCheckResult,
        traceability_result: TraceabilityCheckResult,
        hallucination_result: HallucinationCheckResult,
        output_path: str
    ) -> None:
        """
        生成详细的验证报告
        
        Args:
            consistency_result: 一致性检查结果
            traceability_result: 可追溯性检查结果
            hallucination_result: 幻觉检测结果
            output_path: 输出文件路径
        """
        report_lines = []
        
        # 标题
        report_lines.append("=" * 80)
        report_lines.append("报告验证结果")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        # 1. 数据一致性结果
        report_lines.append("## 1. 数据一致性验证")
        report_lines.append("-" * 80)
        report_lines.append(f"验证结果: {'✅ 通过' if consistency_result.is_consistent else '❌ 失败'}")
        report_lines.append(f"检查的数值数量: {len(consistency_result.checked_values)}")
        report_lines.append(f"发现的不一致项: {len(consistency_result.inconsistencies)}")
        
        if consistency_result.inconsistencies:
            report_lines.append("\n不一致详情:")
            for i, inconsistency in enumerate(consistency_result.inconsistencies, 1):
                report_lines.append(f"  {i}. {inconsistency}")
        
        report_lines.append("")
        
        # 2. 可追溯性结果
        report_lines.append("## 2. 可追溯性验证")
        report_lines.append("-" * 80)
        report_lines.append(f"总数值数量: {traceability_result.total_values}")
        report_lines.append(f"可追溯数值: {traceability_result.traceable_values}")
        report_lines.append(f"可追溯率: {traceability_result.traceability_rate:.2%}")
        report_lines.append(f"验证结果: {'✅ 通过' if traceability_result.traceability_rate >= 0.8 else '❌ 失败'}")
        
        if traceability_result.untraceable_items:
            report_lines.append(f"\n未追溯项 ({len(traceability_result.untraceable_items)}):")
            for i, item in enumerate(traceability_result.untraceable_items[:10], 1):
                report_lines.append(f"  {i}. {item}")
            if len(traceability_result.untraceable_items) > 10:
                report_lines.append(f"  ... 还有 {len(traceability_result.untraceable_items) - 10} 项")
        
        report_lines.append("")
        
        # 3. AI幻觉检测结果
        report_lines.append("## 3. AI幻觉检测")
        report_lines.append("-" * 80)
        report_lines.append(f"总陈述数量: {hallucination_result.total_statements}")
        report_lines.append(f"检测到的幻觉: {hallucination_result.hallucination_count}")
        report_lines.append(f"幻觉率: {hallucination_result.hallucination_rate:.2%}")
        report_lines.append(f"验证结果: {'✅ 通过' if hallucination_result.hallucination_count == 0 else '⚠️ 警告'}")
        
        if hallucination_result.hallucinations:
            report_lines.append(f"\n检测到的幻觉 ({len(hallucination_result.hallucinations)}):")
            for i, hallucination in enumerate(hallucination_result.hallucinations[:5], 1):
                report_lines.append(f"  {i}. 章节: {hallucination['section']}")
                report_lines.append(f"     原因: {hallucination['reason']}")
                report_lines.append(f"     内容: {hallucination['sentence']}")
                report_lines.append("")
            if len(hallucination_result.hallucinations) > 5:
                report_lines.append(f"  ... 还有 {len(hallucination_result.hallucinations) - 5} 项")
        
        report_lines.append("")
        
        # 总结
        report_lines.append("=" * 80)
        report_lines.append("## 总结")
        report_lines.append("-" * 80)
        
        all_passed = (
            consistency_result.is_consistent and
            traceability_result.traceability_rate >= 0.8 and
            hallucination_result.hallucination_count == 0
        )
        
        report_lines.append(f"整体验证结果: {'✅ 全部通过' if all_passed else '❌ 存在问题'}")
        report_lines.append("")
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        print(f"验证报告已生成: {output_path}")
