"""LLM引擎 - 大语言模型集成和管理"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, AsyncGenerator
from openai import AsyncOpenAI
from dataclasses import dataclass

from ..config.settings import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LLMResponse:
    """LLM响应结果"""
    content: str
    usage: Dict[str, Any]
    model: str
    finish_reason: str
    response_time: float


class LLMEngine:
    """LLM引擎"""
    
    def __init__(self,
                 api_key: str = None,
                 base_url: str = None,
                 model: str = None):
        
        self.api_key = api_key or settings.model.openai_api_key
        self.base_url = base_url or settings.model.openai_base_url
        self.model = model or settings.model.llm_model
        
        # 创建异步客户端，设置超时
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=60.0  # 设置60秒超时
        )
        
        # 请求统计
        self.request_count = 0
        self.total_tokens = 0
        self.error_count = 0
        
        # 请求队列和限流
        self.request_queue = asyncio.Queue()
        self.rate_limiter = asyncio.Semaphore(2)  # 最大并发请求数（降低并发以减少拥堵）
        
    async def generate(self,
                      prompt: str,
                      max_tokens: int = None,
                      temperature: float = None,
                      system_prompt: str = None,
                      stream: bool = False) -> str:
        """生成文本"""
        
        start_time = time.time()
        
        try:
            # 构建消息
            messages = []
            
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            messages.append({
                "role": "user", 
                "content": prompt
            })
            
            # 请求参数
            request_params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens or settings.model.max_tokens,
                "temperature": temperature or settings.model.temperature,
                "stream": stream
            }
            
            # 执行生成
            if stream:
                return await self._generate_stream(**request_params)
            else:
                return await self._generate_sync(**request_params, start_time=start_time)
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"LLM生成失败: {e}")
            raise
    
    async def _generate_sync(self, **kwargs) -> str:
        """同步生成，含重试与指数退避"""

        start_time = kwargs.pop('start_time')

        async with self.rate_limiter:
            max_retries = 3
            base_delay = 1.5
            for attempt in range(max_retries):
                try:
                    # 统一的请求超时
                    response = await asyncio.wait_for(
                        self.client.chat.completions.create(**kwargs),
                        timeout=100.0  # 100秒超时
                    )

                    # 更新统计
                    self.request_count += 1
                    if response.usage:
                        self.total_tokens += response.usage.total_tokens

                    # 记录响应时间
                    response_time = time.time() - start_time

                    if response.choices and response.choices[0].message:
                        content = response.choices[0].message.content
                        logger.debug(
                            f"LLM生成成功，耗时: {response_time:.2f}秒，tokens: {response.usage.total_tokens if response.usage else 0}"
                        )
                        return content
                    else:
                        raise ValueError("LLM返回空响应")

                except (asyncio.TimeoutError, TimeoutError) as e:
                    logger.error(f"LLM请求超时 (尝试 {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(base_delay * (2 ** attempt))
                        continue
                    else:
                        self.error_count += 1
                        raise
                except Exception as e:
                    logger.error(f"LLM请求失败: {type(e).__name__}: {str(e)}")
                    if hasattr(e, 'response') and e.response:
                        try:
                            logger.error(f"响应状态码: {e.response.status_code}")
                            logger.error(f"响应内容: {e.response.text}")
                        except Exception:
                            pass
                    # 对非超时错误也做有限重试
                    if attempt < max_retries - 1:
                        await asyncio.sleep(base_delay * (2 ** attempt))
                        continue
                    else:
                        self.error_count += 1
                        raise
    
    async def _generate_stream(self, **kwargs) -> AsyncGenerator[str, None]:
        """流式生成"""
        
        async with self.rate_limiter:
            try:
                response_stream = await self.client.chat.completions.create(**kwargs)
                
                self.request_count += 1
                
                async for chunk in response_stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                        
            except Exception as e:
                self.error_count += 1
                logger.error(f"LLM流式生成失败: {e}")
                raise
    
    async def batch_generate(self,
                           prompts: List[str],
                           max_tokens: int = None,
                           temperature: float = None,
                           system_prompt: str = None,
                           max_concurrency: int = 3) -> List[str]:
        """批量生成"""
        
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def generate_single(prompt):
            async with semaphore:
                return await self.generate(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system_prompt=system_prompt
                )
        
        # 并发执行所有任务
        tasks = [generate_single(prompt) for prompt in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"批量生成第{i}个任务失败: {result}")
                processed_results.append("")
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def analyze_with_json(self,
                              prompt: str,
                              schema: Dict[str, Any],
                              max_retries: int = 3) -> Dict[str, Any]:
        """使用JSON模式分析"""
        
        # 构建JSON提示
        json_prompt = f"""
{prompt}

