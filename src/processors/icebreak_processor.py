"""破冰要点检测处理器"""

from typing import Dict, List, Any, Optional
import re
import asyncio
from ..models.schemas import IcebreakModel, EvidenceHit, AnalysisConfig
from ..engines.vector_engine import VectorSearchEngine
from ..engines.rule_engine import RuleEngine
from ..engines.llm_engine import LLMEngine
from ..utils.logger import get_logger
from ..config.settings import REJECTION_PATTERNS, HANDLING_PATTERNS

logger = get_logger(__name__)


class IcebreakProcessor:
    """破冰要点检测处理器"""
    
    def __init__(self, 
                 vector_engine: VectorSearchEngine,
                 rule_engine: RuleEngine,
                 llm_engine: LLMEngine):
        self.vector_engine = vector_engine
        self.rule_engine = rule_engine
        self.llm_engine = llm_engine
        
        # 破冰要点检测配置
        self.detection_points = [
            'professional_identity',
            'value_help', 
            'time_notice',
            'company_background',
            'free_teach'
        ]
        
    async def analyze(self, 
                     processed_text: Dict[str, Any],
                     config: AnalysisConfig) -> IcebreakModel:
        """分析破冰要点"""
        
        try:
            logger.info("开始破冰要点检测")
            
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
            
            # 检测拒绝相关信息
            refuse_info = await self._detect_refuse_info(processed_text, config)
            results.update(refuse_info)
            
            # 检测预约信息
            appointment_info = await self._detect_appointment(processed_text, config)
            results.update(appointment_info)
            
            # 构建模型
            icebreak_result = IcebreakModel(**results)
            
            logger.info(f"破冰要点检测完成，命中数量: {sum(1 for r in results.values() if isinstance(r, EvidenceHit) and r.hit)}")
            
            return icebreak_result
            
        except Exception as e:
            logger.error(f"破冰要点检测失败: {e}")
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
                category='icebreak',
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
                    query=f"破冰{point}",
                    text=sales_text,
                    category='icebreak'
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
                # 构造安全的调试显示字符串，避免在 f-string 条件中使用格式说明符导致语法错误
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
                        f"Icebreak[{point}] rule(hit={rule_result.get('hit')}, conf={rule_conf_str}) "
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
            'professional_identity': '销售是否表明了专业身份（如益盟操盘手专员、老师、顾问等）',
            'value_help': '销售是否说明了能帮助客户解决问题或带来收益',
            'time_notice': '销售是否告知了沟通需要的时间（如耽误您几分钟）',
            'company_background': '销售是否提及了公司背景或背书（如腾讯投资的上市公司）',
            'free_teach': '销售是否说明了免费服务或免费讲解'
        }
        
        # 为向量检索结果构造安全的显示字符串，避免 f-string 中使用条件格式化导致语法错误
        sim_str = "N/A"
        if vector_result:
            try:
                sim_str = f"{float(vector_result.get('similarity', 0.0)):.3f}"
            except Exception:
                sim_str = str(vector_result.get('similarity'))

        prompt = f"""
请分析以下销售对话文本，判断是否包含指定的破冰要点。

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
向量检索结果：{sim_str}
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
        
        # 增强的无效证据模式
        invalid_evidence_patterns = [
            r"无.*证据",
            r"无符合要求",
            r"不存在.*证据",
            r"无法.*提供",
            r"没有.*原文",
            r"未找到.*片段"
        ]
        
        try:
            if not response:
                return {'hit': False, 'confidence': 0.0, 'evidence': '', 'reasoning': '空响应'}

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
                    evidence = line.split('：', 1)[-1].split(':', 1)[-1].strip()
                    # 检查证据是否有效
                    if any(re.search(pattern, evidence, re.IGNORECASE) for pattern in invalid_evidence_patterns):
                        result['hit'] = False
                        result['confidence'] = 0.0
                        result['evidence'] = ''
                    else:
                        result['evidence'] = evidence
                elif line.startswith('理由：') or line.startswith('理由:'):
                    result['reasoning'] = line.split('：', 1)[-1].split(':', 1)[-1].strip()
            
            # 额外的无效证据检查
            if result['evidence']:
                invalid_tokens = {
                    "无", "n/a", "na", "未知", "none", "null",
                    "不适用", "无证据", "无法提供", "空", "不可用",
                    "not applicable", "no evidence"
                }
                if (result['evidence'].lower() in invalid_tokens or 
                    any(re.search(pattern, result['evidence'], re.IGNORECASE) for pattern in invalid_evidence_patterns)):
                    result['hit'] = False
                    result['confidence'] = 0.0
                    result['evidence'] = ''
            
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

        # 如果所有信号均为0或证据来源为 none，则不命中并清零置信度
        if (rule_conf_val <= 0 and vec_sim_val <= 0 and llm_conf_val <= 0) or evidence_source == 'none':
            hit = False
            final_confidence = 0.0

        # 记录融合信号，便于前端显示与排障
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

        return {
            'hit': hit,
            'confidence': final_confidence,
            'evidence': evidence if evidence else "",
            'evidence_source': evidence_source,
            'signals': signals
        }
    
    async def _detect_refuse_info(self, 
                                 processed_text: Dict[str, Any],
                                 config: AnalysisConfig) -> Dict[str, Any]:
        """检测拒绝相关信息"""
        
        try:
            dialogues = processed_text.get('dialogues', [])
            sales_content = processed_text.get('content_analysis', {}).get('sales_content', [])
            customer_content = processed_text.get('content_analysis', {}).get('customer_content', [])
            customer_text = ' '.join(customer_content)

            # 1) 客户拒绝/抗拒分类（可多选）
            reason_patterns = REJECTION_PATTERNS

            # 2) 销售应对策略识别
            strategy_patterns = HANDLING_PATTERNS

            # 遍历对话，收集客户拒绝与销售应对
            rejection_reasons: List[Dict[str, str]] = []
            handling_strategies: List[Dict[str, str]] = []

            for i, dlg in enumerate(dialogues):
                speaker = dlg.get('speaker')
                content = (dlg.get('content') or '').strip()
                if not content:
                    continue

                # 客户拒绝/抗拒
                if speaker == 'customer':
                    matched_any = False
                    for rtype, pattern in reason_patterns.items():
                        if re.search(pattern, content):
                            rejection_reasons.append({
                                'type': rtype,
                                'quote': content
                            })
                            matched_any = True
                    # 在客户拒绝后，向下寻找1-3条销售应对
                    if matched_any:
                        j = i + 1
                        sales_seen = 0
                        while j < len(dialogues):
                            dlg2 = dialogues[j]
                            sp2 = dlg2.get('speaker')
                            ct2 = (dlg2.get('content') or '').strip()
                            if sp2 == 'customer':
                                break
                            if sp2 == 'sales' and ct2:
                                sales_seen += 1
                                for sname, spattern in strategy_patterns.items():
                                    if re.search(spattern, ct2):
                                        handling_strategies.append({
                                            'strategy': sname,
                                            'quote': ct2
                                        })
                                if sales_seen >= 3:
                                    break
                            j += 1

            # 旧字段的兼容输出
            refuse_reason = ""
            for rtype, pattern in reason_patterns.items():
                if re.search(pattern, customer_text):
                    refuse_reason = rtype
                    break

            refuse_recover_count = len(handling_strategies)

            return {
                'refuse_reason': refuse_reason,
                'refuse_recover_count': refuse_recover_count,
                # 新增返回
                'rejection_reasons': rejection_reasons,
                'handling_strategies': handling_strategies,
                'handle_objection_count': refuse_recover_count,
                # KPI 统计
                'rejection_kpi': (lambda rr: {
                    'total': len(rr),
                    'by_type': [
                        {
                            'type': t,
                            'count': sum(1 for x in rr if x.get('type') == t),
                            'ratio': (sum(1 for x in rr if x.get('type') == t) / len(rr)) if len(rr) else 0.0
                        } for t in reason_patterns.keys()
                    ]
                })(rejection_reasons),
                'handling_kpi': (lambda hs: {
                    'total': len(hs),
                    'by_strategy': [
                        {
                            'strategy': s,
                            'count': sum(1 for x in hs if x.get('strategy') == s),
                            'ratio': (sum(1 for x in hs if x.get('strategy') == s) / len(hs)) if len(hs) else 0.0
                        } for s in strategy_patterns.keys()
                    ]
                })(handling_strategies)
            }
            
        except Exception as e:
            logger.error(f"检测拒绝信息失败: {e}")
            return {
                'refuse_reason': "",
                'refuse_recover_count': 0
            }
    
    async def _detect_appointment(self,
                                processed_text: Dict[str, Any],
                                config: AnalysisConfig) -> Dict[str, Any]:
        """检测预约信息"""
        
        try:
            all_content = processed_text.get('cleaned_text', '')
            
            # 预约关键词
            appointment_patterns = [
                r'(下次|稍后|明天|后天).{0,20}(联系|沟通|电话)',
                r'(预约|约定|安排).{0,10}(时间|通话)',
                r'(什么时候|几点).{0,10}(方便|联系)',
                r'(回头|有空).{0,10}(再|联系|沟通)'
            ]
            
            next_appointment = False
            for pattern in appointment_patterns:
                if re.search(pattern, all_content):
                    next_appointment = True
                    break
            
            return {
                'next_appointment': next_appointment
            }
            
        except Exception as e:
            logger.error(f"检测预约信息失败: {e}")
            return {
                'next_appointment': False
            }
