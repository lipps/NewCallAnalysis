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
                    evidence=rule_result.get('evidence', ''),
                    confidence=rule_result.get('confidence', 0.0),
                    evidence_source='rule'
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
                rule_result=rule_result,
                vector_result=vector_result,
                llm_result=llm_result,
                threshold=config.confidence_threshold,
                max_evidence_length=config.max_evidence_length,
                rule_floor=0.6,
                vector_enabled=config.enable_vector_search,
                llm_enabled=config.enable_llm_validation
            )

            # 调试日志（不影响主流程）
            try:
                try:
                    rule_conf_str = f"{float(rule_result.get('confidence', 0.0) or 0.0):.3f}"
                except Exception:
                    rule_conf_str = str(rule_result.get('confidence'))

                if vector_result:
                    try:
                        vec_sim_str = f"{float(vector_result.get('similarity', 0.0) or 0.0):.3f}"
                    except Exception:
                        vec_sim_str = str(vector_result.get('similarity'))
                else:
                    vec_sim_str = 'N/A'

                if llm_result:
                    try:
                        llm_conf_str = f"{float(llm_result.get('confidence', 0.0) or 0.0):.3f}"
                    except Exception:
                        llm_conf_str = str(llm_result.get('confidence'))
                else:
                    llm_conf_str = 'N/A'

                logger.debug(
                    (
                        f"Deduction[{point}] rule(hit={rule_result.get('hit')}, conf={rule_conf_str}) "
                        f"vec(sim={vec_sim_str}) "
                        f"llm(conf={llm_conf_str}) "
                        f"=> final(hit={final_result['hit']}, conf={final_result['confidence']:.3f}, "
                        f"evidence='{(final_result.get('evidence') or '')[:120]}')"
                    )
                )
            except Exception:
                pass
            
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
重要要求：证据片段必须直接摘自“销售对话文本”的原文，且不可为空，也不可使用“无/N/A/NA/未知”等占位词；
若无法给出原文证据，请返回“判定结果：否”。
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
                            conf_val = float(confidence.group())
                            # 支持百分比与小数两种格式
                            if ('%' in line) or (conf_val > 1.0 and conf_val <= 100.0):
                                conf_val = conf_val / 100.0
                            # 夹取到 [0, 1]
                            conf_val = max(0.0, min(1.0, conf_val))
                            result['confidence'] = conf_val
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
                        threshold: float,
                        max_evidence_length: int,
                        rule_floor: float = 0.6,
                        vector_enabled: bool = True,
                        llm_enabled: bool = True) -> Dict[str, Any]:
        """综合各种检测结果"""
        
        # 权重设置
        rule_weight = 0.4
        vector_weight = 0.3
        llm_weight = 0.3
        
        # 计算综合置信度
        total_confidence = 0.0
        total_weight = 0.0
        
        # 规则引擎结果
        rule_conf_val = float(rule_result.get('confidence', 0) or 0)
        if rule_conf_val > 0:
            total_confidence += rule_conf_val * rule_weight
            total_weight += rule_weight
        
        # 向量检索结果
        vec_sim_val = float(vector_result.get('similarity', 0) or 0) if vector_result else 0.0
        if vec_sim_val > 0:
            total_confidence += vec_sim_val * vector_weight
            total_weight += vector_weight
        
        # LLM验证结果（若无可引用证据则不计分）
        llm_conf_val = float(llm_result.get('confidence', 0) or 0) if llm_result else 0.0
        llm_ev_text = ""
        if llm_result:
            llm_ev_text = str(llm_result.get('evidence') or '').strip().lower()
            invalid_tokens = {
                "无", "n/a", "na", "未知", "none", "null",
                "不适用", "无证据", "无法提供", "空", "不可用",
                "not applicable", "no evidence"
            }
            if (not llm_ev_text) or llm_ev_text in invalid_tokens \
               or llm_ev_text.startswith("不适用") \
               or ("无证据" in llm_ev_text) or ("无法提供" in llm_ev_text):
                llm_conf_val = 0.0
        if llm_conf_val > 0:
            total_confidence += llm_conf_val * llm_weight
            total_weight += llm_weight
        
        # 计算最终置信度
        final_confidence = total_confidence / total_weight if total_weight > 0 else 0.0
        # 夹取到 [0,1]
        final_confidence = max(0.0, min(1.0, final_confidence))
        
        # 判定是否命中
        hit = final_confidence >= threshold

        # 规则兜底：规则命中但 LLM/向量没有有效贡献时，给予保底
        no_vec_llm_signal = not (
            (vector_result and vector_result.get('similarity', 0) > 0) or
            (llm_result and llm_result.get('confidence', 0) > 0)
        )
        if rule_result.get('hit') and no_vec_llm_signal:
            hit = True
            final_confidence = max(final_confidence, rule_floor)
        
        # 选择最佳证据：按贡献优先、长度次之
        rule_ev = str(rule_result.get('evidence') or '')
        llm_ev = str(llm_result.get('evidence')) if llm_result and llm_result.get('evidence') else ''
        vec_ev = str(vector_result.get('document')) if vector_result and vector_result.get('document') else ''

        rule_contrib = rule_conf_val * rule_weight if rule_ev else 0.0
        llm_contrib = llm_conf_val * llm_weight if llm_ev else 0.0
        vec_contrib = vec_sim_val * vector_weight if vec_ev else 0.0

        candidates = [
            (rule_contrib, len(rule_ev), 'rule', rule_ev),
            (llm_contrib, len(llm_ev), 'llm', llm_ev),
            (vec_contrib, len(vec_ev), 'vector', vec_ev)
        ]
        contrib, length, evidence_source, evidence = max(candidates, key=lambda x: (x[0], x[1]))
        if length == 0 and contrib == 0:
            evidence_source = 'none'
            evidence = ''
        if evidence and max_evidence_length:
            evidence = evidence[:max_evidence_length]

        # 记录融合信号
        signals = {
            'rule_confidence': rule_conf_val,
            'vector_similarity': vec_sim_val,
            'llm_confidence': llm_conf_val,
            'rule_weight': rule_weight,
            'vector_weight': vector_weight,
            'llm_weight': llm_weight,
            'final_confidence': final_confidence,
            'threshold': threshold,
            'contributors': [
                src for src, val in (
                    ('rule', rule_conf_val), ('vector', vec_sim_val), ('llm', llm_conf_val)
                ) if val > 0
            ]
        }

        # 如果所有信号均为0或证据来源为 none，则不命中并清零置信度
        if (rule_conf_val <= 0 and vec_sim_val <= 0 and llm_conf_val <= 0) or evidence_source == 'none':
            hit = False
            final_confidence = 0.0

        return {
            'hit': hit,
            'confidence': final_confidence,
            'evidence': evidence if evidence else "",
            'evidence_source': evidence_source,
            'signals': signals
        }
