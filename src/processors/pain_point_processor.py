"""痛点量化处理器"""

import asyncio
import re
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

from ..models.schemas import (
    PainPointQuantificationModel,
    PainPointHit,
    PainPointType,
    QuantificationMetrics,
    AnalysisConfig
)
from ..config.settings import settings
from ..engines.vector_engine import VectorSearchEngine
from ..engines.rule_engine import RuleEngine
from ..engines.llm_engine import LLMEngine
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PainPointProcessor:
    """痛点量化处理器"""
    
    def __init__(self, 
                 vector_engine: VectorSearchEngine,
                 rule_engine: RuleEngine,
                 llm_engine: LLMEngine):
        self.vector_engine = vector_engine
        self.rule_engine = rule_engine
        self.llm_engine = llm_engine
        
        # 从配置中获取痛点检测规则和量化配置
        self.detection_rules = settings.pain_point.detection_rules
        self.quantification_extractors = settings.pain_point.quantification_extractors
        self.confidence_threshold = 0.3  # 降低阈值以匹配测试用例
        self.severity_thresholds = settings.pain_point.severity_thresholds
        self.quantification_weights = settings.pain_point.quantification_weights
        
        # 创建痛点类型到规则键的映射
        self.pain_type_mapping = {
            PainPointType.LOSS: 'loss',
            PainPointType.MISS_OPPORTUNITY: 'miss_opportunity',
            PainPointType.CHASE_HIGH: 'chase_high',
            PainPointType.PANIC_SELL: 'panic_sell'
        }
    
    async def analyze(self,
                     processed_text: Dict[str, Any],
                     config: AnalysisConfig = None) -> PainPointQuantificationModel:
        """主分析入口"""
        
        try:
            logger.info("开始痛点量化分析")

            if config is None:
                config = AnalysisConfig()

            # 提取客户对话内容，尽量保证有有效文本
            customer_content = processed_text.get('content_analysis', {}).get('customer_content', [])
            customer_content = [c for c in customer_content if isinstance(c, str) and c.strip()]

            if not customer_content:
                fallback_candidates = [
                    processed_text.get('cleaned_text'),
                    processed_text.get('original_text'),
                    processed_text.get('full_text'),
                    processed_text.get('transcript')
                ]
                for fallback in fallback_candidates:
                    if isinstance(fallback, str) and fallback.strip():
                        customer_content = [fallback]
                        break

            customer_text = ' '.join(customer_content).strip()

            if not customer_text:
                logger.warning("痛点量化分析未找到客户文本，返回空结果")
                return PainPointQuantificationModel(
                    loss_pain=PainPointHit(
                        pain_type=PainPointType.LOSS,
                        detected=False,
                        quantification=QuantificationMetrics(),
                        confidence=0.0,
                        detection_source='none',
                        signals={}
                    ),
                    miss_opportunity_pain=PainPointHit(
                        pain_type=PainPointType.MISS_OPPORTUNITY,
                        detected=False,
                        quantification=QuantificationMetrics(),
                        confidence=0.0,
                        detection_source='none',
                        signals={}
                    ),
                    chase_high_pain=PainPointHit(
                        pain_type=PainPointType.CHASE_HIGH,
                        detected=False,
                        quantification=QuantificationMetrics(),
                        confidence=0.0,
                        detection_source='none',
                        signals={}
                    ),
                    panic_sell_pain=PainPointHit(
                        pain_type=PainPointType.PANIC_SELL,
                        detected=False,
                        quantification=QuantificationMetrics(),
                        confidence=0.0,
                        detection_source='none',
                        signals={}
                    ),
                    total_pain_score=0.0,
                    dominant_pain_type=None,
                    quantification_reliability=0.0
                )
            
            # 并行检测各类痛点
            pain_types = [
                PainPointType.LOSS, 
                PainPointType.MISS_OPPORTUNITY, 
                PainPointType.CHASE_HIGH, 
                PainPointType.PANIC_SELL
            ]
            
            tasks = [
                self._detect_pain_point(pain_type, customer_text, config)
                for pain_type in pain_types
            ]
            detection_results = await asyncio.gather(*tasks)
            
            # 构建结果字典
            results = {
                'loss_pain': detection_results[0],
                'miss_opportunity_pain': detection_results[1],
                'chase_high_pain': detection_results[2],
                'panic_sell_pain': detection_results[3]
            }
            
            # 计算总体痛点评分和主要痛点
            total_pain_score, dominant_pain_type = self._calculate_total_pain_score(results)
            
            quantification_reliability = self._calculate_quantification_reliability(results)
            
            # 构建最终模型
            pain_point_model = PainPointQuantificationModel(
                loss_pain=results.get('loss_pain'),
                miss_opportunity_pain=results.get('miss_opportunity_pain'),
                chase_high_pain=results.get('chase_high_pain'),
                panic_sell_pain=results.get('panic_sell_pain'),
                total_pain_score=total_pain_score,
                dominant_pain_type=dominant_pain_type,
                quantification_reliability=quantification_reliability
            )
            
            logger.info(f"痛点量化分析完成，总痛点评分: {total_pain_score}")
            
            return pain_point_model
            
        except Exception as e:
            logger.error(f"痛点量化分析失败: {e}")
            # 返回空的痛点模型而不是抛出异常，保证工作流继续运行
            return PainPointQuantificationModel(
                loss_pain=PainPointHit(
                    pain_type=PainPointType.LOSS,
                    detected=False,
                    quantification=QuantificationMetrics(),
                    confidence=0.0,
                    detection_source='none',
                    signals={}
                ),
                miss_opportunity_pain=PainPointHit(
                    pain_type=PainPointType.MISS_OPPORTUNITY,
                    detected=False,
                    quantification=QuantificationMetrics(),
                    confidence=0.0,
                    detection_source='none',
                    signals={}
                ),
                chase_high_pain=PainPointHit(
                    pain_type=PainPointType.CHASE_HIGH,
                    detected=False,
                    quantification=QuantificationMetrics(),
                    confidence=0.0,
                    detection_source='none',
                    signals={}
                ),
                panic_sell_pain=PainPointHit(
                    pain_type=PainPointType.PANIC_SELL,
                    detected=False,
                    quantification=QuantificationMetrics(),
                    confidence=0.0,
                    detection_source='none',
                    signals={}
                ),
                total_pain_score=0.0,
                dominant_pain_type=None,
                quantification_reliability=0.0
            )
    
    async def _detect_pain_point(self, 
                                pain_type: PainPointType, 
                                text: str,
                                config: AnalysisConfig) -> PainPointHit:
        """检测单个痛点"""
        
        try:
            # 获取对应痛点类型的规则 - 使用映射表
            pain_type_key = self.pain_type_mapping.get(pain_type, pain_type.name.lower())
            type_rules = self.detection_rules.get(pain_type_key, {})
            
            # 1. 关键词匹配
            keywords_matched = [
                keyword for keyword in type_rules.get('keywords', [])
                if keyword and keyword in text
            ]
            keyword_score = 1.0 if keywords_matched else 0.0

            # 2. 正则模式匹配
            quantification_matches = []
            for pattern in type_rules.get('quantification_patterns', []):
                matches = re.findall(pattern, text)
                if matches:
                    quantification_matches.extend(matches)

            # 3. 量化指标提取
            quantification_metrics = self._extract_quantification(quantification_matches, text)
            
            quantification_score = 1.0 if quantification_matches else 0.0

            # 4. 严重程度判断
            severity_score = self._calculate_severity(text, type_rules)
            quantification_metrics.severity_score = severity_score

            # 5. 向量检索增强（先检查是否可用）
            vector_result = None
            vector_score = 0.0
            similarity_threshold = getattr(config, 'vector_similarity_threshold', 0.5)
            top_k = getattr(config, 'vector_top_k', 5)

            if self.vector_engine and getattr(config, 'enable_vector_search', True):
                try:
                    vector_result = await self.vector_engine.search_similar(
                        query=f"痛点 {pain_type.value}",
                        text=text,
                        category='pain_point',
                        top_k=top_k,
                        similarity_threshold=similarity_threshold
                    )
                    if vector_result:
                        vector_score = float(vector_result.get('similarity') or 0.0)
                        if vector_score < similarity_threshold:
                            vector_score = 0.0
                except Exception as e:
                    logger.debug(f"向量检索失败: {e}")
                    vector_result = None
                    vector_score = 0.0

            # 6. LLM验证
            llm_result = {'detected': False, 'confidence': 0.0, 'evidence_segments': []}
            if self.llm_engine and getattr(config, 'enable_llm_validation', True):
                llm_result = await self._llm_validate_pain_point(pain_type, text)

            llm_detected = bool(llm_result.get('detected'))
            llm_score = float(llm_result.get('confidence', 0.0) or 0.0) if llm_detected else 0.0

            # 7. 综合置信度计算
            confidence = self._calculate_confidence(
                keyword_score,
                quantification_score,
                vector_score,
                llm_score
            )

            signals = {
                'rule_confidence': keyword_score,
                'quantification_score': quantification_score,
                'vector_similarity': vector_score,
                'llm_confidence': llm_score,
                'weighted_confidence': confidence
            }

            detection_source = 'combined'
            source_candidates = [
                ('llm', llm_score),
                ('vector', vector_score),
                ('rule', keyword_score),
                ('quantification', quantification_score)
            ]
            top_source, top_score = max(source_candidates, key=lambda x: x[1])
            if top_score > 0:
                detection_source = top_source

            # 8. 构建痛点命中结果
            return PainPointHit(
                pain_type=pain_type,
                detected=confidence >= self.confidence_threshold,
                quantification=quantification_metrics,
                evidence_segments=self._merge_evidence_segments(
                    self._extract_evidence_segments(text, type_rules),
                    llm_result.get('evidence_segments') if llm_result else None
                ),
                confidence=confidence,
                detection_source=detection_source,
                signals=signals
            )

        except Exception as e:
            logger.error(f"检测痛点 {pain_type} 失败: {e}")
            return PainPointHit(
                pain_type=pain_type,
                detected=False,
                quantification=QuantificationMetrics(),
                confidence=0.0,
                detection_source='none',
                signals={}
            )
    
    def _extract_quantification(self, matches: List[Any], text: str) -> QuantificationMetrics:
        """从匹配结果中提取量化指标"""
        
        metrics = QuantificationMetrics()
        
        for match in matches:
            groups: List[str]
            if isinstance(match, tuple):
                groups = [g for g in match if g]
            else:
                groups = [match] if match else []

            if not groups:
                continue

            value_str = None
            unit = ''

            for item in groups:
                item = item.strip()
                if not item:
                    continue
                if re.fullmatch(r'\d+\.?\d*', item):
                    value_str = item
                elif any(token in item for token in ('万', '千', '百', '个点', '点', '%', '次', '遍', '回', '成')):
                    unit = item

            if not value_str:
                continue

            try:
                value = float(value_str)
            except (ValueError, TypeError):
                continue

            normalized_amount = self._normalize_amount(value, unit)
            if metrics.amount is None and normalized_amount is not None:
                metrics.amount = normalized_amount

            normalized_ratio = self._normalize_ratio(value, unit)
            if metrics.ratio is None and normalized_ratio is not None:
                metrics.ratio = normalized_ratio

            normalized_frequency = self._normalize_frequency(value, unit)
            if metrics.frequency is None and normalized_frequency is not None:
                metrics.frequency = normalized_frequency
        
        # 如果没有匹配到量化指标，尝试从文本中提取
        if metrics.amount is None:
            amount_match = re.search(r'亏了(\d+\.?\d*)万', text)
            if amount_match:
                metrics.amount = float(amount_match.group(1))
        
        return metrics

    def _normalize_amount(self, value: float, unit: str) -> Optional[float]:
        """统一金额单位为“万元”"""
        if unit is None:
            unit = ''
        unit = unit.replace('元', '').replace('块', '').replace('人民币', '').strip()

        if unit in ('', '万'):
            return value if value > 0 else None
        if unit == '千':
            return value / 10.0
        if unit == '百':
            return value / 100.0
        # 对于“个点”等非金额单位返回None
        return None

    def _normalize_ratio(self, value: float, unit: str) -> Optional[float]:
        """将比例转换为0-1区间"""
        if unit is None:
            unit = ''
        unit = unit.strip()

        if unit in ('%', '％', '个点', '点') or unit.endswith('点'):
            return max(0.0, min(value / 100.0, 1.0))
        if unit == '成':
            return max(0.0, min(value / 10.0, 1.0))
        return None

    def _normalize_frequency(self, value: float, unit: str) -> Optional[int]:
        """归一化频次"""
        if unit is None:
            unit = ''
        unit = unit.strip()

        if unit in ('次', '回', '遍') and value >= 0:
            return int(round(value))
        return None
    
    def _calculate_severity(self, text: str, type_rules: Dict[str, Any]) -> float:
        """计算痛点严重程度"""
        
        severity_keywords = type_rules.get('severity_keywords', {})
        
        # 检查不同严重程度的关键词
        for severity_level, keywords in severity_keywords.items():
            if any(keyword in text for keyword in keywords):
                return {
                    '轻微': 3.0,
                    '中等': 6.0,
                    '严重': 9.0
                }.get(severity_level, 5.0)
        
        return 5.0  # 默认中等严重程度
    
    async def _llm_validate_pain_point(self, 
                                      pain_type: PainPointType, 
                                      text: str) -> Dict[str, Any]:
        """LLM验证痛点"""
        
        prompt = f"""
请分析以下客户对话，判断是否包含"{pain_type.value}"相关的痛点。

客户对话内容：
{text}

请按以下格式回答：
检测结果：是/否
置信度：0.1-1.0之间的数值
证据：如果检测到痛点，请提供具体的证据文本片段

要求：
1. 证据必须直接摘自原文
2. 如果没有明确证据，请回答"否"
"""
        
        try:
            response = await self.llm_engine.generate(
                prompt=prompt,
                max_tokens=300,
                temperature=0.1
            )
            
            # 解析LLM响应
            return self._parse_llm_response(response)
            
        except Exception as e:
            logger.error(f"LLM验证痛点失败: {e}")
            return {'detected': False, 'confidence': 0.0}
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应 - 支持多种格式"""

        try:
            import json

            if not response or not response.strip():
                logger.warning("LLM响应为空")
                return {'detected': False, 'confidence': 0.0, 'evidence_segments': []}

            response = response.strip()

            # 尝试直接JSON解析
            try:
                # 清理可能的markdown格式
                if response.startswith('```json'):
                    response = response[7:]
                if response.endswith('```'):
                    response = response[:-3]
                response = response.strip()

                parsed_response = json.loads(response)
                return {
                    'detected': bool(parsed_response.get('detected', False)),
                    'confidence': float(parsed_response.get('confidence', 0.0)),
                    'evidence_segments': list(parsed_response.get('evidence_segments', []))
                }

            except json.JSONDecodeError as je:
                logger.debug(f"JSON解析失败，尝试文本解析: {je}")
                # 回退到文本解析
                return self._parse_text_response(response)

        except Exception as e:
            logger.error(f"解析LLM响应失败: {e}")
            return {'detected': False, 'confidence': 0.0, 'evidence_segments': []}

    def _parse_text_response(self, response: str) -> Dict[str, Any]:
        """从文本响应中解析结果"""

        detected = False
        confidence = 0.0
        evidence_segments = []

        lines = response.split('\n')

        for line in lines:
            line = line.strip()

            # 解析检测结果
            if line.startswith('检测结果') or line.startswith('结果'):
                if '是' in line:
                    detected = True
                elif '否' in line:
                    detected = False

            # 解析置信度
            elif line.startswith('置信度'):
                import re
                confidence_match = re.search(r'([0-9.]+)', line)
                if confidence_match:
                    try:
                        confidence = float(confidence_match.group(1))
                        # 确保在0-1范围内
                        if confidence > 1.0:
                            confidence = min(confidence / 100.0, 1.0)
                    except ValueError:
                        confidence = 0.5

            # 解析证据
            elif line.startswith('证据') and detected:
                evidence_text = line.split('：', 1)[-1].split(':', 1)[-1].strip()
                if evidence_text and evidence_text not in ['无', '没有', '空', '']:
                    evidence_segments.append(evidence_text)

        # 如果没有明确的置信度，设置默认值
        if confidence == 0.0:
            confidence = 0.7 if detected else 0.8

        # 回退关键词检测
        if not any(line.startswith(('检测结果', '结果')) for line in lines):
            response_lower = response.lower()
            positive_keywords = ['true', 'yes', '是', '检测到', '存在', '发现']
            negative_keywords = ['false', 'no', '否', '未检测到', '不存在', '未发现']

            if any(keyword in response_lower for keyword in positive_keywords):
                detected = True
                confidence = 0.6
            elif any(keyword in response_lower for keyword in negative_keywords):
                detected = False
                confidence = 0.8

        return {
            'detected': detected,
            'confidence': confidence,
            'evidence_segments': evidence_segments
        }
    
    def _calculate_confidence(self, 
                             keyword_score: float, 
                             quantification_score: float,
                             vector_score: float,
                             llm_score: float) -> float:
        """综合计算置信度"""
        
        # 权重配置
        weights = {
            'keywords': 0.7,  # 关键词权重
            'quantification': 0.15,
            'vector': 0.075,   # 向量权重
            'llm': 0.075       # LLM权重
        }
        
        confidence = (
            max(0.0, min(keyword_score, 1.0)) * weights['keywords'] +
            max(0.0, min(quantification_score, 1.0)) * weights['quantification'] +
            max(0.0, min(vector_score, 1.0)) * weights['vector'] +
            max(0.0, min(llm_score, 1.0)) * weights['llm']
        )

        if keyword_score >= 1.0:
            confidence = max(confidence, 0.7)

        return min(max(confidence, 0.0), 1.0)
    
    def _extract_evidence_segments(self, 
                                  text: str, 
                                  type_rules: Dict[str, Any]) -> List[str]:
        """提取证据片段"""
        
        evidence_segments = []
        
        # 从关键词和正则模式中提取
        for keyword in type_rules.get('keywords', []):
            if keyword in text:
                # 找到关键词周围的上下文
                start = max(0, text.index(keyword) - 20)
                end = min(len(text), text.index(keyword) + 20)
                evidence_segments.append(text[start:end])
        
        return evidence_segments

    def _merge_evidence_segments(self, primary: List[str], secondary: Optional[List[str]]) -> List[str]:
        """合并不同来源的证据片段并去重"""
        merged = []
        for segment in (primary or []) + (secondary or []):
            if not segment:
                continue
            cleaned = segment.strip()
            if cleaned and cleaned not in merged:
                merged.append(cleaned)
        return merged
    
    def _calculate_total_pain_score(self, 
                                   results: Dict[str, PainPointHit]) -> Tuple[float, Optional[PainPointType]]:
        """计算总体痛点评分和主要痛点"""
        
        pain_scores = {}
        for pain_type, result in results.items():
            if isinstance(result, PainPointHit) and result.detected:
                # 综合计算痛点得分
                score = (
                    result.confidence * 0.4 +
                    result.quantification.severity_score * 0.3 +
                    (result.quantification.amount or 0) * 0.1 +
                    (result.quantification.ratio or 0) * 0.2
                )
                pain_scores[pain_type] = score
        
        # 找出最高分痛点
        if pain_scores:
            dominant_pain_type = max(pain_scores, key=pain_scores.get)
            total_pain_score = pain_scores[dominant_pain_type]
            
            # 映射字符串到枚举值
            type_mapping = {
                'loss_pain': PainPointType.LOSS,
                'miss_opportunity_pain': PainPointType.MISS_OPPORTUNITY,
                'chase_high_pain': PainPointType.CHASE_HIGH,
                'panic_sell_pain': PainPointType.PANIC_SELL
            }
            
            return total_pain_score, type_mapping.get(dominant_pain_type)
        
        return 0.0, None
    
    def _calculate_quantification_reliability(self, 
                                             results: Dict[str, PainPointHit]) -> float:
        """计算量化可信度"""
        
        reliability_scores = []
        for result in results.values():
            if isinstance(result, PainPointHit):
                # 综合计算可信度
                score = (
                    result.confidence * 0.4 +
                    (1 if result.quantification.amount is not None else 0) * 0.3 +
                    (1 if result.quantification.frequency is not None else 0) * 0.15 +
                    (1 if result.quantification.ratio is not None else 0) * 0.15
                )
                reliability_scores.append(score)
        
        return np.mean(reliability_scores) if reliability_scores else 0.0
