"""客户側结构化输出处理器"""

from typing import Dict, List, Any, Optional
import re
import asyncio
from ..models.schemas import CustomerModel, ValueRecognition, AnalysisConfig
from ..engines.llm_engine import LLMEngine
from ..utils.logger import get_logger

logger = get_logger(__name__)


class CustomerProcessor:
    """客户側结构化输出处理器"""
    
    def __init__(self, llm_engine: Optional[LLMEngine] = None):
        self.llm_engine = llm_engine
    
    def _extract_customer_from_raw_text(self, raw_text: str) -> List[str]:
        """从原始文本中提取客户对话"""
        customer_content = []
        
        # 按行分割并查找客户对话
        lines = raw_text.split('\n')
        for line in lines:
            line = line.strip()
            if line:
                # 检查是否是客户对话（客户：开头或类似模式）
                if line.startswith('客户：'):
                    content = line.replace('客户：', '').strip()
                    if content:
                        customer_content.append(content)
                elif re.match(r'^(用户|顾客|买家)：', line):
                    content = re.sub(r'^(用户|顾客|买家)：', '', line).strip()
                    if content:
                        customer_content.append(content)
        
        return customer_content
        
    async def analyze(self, 
                     processed_text: Dict[str, Any],
                     config: AnalysisConfig) -> CustomerModel:
        """分析客户侧信息"""
        
        try:
            logger.info("开始客户侧分析")
            
            # 提取客户对话内容 - 多种路径尝试
            customer_content = []
            
            # 尝试从不同的数据结构中提取客户内容
            if 'content_analysis' in processed_text:
                customer_content = processed_text['content_analysis'].get('customer_content', [])
            elif 'customer_content' in processed_text:
                customer_content = processed_text['customer_content']
            elif 'speakers' in processed_text:
                # 从说话者分析中提取客户内容
                for speaker_data in processed_text['speakers']:
                    if speaker_data.get('role') == '客户':
                        customer_content.extend(speaker_data.get('content', []))
            
            # 如果还是没有，尝试从原始文本中提取
            if not customer_content:
                raw_text = processed_text.get('raw_text', '')
                customer_content = self._extract_customer_from_raw_text(raw_text)
            
            customer_text = ' '.join(customer_content) if isinstance(customer_content, list) else str(customer_content)
            
            if not customer_text.strip():
                logger.warning("未找到客户对话内容")
                return CustomerModel(
                    summary="无客户对话内容",
                    questions=[],
                    value_recognition=ValueRecognition.UNCLEAR,
                    attitude_score=0.0
                )
            
            # 并行执行各项分析
            tasks = [
                self._analyze_customer_summary(customer_text),
                self._extract_customer_questions(customer_text),
                self._analyze_value_recognition(customer_text),
                self._calculate_attitude_score(customer_text)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # 构建结果
            customer_result = CustomerModel(
                summary=results[0],
                questions=results[1],
                value_recognition=results[2],
                attitude_score=results[3]
            )
            
            logger.info(f"客户侧分析完成，态度评分: {results[3]:.2f}")
            
            return customer_result
            
        except Exception as e:
            logger.error(f"客户侧分析失败: {e}")
            raise
    
    async def _analyze_customer_summary(self, customer_text: str) -> str:
        """分析客户总结"""
        
        try:
            prompt = f"""
请分析以下客户在销售通话中的表达，给出客户的态度总结。

客户说的话：
{customer_text}

请按照“认可/不认可 + 主要理由”的格式回答，例如：
- "认可：讲的指标确实有帮助"
- "不认可：觉得太贵了，效果不确定"
- "不明确：没有明确表达态度"

请直接给出结论，不要多余的解释。
"""
            
            response = await self.llm_engine.generate(
                prompt=prompt,
                max_tokens=200,
                temperature=0.1
            )
            
            return response.strip()[:200]  # 限制长度
            
        except Exception as e:
            logger.error(f"分析客户总结失败: {e}")
            return "分析失败"
    
    async def _extract_customer_questions(self, customer_text: str) -> List[str]:
        """提取客户问题"""
        
        try:
            # 使用正则表达式提取疑问句
            question_patterns = [
                r'[^。！？]*[？。][^。！？]*',  # 以问号结尾
                r'(什么|怎么|为什么|哪里|哪个|多少|几个)[^。！？]*',  # 疑问词
                r'(是吗|好吗|可以吗|能吗|会吗)[^。！？]*',  # 以吗结尾
                r'(有没有|能不能|可不可以)[^。！？]*'  # 反问
            ]
            
            questions = []
            for pattern in question_patterns:
                matches = re.findall(pattern, customer_text)
                for match in matches:
                    question = match.strip()
                    if len(question) > 5 and question not in questions:  # 去重和过滤太短的
                        questions.append(question)
            
            # 如果正则提取的问题太少，使用LLM补充
            if len(questions) < 2:
                llm_questions = await self._extract_questions_by_llm(customer_text)
                questions.extend(llm_questions)
            
            # 去重并限制数量
            unique_questions = []
            for q in questions:
                if q not in unique_questions and len(unique_questions) < 10:
                    unique_questions.append(q)
            
            return unique_questions
            
        except Exception as e:
            logger.error(f"提取客户问题失败: {e}")
            return []
    
    async def _extract_questions_by_llm(self, customer_text: str) -> List[str]:
        """使用LLM提取客户问题"""
        
        try:
            prompt = f"""
请从以下客户的说话中提取出所有的问题。

客户说的话：
{customer_text}

请用以下格式回答：
问题1：[...]
问题2：[...]

注意：
1. 只提取明确的问题，不要推测
2. 保持原文表达，不要改写
3. 如果没有问题，回答“无问题”
"""
            
            response = await self.llm_engine.generate(
                prompt=prompt,
                max_tokens=300,
                temperature=0.1
            )
            
            # 解析响应
            questions = []
            lines = response.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('问题') and '：' in line:
                    question = line.split('：', 1)[1].strip()
                    if question and question != '无问题' and len(question) > 3:
                        questions.append(question)
            
            return questions
            
        except Exception as e:
            logger.error(f"LLM提取客户问题失败: {e}")
            return []
    
    async def _analyze_value_recognition(self, customer_text: str) -> ValueRecognition:
        """分析对软件价值的认同度"""
        
        try:
            # 认同关键词
            positive_patterns = [
                r'(有用|有帮助|不错|好|可以|行|有意思)',
                r'(确实|真的|正确|准确)',
                r'(向你学习|请教|了解一下)',
                r'(这个功能|这个软件).{0,20}(好|不错|有用)'
            ]
            
            # 不认同关键词
            negative_patterns = [
                r'(不好|不行|不可以|不行|不用)',
                r'(没用|没意思|没必要|不需要)',
                r'(骗人|假的|不可能|不相信)',
                r'(太贵|太贵了|不值|不值得)'
            ]
            
            # 不明确关键词
            unclear_patterns = [
                r'(考虑|想想|再说|回头)',
                r'(不确定|不清楚|不知道)',
                r'(等一下|等等|稍后)'
            ]
            
            # 计算各类别匹配数
            positive_count = sum(1 for pattern in positive_patterns if re.search(pattern, customer_text))
            negative_count = sum(1 for pattern in negative_patterns if re.search(pattern, customer_text))
            unclear_count = sum(1 for pattern in unclear_patterns if re.search(pattern, customer_text))
            
            # 判定结果
            if positive_count > negative_count and positive_count > unclear_count:
                return ValueRecognition.YES
            elif negative_count > positive_count and negative_count > unclear_count:
                return ValueRecognition.NO
            else:
                return ValueRecognition.UNCLEAR
                
        except Exception as e:
            logger.error(f"分析价值认同度失败: {e}")
            return ValueRecognition.UNCLEAR
    
    async def _calculate_attitude_score(self, customer_text: str) -> float:
        """计算客户态度评分 (-1到1)"""
        
        try:
            # 积极态度词汇及权重
            positive_words = {
                '好': 0.3, '不错': 0.4, '可以': 0.3, '行': 0.3,
                '有用': 0.5, '有帮助': 0.5, '有意思': 0.4,
                '确实': 0.4, '真的': 0.4, '正确': 0.4,
                '谢谢': 0.6, '感谢': 0.6, '辛苦': 0.5,
                '向你学习': 0.7, '请教': 0.6
            }
            
            # 消极态度词汇及权重
            negative_words = {
                '不好': -0.4, '不行': -0.4, '不可以': -0.4,
                '没用': -0.5, '没意思': -0.5, '不需要': -0.4,
                '骗人': -0.8, '假的': -0.7, '不可能': -0.6,
                '太贵': -0.6, '不值': -0.5,
                '没空': -0.3, '没时间': -0.3, '很忙': -0.3,
                '不想': -0.4, '不感兴趣': -0.5
            }
            
            # 中性词汇（略微偏消极）
            neutral_words = {
                '考虑': -0.1, '想想': -0.1, '再说': -0.1,
                '不确定': -0.2, '不清楚': -0.2,
                '等一下': -0.1, '回头': -0.1
            }
            
            # 计算总分
            total_score = 0.0
            word_count = 0
            
            # 积极词汇评分
            for word, weight in positive_words.items():
                count = customer_text.count(word)
                if count > 0:
                    total_score += weight * count
                    word_count += count
            
            # 消极词汇评分
            for word, weight in negative_words.items():
                count = customer_text.count(word)
                if count > 0:
                    total_score += weight * count
                    word_count += count
            
            # 中性词汇评分
            for word, weight in neutral_words.items():
                count = customer_text.count(word)
                if count > 0:
                    total_score += weight * count
                    word_count += count
            
            # 归一化到-1到1范围
            if word_count > 0:
                normalized_score = total_score / word_count
                # 限制在-1到1范围内
                return max(-1.0, min(1.0, normalized_score))
            else:
                return 0.0  # 中性
                
        except Exception as e:
            logger.error(f"计算态度评分失败: {e}")
            return 0.0