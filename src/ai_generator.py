"""
AI Text Generator for Case 3 Automation Agent.

This module provides AI-powered text generation with:
- Claude API integration
- Error handling and retry mechanism
- Grounding validation to prevent hallucinations
- Token usage tracking and cost estimation

根据 PROJECT_PLAN.md 第6节 "AI文本生成器" 和第10节 "Grounding验证" 实现。
"""

import logging
import os
import time
from typing import Dict, List, Optional, Any, Tuple
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from anthropic import Anthropic, APIError, RateLimitError, APITimeoutError
from pydantic import BaseModel, Field

from .models import GenerationResult, CitationInfo


# ==================== 配置模型 ====================

class APIConfig(BaseModel):
    """API配置"""
    endpoint: str = Field(description="API endpoint URL")
    api_key: str = Field(description="API密钥")
    model_name: str = Field(default="claude-sonnet-4-5", description="模型名称")
    max_tokens: int = Field(default=4000, description="最大输出tokens")
    temperature: float = Field(default=0.3, description="温度参数(0-1)")
    timeout: int = Field(default=60, description="超时时间(秒)")


class GroundingResult(BaseModel):
    """Grounding验证结果"""
    is_grounded: bool = Field(description="是否基于提供的数据")
    hallucinations: List[str] = Field(
        default_factory=list,
        description="检测到的幻觉内容"
    )
    confidence_score: float = Field(
        default=1.0,
        description="置信度分数(0-1)"
    )
    details: str = Field(default="", description="详细说明")


class TokenUsage(BaseModel):
    """Token使用统计"""
    input_tokens: int = Field(default=0, description="输入tokens")
    output_tokens: int = Field(default=0, description="输出tokens")
    total_tokens: int = Field(default=0, description="总tokens")
    estimated_cost: float = Field(default=0.0, description="估算成本(美元)")


# ==================== AI文本生成器 ====================

