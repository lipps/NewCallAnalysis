"""UI适配器 - 将分析结果转换为UI所需格式

该模块是核心适配层，负责将现有系统的CallAnalysisResult转换为
UI界面所需的标准化格式。采用适配器模式，确保零侵入现有系统。

主要功能：
1. 格式转换：将现有数据结构映射到UI格式
2. 证据增强：结合EvidenceEnhancer提供结构化证据
3. 数据补全：为缺失字段提供合理默认值
4. 性能优化：缓存机制和懒加载处理
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import json

from .evidence_enhancer import EvidenceEnhancer
from ..models.schemas import (
    CallAnalysisResult, EvidenceHit, IcebreakModel, DeductionModel,
    ProcessModel, CustomerModel, ActionsModel, ActionExecution
)

logger = logging.getLogger(__name__)


class UIAdapter:
    """UI格式适配器

    将CallAnalysisResult转换为UI所需的dictForUI格式，
    提供完整的数据映射和格式转换功能。
    """

    def __init__(self,
                 evidence_enhancer: Optional[EvidenceEnhancer] = None,
                 enable_cache: bool = True,
                 cache_size: int = 100):
        """初始化UI适配器

        Args:
            evidence_enhancer: 证据增强器实例
            enable_cache: 是否启用缓存
            cache_size: 缓存大小
        """
        self.evidence_enhancer = evidence_enhancer or EvidenceEnhancer()
        self.enable_cache = enable_cache
        self.cache_size = cache_size

        # 简单的内存缓存
        self._cache: Dict[str, Dict] = {} if enable_cache else {}
        self._cache_stats = {"hits": 0, "misses": 0}

    def convert_to_ui_format(self,
                           result: CallAnalysisResult,
                           processed_text: Optional[Dict] = None,
                           include_metadata: bool = True) -> Dict[str, Any]:
        """转换为UI格式

        这是主要的转换入口，将CallAnalysisResult转换为UI所需的完整格式

        Args:
            result: 分析结果
            processed_text: 处理后的文本数据（包含dialogues等）
            include_metadata: 是否包含元数据

        Returns:
            Dict: UI格式的分析结果
        """
        try:
            # 生成缓存键
            cache_key = self._generate_cache_key(result, processed_text) if self.enable_cache else None

            # 检查缓存
            if cache_key and cache_key in self._cache:
                self._cache_stats["hits"] += 1
                logger.debug(f"Cache hit for call: {result.call_id}")
                return self._cache[cache_key]

            if self.enable_cache:
                self._cache_stats["misses"] += 1

            # 执行转换
            ui_result = {
                "output": {
                    "customer_side": self._map_customer_side(result.customer),
                    "standard_actions": self._map_standard_actions(result.actions, result.process),
                    "opening": self._map_opening(result.icebreak, processed_text),
                    "meta": self._map_meta(result) if include_metadata else {},
                    "metrics": self._map_metrics(result.process),
                    "rejects": self._map_rejects(result.icebreak),
                    "demo": self._map_demo(result.演绎, processed_text),
                    "demo_more": self._map_demo_more(result.演绎, processed_text)
                }
            }

            # 添加适配器元数据
            if include_metadata:
                ui_result["_adapter_metadata"] = {
                    "conversion_timestamp": datetime.now().isoformat(),
                    "adapter_version": "1.0.0",
                    "source_call_id": result.call_id,
                    "has_processed_text": processed_text is not None
                }

            # 缓存结果
            if cache_key:
                self._update_cache(cache_key, ui_result)

            logger.info(f"Successfully converted call {result.call_id} to UI format")
            return ui_result

        except Exception as e:
            logger.error(f"Failed to convert call {result.call_id} to UI format: {e}")
            # 返回基础格式以确保系统稳定性
            return self._create_fallback_ui_result(result)

    def _map_customer_side(self, customer: CustomerModel) -> Dict[str, Any]:
        """映射客户侧数据

        直接映射现有的CustomerModel数据，几乎不需要转换

        Args:
            customer: 客户模型

        Returns:
            Dict: 客户侧UI格式
        """
        return {
            "questions": customer.questions or [],
            "summary": customer.summary or "",
            "value_recognition": customer.value_recognition or "UNCLEAR"
        }

    def _map_standard_actions(self, actions: ActionsModel, process: ProcessModel) -> Dict[str, Any]:
        """映射标准动作数据

        结合ActionsModel和ProcessModel的相关字段

        Args:
            actions: 动作模型
            process: 过程模型

        Returns:
            Dict: 标准动作UI格式
        """
        return {
            "money_ask": {
                "count": process.money_ask_count,
                "quotes": process.money_ask_quotes[:5],  # 限制显示数量
                "total_attempts": process.money_ask_count
            },
            "action_summary": {
                "total_executed": self._count_executed_actions(actions),
                "execution_rate": self._calculate_execution_rate(actions),
                "key_actions": self._get_key_executed_actions(actions)
            }
        }

    def _map_opening(self, icebreak: IcebreakModel, processed_text: Optional[Dict] = None) -> Dict[str, Any]:
        """映射开场白数据

        将IcebreakModel转换为UI格式，使用证据增强器处理证据

        Args:
            icebreak: 破冰模型
            processed_text: 处理文本

        Returns:
            Dict: 开场白UI格式
        """
        return {
            "professional_identity": self._convert_evidence_hit(
                icebreak.professional_identity, processed_text, "专业身份"
            ),
            "value_help": self._convert_evidence_hit(
                icebreak.value_help, processed_text, "帮助价值"
            ),
            "time_notice": self._convert_evidence_hit(
                icebreak.time_notice, processed_text, "时间说明"
            ),
            "tencent_invest": self._convert_evidence_hit(
                icebreak.company_background, processed_text, "腾讯投资"
            ),
            "free_teach": self._convert_evidence_hit(
                icebreak.free_teach, processed_text, "免费讲解"
            )
        }

    def _map_meta(self, result: CallAnalysisResult) -> Dict[str, Any]:
        """映射元数据

        Args:
            result: 分析结果

        Returns:
            Dict: 元数据UI格式
        """
        return {
            "call_id": result.call_id,
            "customer_id": result.customer_id or "",
            "sales_id": result.sales_id or "",
            "call_time": result.call_time or "",
            "analysis_timestamp": result.analysis_timestamp
        }

    def _map_metrics(self, process: ProcessModel) -> Dict[str, Any]:
        """映射指标数据

        直接映射ProcessModel的指标字段

        Args:
            process: 过程模型

        Returns:
            Dict: 指标UI格式
        """
        return {
            "talk_time_min": round(process.explain_duration_min, 2),
            "interactions_per_min": round(process.interaction_rounds_per_min, 2),
            "deal_or_visit": process.deal_or_visit,
            "word_stats": {
                "total_words": process.total_words,
                "sales_words": process.sales_words,
                "customer_words": process.customer_words,
                "sales_ratio": round(process.sales_words / max(process.total_words, 1), 3)
            }
        }

    def _map_rejects(self, icebreak: IcebreakModel) -> Dict[str, Any]:
        """映射拒绝处理数据

        使用IcebreakModel中的拒绝相关字段

        Args:
            icebreak: 破冰模型

        Returns:
            Dict: 拒绝处理UI格式
        """
        return {
            "handle_objection_count": icebreak.handle_objection_count,
            "handling_strategies": icebreak.handling_strategies or [],
            "rejection_reasons": icebreak.rejection_reasons or [],
            "next_appointment": icebreak.next_appointment,
            "rejection_kpi": icebreak.rejection_kpi or {},
            "handling_kpi": icebreak.handling_kpi or {}
        }

    def _map_demo(self, deduction: DeductionModel, processed_text: Optional[Dict] = None) -> Dict[str, Any]:
        """映射演绎数据

        将DeductionModel转换为UI格式，重点处理证据增强

        Args:
            deduction: 演绎模型
            processed_text: 处理文本

        Returns:
            Dict: 演绎UI格式
        """
        return {
            "bs_explained": self._convert_evidence_hit(
                deduction.bs_explained, processed_text, "BS点讲解"
            ),
            "period_resonance_explained": self._convert_evidence_hit(
                deduction.period_resonance_explained, processed_text, "周期共振"
            ),
            "control_funds_explained": self._convert_evidence_hit(
                deduction.control_funds_explained, processed_text, "控盘资金"
            ),
            "bubugao_explained": self._convert_evidence_hit(
                deduction.bubugao_explained, processed_text, "步步高"
            ),
            "value_quantify_explained": self._convert_evidence_hit(
                deduction.value_quantify_explained, processed_text, "价值量化"
            ),
            "customer_stock_explained": self._convert_evidence_hit(
                deduction.customer_stock_explained, processed_text, "客户股票"
            )
        }

    def _map_demo_more(self, deduction: DeductionModel, processed_text: Optional[Dict] = None) -> Dict[str, Any]:
        """映射深度演绎数据

        基于现有DeductionModel推断深度分析，这是一个增强功能

        Args:
            deduction: 演绎模型
            processed_text: 处理文本

        Returns:
            Dict: 深度演绎UI格式
        """
        return {
            "bs_explained": {
                "coverage": self._convert_evidence_hit(
                    deduction.bs_explained, processed_text, "BS点覆盖"
                ),
                "depth_effectiveness": self._analyze_depth_effectiveness(
                    deduction.bs_explained, "BS点讲解"
                )
            },
            "period_resonance_explained": {
                "coverage": self._convert_evidence_hit(
                    deduction.period_resonance_explained, processed_text, "周期共振覆盖"
                ),
                "depth_effectiveness": self._analyze_depth_effectiveness(
                    deduction.period_resonance_explained, "周期共振讲解"
                )
            },
            "control_funds_explained": {
                "coverage": self._convert_evidence_hit(
                    deduction.control_funds_explained, processed_text, "控盘资金覆盖"
                ),
                "depth_effectiveness": self._analyze_depth_effectiveness(
                    deduction.control_funds_explained, "控盘资金讲解"
                )
            },
            "bubugao_explained": {
                "coverage": self._convert_evidence_hit(
                    deduction.bubugao_explained, processed_text, "步步高覆盖"
                ),
                "depth_effectiveness": self._analyze_depth_effectiveness(
                    deduction.bubugao_explained, "步步高讲解"
                )
            },
            "value_quantify_explained": {
                "coverage": self._convert_evidence_hit(
                    deduction.value_quantify_explained, processed_text, "价值量化覆盖"
                ),
                "depth_effectiveness": self._analyze_depth_effectiveness(
                    deduction.value_quantify_explained, "价值量化讲解"
                )
            }
        }

    def _convert_evidence_hit(self,
                            evidence_hit: EvidenceHit,
                            processed_text: Optional[Dict] = None,
                            context_hint: Optional[str] = None) -> Dict[str, Any]:
        """转换证据命中为UI格式

        这是核心的证据转换方法，结合EvidenceEnhancer进行增强

        Args:
            evidence_hit: 证据命中对象
            processed_text: 处理文本
            context_hint: 上下文提示

        Returns:
            Dict: UI格式的证据
        """
        try:
            # 使用证据增强器增强证据
            enhanced_evidence = self.evidence_enhancer.enhance_evidence(
                evidence_hit.evidence,
                processed_text,
                context_hint
            )

            return {
                "hit": evidence_hit.hit,
                "evidence": enhanced_evidence,
                "confidence": evidence_hit.confidence,
                "evidence_source": evidence_hit.evidence_source,
                # 保留原始数据用于调试
                "_original_evidence": evidence_hit.evidence if evidence_hit.evidence else ""
            }

        except Exception as e:
            logger.warning(f"Evidence conversion failed for {context_hint}: {e}")
            # 降级处理
            return {
                "hit": evidence_hit.hit,
                "evidence": [{
                    "idx": 0,
                    "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "quote": evidence_hit.evidence[:200] if evidence_hit.evidence else "",
                    "match_type": "fallback",
                    "confidence": 0.1
                }],
                "confidence": evidence_hit.confidence,
                "evidence_source": "fallback"
            }

    def _analyze_depth_effectiveness(self, evidence_hit: EvidenceHit, topic: str) -> Dict[str, Any]:
        """分析深度有效性

        基于现有证据推断讲解的深度和有效性

        Args:
            evidence_hit: 证据命中
            topic: 话题名称

        Returns:
            Dict: 深度有效性分析
        """
        if not evidence_hit.hit:
            return {
                "depth": "无",
                "effectiveness_score": 0,
                "analysis": f"未检测到{topic}相关内容"
            }

        # 基于证据长度和置信度推断深度
        evidence_length = len(evidence_hit.evidence) if evidence_hit.evidence else 0
        confidence = evidence_hit.confidence

        if evidence_length > 100 and confidence > 0.8:
            depth = "深入"
            effectiveness = 0.8 + confidence * 0.2
        elif evidence_length > 50 and confidence > 0.6:
            depth = "适中"
            effectiveness = 0.5 + confidence * 0.3
        else:
            depth = "浅显"
            effectiveness = confidence * 0.5

        return {
            "depth": depth,
            "effectiveness_score": round(min(effectiveness, 1.0), 2),
            "analysis": f"{topic}讲解深度{depth}，有效性评分{round(effectiveness, 2)}"
        }

    def _count_executed_actions(self, actions: ActionsModel) -> int:
        """计算已执行动作数量

        Args:
            actions: 动作模型

        Returns:
            int: 已执行动作数量
        """
        count = 0
        for field_name, field_value in actions.__dict__.items():
            if isinstance(field_value, ActionExecution) and field_value.executed:
                count += 1
        return count

    def _calculate_execution_rate(self, actions: ActionsModel) -> float:
        """计算执行率

        Args:
            actions: 动作模型

        Returns:
            float: 执行率 (0-1)
        """
        total_actions = len([f for f in actions.__dict__.values() if isinstance(f, ActionExecution)])
        executed_actions = self._count_executed_actions(actions)

        return round(executed_actions / max(total_actions, 1), 3)

    def _get_key_executed_actions(self, actions: ActionsModel) -> List[str]:
        """获取关键已执行动作列表

        Args:
            actions: 动作模型

        Returns:
            List[str]: 关键动作列表
        """
        executed_actions = []
        action_name_map = {
            "professional_identity": "专业身份",
            "value_help": "帮助价值",
            "time_notice": "时间说明",
            "company_background": "公司背景",
            "free_teach": "免费讲解",
            "bs_explained": "BS点讲解",
            "period_resonance_explained": "周期共振",
            "control_funds_explained": "控盘资金",
            "bubugao_explained": "步步高",
            "value_quantify_explained": "价值量化",
            "customer_stock_explained": "客户股票"
        }

        for field_name, field_value in actions.__dict__.items():
            if isinstance(field_value, ActionExecution) and field_value.executed:
                chinese_name = action_name_map.get(field_name, field_name)
                executed_actions.append(chinese_name)

        return executed_actions

    def _create_fallback_ui_result(self, result: CallAnalysisResult) -> Dict[str, Any]:
        """创建降级UI结果

        当转换失败时，提供基础的UI格式以保证系统稳定性

        Args:
            result: 分析结果

        Returns:
            Dict: 降级UI格式
        """
        logger.warning(f"Using fallback UI result for call: {result.call_id}")

        return {
            "output": {
                "customer_side": {
                    "questions": [],
                    "summary": "转换失败，请检查数据格式",
                    "value_recognition": "UNCLEAR"
                },
                "standard_actions": {
                    "money_ask": {"count": 0, "quotes": [], "total_attempts": 0},
                    "action_summary": {"total_executed": 0, "execution_rate": 0.0, "key_actions": []}
                },
                "opening": self._create_empty_opening(),
                "meta": {
                    "call_id": result.call_id,
                    "customer_id": result.customer_id or "",
                    "sales_id": result.sales_id or "",
                    "call_time": result.call_time or "",
                    "analysis_timestamp": result.analysis_timestamp
                },
                "metrics": {"talk_time_min": 0.0, "interactions_per_min": 0.0, "deal_or_visit": False},
                "rejects": {"handle_objection_count": 0, "handling_strategies": [], "rejection_reasons": []},
                "demo": self._create_empty_demo(),
                "demo_more": self._create_empty_demo_more()
            },
            "_adapter_metadata": {
                "conversion_timestamp": datetime.now().isoformat(),
                "adapter_version": "1.0.0",
                "source_call_id": result.call_id,
                "conversion_status": "fallback",
                "has_processed_text": False
            }
        }

    def _create_empty_opening(self) -> Dict[str, Any]:
        """创建空的开场白格式"""
        empty_evidence = {"hit": False, "evidence": [], "confidence": 0.0, "evidence_source": "none"}
        return {
            "professional_identity": empty_evidence,
            "value_help": empty_evidence,
            "time_notice": empty_evidence,
            "tencent_invest": empty_evidence,
            "free_teach": empty_evidence
        }

    def _create_empty_demo(self) -> Dict[str, Any]:
        """创建空的演绎格式"""
        empty_evidence = {"hit": False, "evidence": [], "confidence": 0.0, "evidence_source": "none"}
        return {
            "bs_explained": empty_evidence,
            "period_resonance_explained": empty_evidence,
            "control_funds_explained": empty_evidence,
            "bubugao_explained": empty_evidence,
            "value_quantify_explained": empty_evidence,
            "customer_stock_explained": empty_evidence
        }

    def _create_empty_demo_more(self) -> Dict[str, Any]:
        """创建空的深度演绎格式"""
        empty_coverage = {"hit": False, "evidence": [], "confidence": 0.0, "evidence_source": "none"}
        empty_depth = {"depth": "无", "effectiveness_score": 0, "analysis": "无数据"}

        return {
            f"{key}": {
                "coverage": empty_coverage,
                "depth_effectiveness": empty_depth
            }
            for key in ["bs_explained", "period_resonance_explained", "control_funds_explained",
                       "bubugao_explained", "value_quantify_explained"]
        }

    def _generate_cache_key(self, result: CallAnalysisResult, processed_text: Optional[Dict]) -> str:
        """生成缓存键

        Args:
            result: 分析结果
            processed_text: 处理文本

        Returns:
            str: 缓存键
        """
        import hashlib

        key_data = f"{result.call_id}|{result.analysis_timestamp}|{hash(str(processed_text))}"
        return hashlib.md5(key_data.encode('utf-8')).hexdigest()[:16]

    def _update_cache(self, key: str, value: Dict[str, Any]) -> None:
        """更新缓存

        Args:
            key: 缓存键
            value: 缓存值
        """
        if not self.enable_cache:
            return

        # 简单的LRU策略
        if len(self._cache) >= self.cache_size:
            # 删除最旧的10%条目
            keys_to_remove = list(self._cache.keys())[:self.cache_size // 10]
            for k in keys_to_remove:
                del self._cache[k]

        self._cache[key] = value

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计

        Returns:
            Dict: 缓存统计信息
        """
        if not self.enable_cache:
            return {"cache_enabled": False}

        total_requests = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_rate = self._cache_stats["hits"] / total_requests if total_requests > 0 else 0

        return {
            "cache_enabled": True,
            "cache_size": len(self._cache),
            "max_size": self.cache_size,
            "hits": self._cache_stats["hits"],
            "misses": self._cache_stats["misses"],
            "hit_rate": round(hit_rate, 3),
            "total_requests": total_requests
        }

    def clear_cache(self) -> None:
        """清空缓存"""
        if self.enable_cache:
            self._cache.clear()
            self._cache_stats = {"hits": 0, "misses": 0}
            logger.info("UI adapter cache cleared")

    def get_conversion_stats(self) -> Dict[str, Any]:
        """获取转换统计信息

        Returns:
            Dict: 统计信息
        """
        cache_stats = self.get_cache_stats()
        evidence_stats = self.evidence_enhancer.get_cache_stats()

        return {
            "adapter_cache": cache_stats,
            "evidence_enhancer_cache": evidence_stats,
            "adapter_version": "1.0.0"
        }