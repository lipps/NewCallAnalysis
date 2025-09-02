"""功能演绎要点检测处理器"""

from typing import Dict, List, Any, Optional
import re
import asyncio
from ..models.schemas import DeductionModel, EvidenceHit, AnalysisConfig
from ..engines.vector_engine import VectorSearchEngine
from ..engines.rule_engine import RuleEngine
from ..engines.llm_engine import LLMEngine
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DeductionProcessor:
    """功能演绎要点检测处理器"""
    
    def __init__(self, 
                 vector_engine: VectorSearchEngine,
                 rule_engine: RuleEngine,
                 llm_engine: LLMEngine):
        self.vector_engine = vector_engine
        self.rule_engine = rule_engine
        self.llm_engine = llm_engine
        
        # 功能演绎要点检测配置
        self.detection_points = [
            'bs_explained',
            'period_resonance_explained', 
            'control_funds_explained',
            'bubugao_explained',
            'value_quantify_explained',
            'customer_stock_explained'
        ]
        
    async def analyze(self, 
                     processed_text: Dict[str, Any],
                     config: AnalysisConfig) -> DeductionModel:
        """分析功能演绎要点"""
        
        try:
            logger.info("开始功能演绎要点检测")
            
            # 提取销售对话内容
            sales_content = processed_text.get('content_analysis', {}).get('sales_content', [])
            sales_text = ' '.join(sales_content)
            
            # 并行检测各个要点
            tasks = []
            for point in self.detection_points:
                tasks.append(self._detect_point(point, sales_text, processed_text, config))
            
            # 执行并行检测
            detection_results = await asyncio.gather(*tasks)
            
            # 构建检测结果字典
            results = {}
            for i, point in enumerate(self.detection_points):
                results[point] = detection_results[i]
            
            # 构建模型
            deduction_result = DeductionModel(**results)
            
            logger.info(f"功能演绎要点检测完成，命中数量: {sum(1 for r in results.values() if isinstance(r, EvidenceHit) and r.hit)}")
            
            return deduction_result
            
        except Exception as e:
            logger.error(f"功能演绎要点检测失败: {e}")
            raise
    
    async def _detect_point(self, 
                           point: str,
                           sales_text: str,
                           processed_text: Dict[str, Any],
                           config: AnalysisConfig) -> EvidenceHit:
        """检测单个要点"""
        
        try:
            # 1. 规则引擎检测
            rule_result = await self.rule_engine.detect(
                category='deduction',
                point=point,
                text=sales_text
            )
            
            # 如果规则命中且置信度高，直接返回
            if rule_result['hit'] and rule_result['confidence'] > 0.8:
                return EvidenceHit(
                    hit=True,
                    evidence=rule_result['evidence'],
                    confidence=rule_result['confidence']
                )
            
            # 2. 向量检索检测（如果启用）
            vector_result = None
            if config.enable_vector_search:
                vector_result = await self.vector_engine.search_similar(
                    query=f"功能演绎{point}",
                    text=sales_text,
                    category='deduction'
                )
            
            # 3. LLM验证（如果启用）
            llm_result = None
            if config.enable_llm_validation:
                llm_result = await self._llm_validate_point(
                    point, sales_text, rule_result, vector_result
                )
            
            # 4. 综合判定
            final_result = self._combine_results(
                rule_result, vector_result, llm_result, config.confidence_threshold
            )
            
            return EvidenceHit(**final_result)
            
        except Exception as e:
            logger.error(f"检测要点 {point} 失败: {e}")
            return EvidenceHit(hit=False, evidence="", confidence=0.0)
    
    async def _llm_validate_point(self,
                                 point: str,
                                 text: str,
                                 rule_result: Dict[str, Any],
                                 vector_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """LLM验证要点"""
        
        point_descriptions = {
            'bs_explained': '销售是否讲解了买卖点、操盘线、B点S点、趋势信号等内容',
            'period_resonance_explained': '销售是否讲到了周期共振、不同时间级别的行情分析',
            'control_funds_explained': '销售是否提及了主力资金、控盘资金、筹码分布等内容',
            'bubugao_explained': '销售是否讲到了步步高功能、VIP专属指标等内容',
            'value_quantify_explained': '销售是否将功能结合真实案例或量化价值进行演绎',
            'customer_stock_explained': '销售是否分析或演绎了客户提及的具体股票'
        }
        
        prompt = f"""
请分析以下销售对话文本，判断是否包含指定的功能演绎要点。

要点：{point_descriptions.get(point, point)}

销售对话文本：
{text}

请按以下格式回答：
判定结果：是/否
置信度：0.0-1.0之间的数值
证据片段：如果判定为是，请提供具体的证据文本片段（不超过100字）
理由：简要说明判定理由

规则引擎结果：{rule_result.get('hit', False)} (置信度: {rule_result.get('confidence', 0.0)})
向量检索结果：{vector_result.get('similarity', 0.0) if vector_result else 'N/A'}
"""
        
        try:
            response = await self.llm_engine.generate(
                prompt=prompt,
                max_tokens=300,
                temperature=0.1
            )
            
            # 解析LLM响应
            result = self._parse_llm_response(response, point)
            return result
            
        except Exception as e:
            logger.error(f"LLM验证失败: {e}")
            return {'hit': False, 'confidence': 0.0, 'evidence': '', 'reasoning': str(e)}
    
    def _parse_llm_response(self, response: str, point: str) -> Dict[str, Any]:
        """解析LLM响应"""
        
        try:
            lines = response.strip().split('\n')
            result = {'hit': False, 'confidence': 0.0, 'evidence': '', 'reasoning': ''}
            
            for line in lines:
                line = line.strip()
                if line.startswith('判定结果：') or line.startswith('判定结果:'):
                    result['hit'] = '是' in line
                elif line.startswith('置信度：') or line.startswith('置信度:'):
                    try:
                        confidence = re.search(r'\d+\.?\d*', line)
                        if confidence:
                            result['confidence'] = float(confidence.group())
                    except:
                        result['confidence'] = 0.5
                elif line.startswith('证据片段：') or line.startswith('证据片段:'):
                    result['evidence'] = line.split('：', 1)[-1].split(':', 1)[-1].strip()
                elif line.startswith('理由：') or line.startswith('理由:'):
                    result['reasoning'] = line.split('：', 1)[-1].split(':', 1)[-1].strip()
            
            return result
            
        except Exception as e:
            logger.error(f"解析LLM响应失败: {e}")
            return {'hit': False, 'confidence': 0.0, 'evidence': '', 'reasoning': str(e)}
    
    def _combine_results(self,
                        rule_result: Dict[str, Any],
                        vector_result: Optional[Dict[str, Any]],
                        llm_result: Optional[Dict[str, Any]],
                        threshold: float) -> Dict[str, Any]:
        """综合各种检测结果"""
        
        # 权重设置
        rule_weight = 0.4
        vector_weight = 0.3
        llm_weight = 0.3
        
        # 计算综合置信度
        total_confidence = 0.0
        total_weight = 0.0
        
        # 规则引擎结果
        if rule_result.get('confidence', 0) > 0:
            total_confidence += rule_result['confidence'] * rule_weight
            total_weight += rule_weight
        
        # 向量检索结果
        if vector_result and vector_result.get('similarity', 0) > 0:
            total_confidence += vector_result['similarity'] * vector_weight
            total_weight += vector_weight
        
        # LLM验证结果
        if llm_result and llm_result.get('confidence', 0) > 0:
            total_confidence += llm_result['confidence'] * llm_weight
            total_weight += llm_weight
        
        # 计算最终置信度
        final_confidence = total_confidence / total_weight if total_weight > 0 else 0.0
        
        # 判定是否命中
        hit = final_confidence >= threshold
        
        # 选择最佳证据
        evidence = ""
        if rule_result.get('evidence') and len(rule_result['evidence']) > len(evidence):
            evidence = rule_result['evidence']
        if llm_result and llm_result.get('evidence') and len(llm_result['evidence']) > len(evidence):
            evidence = llm_result['evidence']
        
        return {
            'hit': hit,
            'confidence': final_confidence,
            'evidence': evidence[:200] if evidence else ""  # 限制证据长度
        }