class AITextGenerator:
    """
    AI文本生成器

    功能:
    1. 调用Claude API生成自然语言内容
    2. 实现指数退避重试机制
    3. Grounding验证防止幻觉
    4. Token使用统计和成本估算

    使用示例:
    ```python
    config = APIConfig(
        endpoint="https://api.anthropic.com",
        api_key="sk-...",
        model_name="claude-sonnet-4-5"
    )
    generator = AITextGenerator(config)

    result = generator.generate_text(
        prompt_template="Describe {company_name}",
        data={"company_name": "EmergConnect"},
        source_data=source_data
    )
    ```
    """

    # Token定价(美元/1K tokens) - Claude Sonnet 4.5
    PRICING = {
        "input": 0.003,   # $3 per million input tokens
        "output": 0.015   # $15 per million output tokens
    }

    def __init__(self, api_config: APIConfig):
        """
        初始化AI文本生成器

        Args:
            api_config: API配置
        """
        self.config = api_config
        self.logger = logging.getLogger(__name__)

        # 检测使用哪个API提供商
        self.provider = self._detect_provider()
        
        if self.provider == "openai":
            # 初始化OpenAI客户端
            from openai import OpenAI
            # 只在endpoint非空时使用base_url参数
            if api_config.endpoint:
                self.client = OpenAI(
                    api_key=api_config.api_key,
                    base_url=api_config.endpoint
                )
            else:
                # 使用默认的OpenAI endpoint
                self.client = OpenAI(api_key=api_config.api_key)
            self.logger.info(f"Using OpenAI API with model: {api_config.model_name}")
        else:
            # 初始化Anthropic客户端
            if "azure" in api_config.endpoint.lower():
                # Azure AI Foundry使用自定义端点
                self.client = Anthropic(
                    api_key=api_config.api_key,
                    base_url=api_config.endpoint
                )
            else:
                # 标准Anthropic API
                self.client = Anthropic(api_key=api_config.api_key)
            self.logger.info(f"Using Claude API with model: {api_config.model_name}")

        # Token使用统计
        self.total_usage = TokenUsage()

    def _detect_provider(self) -> str:
        """检测使用哪个API提供商"""
        # 优先使用OpenAI（如果配置了OPENAI_API_KEY）
        if os.getenv("OPENAI_API_KEY"):
            return "openai"
        # 检查模型名称
        if "gpt" in self.config.model_name.lower():
            return "openai"
        return "claude"

    def generate_text(
        self,
        prompt_template: str,
        data: Dict[str, Any],
        source_data: Optional[Dict[str, Any]] = None,
        validate_grounding: bool = True
    ) -> GenerationResult:
        """
        生成自然语言文本

        Args:
            prompt_template: Prompt模板(支持 {variable} 占位符)
            data: 填充数据
            source_data: 源数据(用于grounding验证)
            validate_grounding: 是否进行grounding验证

        Returns:
            GenerationResult: 生成结果,包含文本、验证结果、token统计等
        """
        try:
            # 1. 构建Prompt
            prompt = self._build_prompt(prompt_template, data)
            self.logger.debug(f"Built prompt: {prompt[:200]}...")

            # 2. 调用API生成文本
            generated_text, usage = self._call_api(prompt)
            self.logger.info(
                f"Generated {len(generated_text)} characters, "
                f"used {usage.total_tokens} tokens"
            )

            # 3. Grounding验证
            grounding_result = None
            validation_errors = []

            if validate_grounding and source_data:
                grounding_result = self.validate_grounding(
                    generated_text,
                    source_data
                )

                if not grounding_result.is_grounded:
                    validation_errors.append(
                        f"Grounding validation failed: "
                        f"{len(grounding_result.hallucinations)} hallucinations detected"
                    )
                    self.logger.warning(
                        f"Hallucinations detected: {grounding_result.hallucinations}"
                    )

            # 4. 构建可追溯性信息
            traceability_map = self._build_traceability(
                generated_text,
                source_data or {}
            )

            # 5. 更新总Token统计
            self.total_usage.input_tokens += usage.input_tokens
            self.total_usage.output_tokens += usage.output_tokens
            self.total_usage.total_tokens += usage.total_tokens
            self.total_usage.estimated_cost += usage.estimated_cost

            # 6. 返回结果
            return GenerationResult(
                success=True,
                output_path=None,  # 文本内容,不是文件路径
                validation_errors=validation_errors,
                traceability_map=traceability_map,
                metrics={
                    "generated_text": generated_text,
                    "token_usage": usage.model_dump(),
                    "grounding_result": (
                        grounding_result.model_dump() if grounding_result else None
                    ),
                    "total_usage": self.total_usage.model_dump()
                }
            )

        except Exception as e:
            self.logger.error(f"Text generation failed: {str(e)}", exc_info=True)
            return GenerationResult(
                success=False,
                validation_errors=[f"Generation error: {str(e)}"]
            )

    def _build_prompt(
        self,
        template: str,
        data: Dict[str, Any]
    ) -> str:
        """
        构建Prompt

        支持嵌套字段访问,如 {company.name}

        Args:
            template: Prompt模板
            data: 数据字典

        Returns:
            str: 填充后的Prompt
        """
        try:
            # 简单占位符替换
            prompt = template

            for key, value in data.items():
                placeholder = "{" + key + "}"
                if placeholder in prompt:
                    # 处理不同类型的值
                    if isinstance(value, (list, dict)):
                        value_str = str(value)
                    else:
                        value_str = str(value)

                    prompt = prompt.replace(placeholder, value_str)

            return prompt

        except Exception as e:
            self.logger.error(f"Prompt building failed: {str(e)}")
            raise ValueError(f"Failed to build prompt: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError))
    )
    def _call_api(self, prompt: str) -> Tuple[str, TokenUsage]:
        """
        调用AI API (支持Claude和OpenAI)

        实现指数退避重试机制:
        - 最多重试3次
        - 等待时间: 4秒, 8秒, 10秒(最大)
        - 仅对限流和超时错误重试

        Args:
            prompt: Prompt文本

        Returns:
            Tuple[str, TokenUsage]: (生成的文本, Token使用统计)

        Raises:
            APIError: API调用失败
        """
        try:
            start_time = time.time()

            if self.provider == "openai":
                # 调用OpenAI API (使用chat.completions.create)
                response = self.client.chat.completions.create(
                    model=self.config.model_name,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature
                )
                
                elapsed_time = time.time() - start_time
                self.logger.debug(f"OpenAI API call completed in {elapsed_time:.2f}s")
                
                # 提取生成的文本
                generated_text = response.choices[0].message.content
                
                # OpenAI的token使用
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                
            else:
                # 调用Claude API
                response = self.client.messages.create(
                    model=self.config.model_name,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )

                elapsed_time = time.time() - start_time
                self.logger.debug(f"Claude API call completed in {elapsed_time:.2f}s")

                # 提取生成的文本
                generated_text = ""
                if response.content and len(response.content) > 0:
                    generated_text = response.content[0].text

                # 计算Token使用
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens

            total_tokens = input_tokens + output_tokens

            # 计算成本（使用Claude定价作为默认）
            estimated_cost = (
                (input_tokens / 1000) * self.PRICING["input"] +
                (output_tokens / 1000) * self.PRICING["output"]
            )

            usage = TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                estimated_cost=estimated_cost
            )

            return generated_text, usage

        except RateLimitError as e:
            self.logger.warning(f"Rate limit hit, will retry: {str(e)}")
            raise
        except APITimeoutError as e:
            self.logger.warning(f"API timeout, will retry: {str(e)}")
            raise
        except APIError as e:
            self.logger.error(f"API error: {str(e)}")
            raise ValueError(f"API call failed: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            raise ValueError(f"API call failed: {str(e)}")

    def validate_grounding(
        self,
        generated_text: str,
        source_data: Dict[str, Any]
    ) -> GroundingResult:
        """
        验证生成内容是否基于提供的源数据(Grounding验证)

        检查策略:
        1. 提取生成文本中的数值和关键事实
        2. 检查这些信息是否在源数据中存在
        3. 标记可疑的幻觉内容

        Args:
            generated_text: 生成的文本
            source_data: 源数据

        Returns:
            GroundingResult: 验证结果
        """
        hallucinations = []

        try:
            # 简化的grounding检查
            # TODO: 实现更复杂的验证逻辑

            # 1. 检查是否包含源数据中的关键字段
            has_company_name = False
            if "company_name" in source_data:
                company_name = source_data["company_name"]
                if company_name and company_name.lower() in generated_text.lower():
                    has_company_name = True

            # 2. 检查是否有明显的数值不一致
            # (这里只是示例,实际应该更严格)

            # 3. 基本的幻觉检测
            # 检查是否包含未提供的具体数字(简单启发式)
            import re
            numbers_in_text = re.findall(r'\b\d+\.?\d*\b', generated_text)

            if len(numbers_in_text) > 0 and source_data:
                # 检查这些数字是否在源数据中
                source_data_str = str(source_data).lower()

                for num in numbers_in_text:
                    if num not in source_data_str:
                        # 可能是幻觉数字
                        hallucinations.append(
                            f"Numerical value '{num}' not found in source data"
                        )

            # 计算置信度
            confidence_score = 1.0
            if hallucinations:
                confidence_score = max(0.0, 1.0 - len(hallucinations) * 0.2)

            is_grounded = len(hallucinations) == 0

            return GroundingResult(
                is_grounded=is_grounded,
                hallucinations=hallucinations,
                confidence_score=confidence_score,
                details=f"Checked {len(numbers_in_text)} numerical values"
            )

        except Exception as e:
            self.logger.error(f"Grounding validation failed: {str(e)}")
            return GroundingResult(
                is_grounded=False,
                hallucinations=[f"Validation error: {str(e)}"],
                confidence_score=0.0,
                details=str(e)
            )

    def _build_traceability(
        self,
        generated_text: str,
        source_data: Dict[str, Any]
    ) -> List[CitationInfo]:
        """
        构建可追溯性映射

        记录生成内容中的关键陈述及其数据源

        Args:
            generated_text: 生成的文本
            source_data: 源数据

        Returns:
            List[CitationInfo]: 引用信息列表
        """
        citations = []

        try:
            # 提取关键陈述和数据源
            # TODO: 实现更详细的引用跟踪

            # 示例: 如果提到公司名称,记录其来源
            if "company_name" in source_data:
                company_name = source_data["company_name"]
                if company_name and company_name.lower() in generated_text.lower():
                    citations.append(CitationInfo(
                        statement=f"Company name: {company_name}",
                        source_file=source_data.get("source_file", "Unknown"),
                        source_sheet=source_data.get("source_sheet"),
                        source_row=source_data.get("source_row"),
                        source_column="company_name"
                    ))

            return citations

        except Exception as e:
            self.logger.error(f"Traceability building failed: {str(e)}")
            return []

    def get_total_usage(self) -> TokenUsage:
        """
        获取总Token使用统计

        Returns:
            TokenUsage: 累计Token使用情况
        """
        return self.total_usage

    def reset_usage(self):
        """重置Token使用统计"""
        self.total_usage = TokenUsage()
        self.logger.info("Token usage statistics reset")


# ==================== 工厂函数 ====================

def create_generator_from_config(config_module_path: str = "case3_config") -> AITextGenerator:
    """
    从配置文件创建AI生成器

    Args:
        config_module_path: 配置模块路径(默认: case3_config)

    Returns:
        AITextGenerator: AI文本生成器实例
    """
    try:
        # 优先使用OpenAI（如果配置了）
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            # OpenAI官方API不需要自定义endpoint
            endpoint = os.getenv("OPENAI_ENDPOINT", "")  # 空字符串表示使用默认
            model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            
            config = APIConfig(
                endpoint=endpoint,
                api_key=openai_key,
                model_name=model_name
            )
            
            return AITextGenerator(config)
        
        # 否则使用Claude
        api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
        endpoint = os.getenv(
            "ANTHROPIC_ENDPOINT",
            "https://agentinterview-resource.services.ai.azure.com/anthropic/"
        )
        model_name = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")

        if not api_key:
            raise ValueError(
                "API key not found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY "
                "environment variable"
            )

        config = APIConfig(
            endpoint=endpoint,
            api_key=api_key,
            model_name=model_name
        )

        return AITextGenerator(config)

    except Exception as e:
        logging.error(f"Failed to create AI generator: {str(e)}")
        raise


__all__ = [
    'AITextGenerator',
    'APIConfig',
    'GroundingResult',
    'TokenUsage',
    'create_generator_from_config'
]