请严格按照以下JSON格式返回结果：
{json.dumps(schema, ensure_ascii=False, indent=2)}

重要：
1. 只返回有效的JSON，不要包含其他解释文字
2. 确保所有必需字段都有值
3. 数值字段请使用数字类型，布尔字段请使用true/false
"""
        
        for attempt in range(max_retries):
            try:
                response = await self.generate(
                    prompt=json_prompt,
                    temperature=0.1  # 使用较低温度确保一致性
                )
                
                # 尝试解析JSON
                try:
                    # 清理响应（移除可能的markdown标记等）
                    cleaned_response = response.strip()
                    if cleaned_response.startswith('```json'):
                        cleaned_response = cleaned_response[7:]
                    if cleaned_response.endswith('```'):
                        cleaned_response = cleaned_response[:-3]
                    cleaned_response = cleaned_response.strip()
                    
                    result = json.loads(cleaned_response)
                    logger.debug(f"JSON解析成功，尝试次数: {attempt + 1}")
                    return result
                    
                except json.JSONDecodeError as je:
                    logger.warning(f"JSON解析失败 (尝试 {attempt + 1}/{max_retries}): {je}")
                    logger.debug(f"原始响应: {response}")
                    
                    if attempt == max_retries - 1:
                        # 最后一次尝试，返回错误结构
                        return {"error": "JSON解析失败", "raw_response": response}
                    
            except Exception as e:
                logger.error(f"LLM请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise
        
        return {"error": "生成失败"}
    
    async def validate_and_correct(self,
                                 text: str,
                                 expected_format: str,
                                 validation_prompt: str) -> str:
        """验证和纠正文本"""
        
        try:
            validation_request = f"""
请检查以下文本是否符合要求，如果不符合请进行修正：

原文本：
{text}

要求：
{expected_format}

验证规则：
{validation_prompt}

请返回修正后的文本（如果原文本已经正确，则返回原文本）：
"""
            
            corrected = await self.generate(
                prompt=validation_request,
                temperature=0.1
            )
            
            return corrected.strip()
            
        except Exception as e:
            logger.error(f"文本验证和纠正失败: {e}")
            return text  # 返回原文本
    
    async def summarize(self,
                       text: str,
                       max_length: int = 200,
                       focus: str = None) -> str:
        """文本摘要"""
        
        try:
            summary_prompt = f"""
请对以下文本进行摘要，要求：
1. 摘要长度不超过{max_length}个字符
2. 保留关键信息和要点
3. 语言简洁明了
{f"4. 重点关注：{focus}" if focus else ""}

原文本：
{text}

摘要：
"""
            
            summary = await self.generate(
                prompt=summary_prompt,
                temperature=0.3,
                max_tokens=max_length // 2  # 估算token数量
            )
            
            return summary.strip()
            
        except Exception as e:
            logger.error(f"文本摘要失败: {e}")
            return text[:max_length] + "..." if len(text) > max_length else text
    
    async def extract_entities(self,
                             text: str,
                             entity_types: List[str]) -> Dict[str, List[str]]:
        """实体提取"""
        
        try:
            entity_prompt = f"""
从以下文本中提取指定类型的实体：

实体类型：{', '.join(entity_types)}

文本：
{text}

请按以下JSON格式返回结果：
{{
  "entity_type1": ["实体1", "实体2"],
  "entity_type2": ["实体3", "实体4"]
}}
"""
            
            entities = await self.analyze_with_json(
                prompt=entity_prompt,
                schema={entity_type: [] for entity_type in entity_types}
            )
            
            return entities
            
        except Exception as e:
            logger.error(f"实体提取失败: {e}")
            return {entity_type: [] for entity_type in entity_types}
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取引擎统计信息"""
        
        return {
            "model": self.model,
            "base_url": self.base_url,
            "request_count": self.request_count,
            "total_tokens": self.total_tokens,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.request_count, 1),
            "avg_tokens_per_request": self.total_tokens / max(self.request_count, 1)
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        
        try:
            test_response = await self.generate(
                prompt="请回答：健康检查",
                max_tokens=10,
                temperature=0.0
            )
            
            return {
                "status": "healthy",
                "model": self.model,
                "response": test_response,
                "timestamp": time.time()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy", 
                "error": str(e),
                "timestamp": time.time()
            }


# 全局LLM引擎实例
_llm_engine_instance = None

def get_llm_engine() -> LLMEngine:
    """获取全局LLM引擎实例"""
    global _llm_engine_instance
    
    if _llm_engine_instance is None:
        _llm_engine_instance = LLMEngine()
    
    return _llm_engine_instance
