"""客户情况考察处理器"""

import asyncio
from typing import Dict, Any
from ..engines.llm_engine import LLMEngine
from ..config.settings import settings
from ..models.schemas import CustomerProbingModel, AnalysisConfig
from ..utils.logger import get_logger

logger = get_logger(__name__)

class CustomerProbingProcessor:
    """客户情况考察分析处理器"""

    def __init__(self, llm_engine: LLMEngine):
        self.llm_engine = llm_engine

    def _validate_input(self, processed_text: Dict[str, Any]) -> str:
        """验证输入数据"""
        if not isinstance(processed_text, dict):
            raise ValueError("processed_text must be a dictionary")

        # Try different field names from text processor
        transcript = processed_text.get("full_text", "")
        if not transcript:
            transcript = processed_text.get("original_text", "")
        if not transcript:
            transcript = processed_text.get("cleaned_text", "")

        if not transcript or not isinstance(transcript, str):
            raise ValueError("Invalid or missing transcript text")

        if len(transcript.strip()) < 20:
            logger.warning("Transcript too short for meaningful customer probing analysis")
            return ""

        return transcript.strip()

    def _parse_llm_response(self, llm_response: str) -> CustomerProbingModel:
        """解析LLM响应结果"""
        if not llm_response:
            return CustomerProbingModel()

        response = llm_response.strip()

        # 支持多种判断格式
        positive_indicators = ['YES', '是', 'TRUE', '有', '存在考察', '询问了']
        has_probing = any(indicator in response.upper() for indicator in positive_indicators)

        if has_probing:
            # 提取证据部分，限制长度
            lines = response.split('\n')
            evidence_lines = []
            for line in lines:
                if any(keyword in line for keyword in ['证据', '提及', '询问', '了解', '仓位', '资金', '风险']):
                    evidence_lines.append(line.strip())

            details = ' '.join(evidence_lines) if evidence_lines else response[:200]

            return CustomerProbingModel(
                has_customer_probing=True,
                customer_probing_details=details.strip()[:500]  # 限制长度
            )
        else:
            return CustomerProbingModel(
                has_customer_probing=False,
                customer_probing_details=""
            )

    async def analyze(self, processed_text: Dict[str, Any], config: AnalysisConfig) -> Dict[str, Any]:
        """
        使用LLM分析是否存在客户情况考察
        """
        try:
            # 输入验证
            transcript = self._validate_input(processed_text)
            if not transcript:
                logger.info("Transcript too short, skipping customer probing analysis")
                return CustomerProbingModel().model_dump()

            # 构建提示词
            prompt = settings.CUSTOMER_PROBING_PROMPT.format(transcript=transcript)

            # 检查配置是否启用LLM
            if not config.enable_llm_validation:
                logger.info("LLM validation disabled, skipping customer probing analysis")
                return CustomerProbingModel().model_dump()

            # 调用LLM引擎进行分析，添加超时控制
            logger.info("Starting customer probing analysis with LLM")
            llm_response = await asyncio.wait_for(
                self.llm_engine.generate(
                    prompt,
                    max_tokens=300,
                    temperature=0.1
                ),
                timeout=120.0  # 增加到2分钟超时
            )

            # 解析响应
            model = self._parse_llm_response(llm_response)

            logger.info(f"Customer probing analysis completed: {model.has_customer_probing}")
            return model.model_dump()

        except asyncio.TimeoutError:
            logger.error("Customer probing analysis timeout")
            return CustomerProbingModel().model_dump()
        except ValueError as e:
            logger.error(f"Input validation error in customer probing analysis: {e}")
            return CustomerProbingModel().model_dump()
        except Exception as e:
            logger.error(f"Customer probing analysis failed: {e}")
            return CustomerProbingModel().model_dump()
