"""标准动作执行情况处理器"""

from typing import Dict, List, Any, Optional
from ..models.schemas import ActionsModel, ActionExecution, AnalysisConfig, EvidenceHit
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ActionProcessor:
    """标准动作执行情况处理器"""
    
    def __init__(self):
        pass
        
    async def analyze(self, 
                     icebreak_result,  # IcebreakModel or Dict
                     deduction_result,  # DeductionModel or Dict
                     config: AnalysisConfig) -> ActionsModel:
        """分析标准动作执行情况"""
        
        try:
            logger.info("开始标准动作执行情况分析")
            
            # 从破冰结果中提取动作执行情况
            icebreak_actions = self._extract_icebreak_actions(icebreak_result)
            
            # 从演绎结果中提取动作执行情况
            deduction_actions = self._extract_deduction_actions(deduction_result)
            
            # 合并动作执行情况
            all_actions = {**icebreak_actions, **deduction_actions}
            
            # 构建动作模型
            actions_result = ActionsModel(**all_actions)
            
            # 计算执行统计
            executed_count = sum(1 for action in all_actions.values() if action.executed)
            total_count = len(all_actions)
            
            logger.info(f"标准动作执行情况分析完成，执行率: {executed_count}/{total_count} ({executed_count/total_count*100:.1f}%)")
            
            return actions_result
            
        except Exception as e:
            logger.error(f"标准动作执行情况分析失败: {e}")
            raise
    
    def _extract_icebreak_actions(self, icebreak_result) -> Dict[str, ActionExecution]:
        """从破冰结果中提取动作执行情况"""
        
        actions = {}
        
        # 破冰动作映射
        icebreak_mapping = {
            'professional_identity': 'professional_identity',
            'value_help': 'value_help',
            'time_notice': 'time_notice',
            'company_background': 'company_background',
            'free_teach': 'free_teach'
        }
        
        for result_key, action_key in icebreak_mapping.items():
            # 处理Pydantic模型或字典
            if hasattr(icebreak_result, result_key):
                evidence_hit = getattr(icebreak_result, result_key)
            elif isinstance(icebreak_result, dict) and result_key in icebreak_result:
                evidence_hit = icebreak_result[result_key]
            else:
                # 创建默认值
                actions[action_key] = ActionExecution(
                    executed=False,
                    confidence=0.0,
                    evidence_count=0,
                    evidence_list=[]
                )
                continue
                
            if hasattr(evidence_hit, 'hit'):
                # 处理EvidenceHit对象
                executed = evidence_hit.hit
                evidence = getattr(evidence_hit, 'evidence', '')
                confidence = getattr(evidence_hit, 'confidence', 0.0)
                count = 1 if executed else 0
                evidence_list = [evidence] if evidence else []
            elif isinstance(evidence_hit, dict):
                # 处理字典格式
                executed = evidence_hit.get('hit', False)
                evidence = evidence_hit.get('evidence', '')
                confidence = evidence_hit.get('confidence', 0.0)
                count = 1 if executed else 0
                evidence_list = [evidence] if evidence else []
            else:
                # 默认处理
                executed = False
                confidence = 0.0
                count = 0
                evidence_list = []
            
            actions[action_key] = ActionExecution(
                executed=executed,
                confidence=confidence,
                evidence_count=count,
                evidence_list=evidence_list
            )
        
        return actions
    
    def _extract_deduction_actions(self, deduction_result) -> Dict[str, ActionExecution]:
        """从演绎结果中提取动作执行情况"""
        
        actions = {}
        
        # 演绎动作映射
        deduction_mapping = {
            'bs_explained': 'bs_explained',
            'period_resonance_explained': 'period_resonance_explained',
            'control_funds_explained': 'control_funds_explained',
            'bubugao_explained': 'bubugao_explained',
            'value_quantify_explained': 'value_quantify_explained',
            'customer_stock_explained': 'customer_stock_explained'
        }
        
        for result_key, action_key in deduction_mapping.items():
            # 处理Pydantic模型或字典
            if hasattr(deduction_result, result_key):
                evidence_hit = getattr(deduction_result, result_key)
            elif isinstance(deduction_result, dict) and result_key in deduction_result:
                evidence_hit = deduction_result[result_key]
            else:
                # 创建默认值
                actions[action_key] = ActionExecution(
                    executed=False,
                    confidence=0.0,
                    evidence_count=0,
                    evidence_list=[]
                )
                continue
                
            if hasattr(evidence_hit, 'hit'):
                # 处理EvidenceHit对象
                executed = evidence_hit.hit
                evidence = getattr(evidence_hit, 'evidence', '')
                confidence = getattr(evidence_hit, 'confidence', 0.0)
                count = 1 if executed else 0
                evidence_list = [evidence] if evidence else []
            elif isinstance(evidence_hit, dict):
                # 处理字典格式
                executed = evidence_hit.get('hit', False)
                evidence = evidence_hit.get('evidence', '')
                confidence = evidence_hit.get('confidence', 0.0)
                count = 1 if executed else 0
                evidence_list = [evidence] if evidence else []
            else:
                # 默认处理
                executed = False
                confidence = 0.0
                count = 0
                evidence_list = []
            
            actions[action_key] = ActionExecution(
                executed=executed,
                confidence=confidence,
                evidence_count=count,
                evidence_list=evidence_list
            )
        
        return actions
    
    def _estimate_action_count(self, evidence: str, action_type: str) -> int:
        """估算动作执行次数"""
        
        try:
            # 根据不同类型的动作估算次数
            if action_type in ['bs_explained']:
                # BS点讲解：统计BS相关关键词出现次数
                bs_keywords = ['B点', 'S点', '买点', '卖点', '买卖点']
                count = sum(evidence.count(keyword) for keyword in bs_keywords)
                return max(1, count)  # 至少为1
                
            elif action_type == 'bubugao_explained':
                # 步步高讲解：统计相关关键词
                bubugao_keywords = ['步步高', 'VIP', '专属']
                count = sum(evidence.count(keyword) for keyword in bubugao_keywords)
                return max(1, count)
                
            elif action_type == 'control_funds_explained':
                # 控盘资金讲解：统计相关关键词
                funds_keywords = ['主力', '控盘', '资金', '筹码']
                count = sum(evidence.count(keyword) for keyword in funds_keywords)
                return max(1, count)
                
            elif action_type == 'period_resonance_explained':
                # 周期共振讲解：统计相关关键词
                period_keywords = ['周期', '共振', '日线', '周线', '月线']
                count = sum(evidence.count(keyword) for keyword in period_keywords)
                return max(1, count)
                
            elif action_type == 'value_quantify_explained':
                # 价值量化演绎：统计数据和案例关键词
                value_keywords = ['收益', '%', '成功', '实盘', '案例']
                count = sum(evidence.count(keyword) for keyword in value_keywords)
                return max(1, count)
                
            elif action_type == 'customer_stock_explained':
                # 客户股票讲解：统计股票名称或分析关键词
                stock_keywords = ['股票', '分析', '您的', '你的', '这只']
                count = sum(evidence.count(keyword) for keyword in stock_keywords)
                return max(1, count)
            
            else:
                # 其他类型默认为1次
                return 1
                
        except Exception as e:
            logger.error(f"估算动作次数失败: {e}")
            return 1  # 默认为1次