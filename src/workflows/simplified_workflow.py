"""简化的工作流实现 - 避免LangGraph并发问题"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from ..models.schemas import CallInput, CallAnalysisResult, AnalysisConfig
from ..processors.text_processor import TextProcessor
from ..processors.icebreak_processor import IcebreakProcessor
from ..processors.deduction_processor import DeductionProcessor
from ..processors.process_processor import ProcessProcessor
from ..processors.customer_processor import CustomerProcessor
from ..processors.action_processor import ActionProcessor
from ..processors.customer_probing_processor import CustomerProbingProcessor
from ..processors.pain_point_processor import PainPointProcessor
from ..engines.vector_engine import VectorSearchEngine
from ..engines.rule_engine import RuleEngine
from ..engines.llm_engine import LLMEngine
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SimpleCallAnalysisWorkflow:
    """简化的通话分析工作流"""
    
    def __init__(self,
                 vector_engine: VectorSearchEngine,
                 rule_engine: RuleEngine,
                 llm_engine: LLMEngine):
        
        self.vector_engine = vector_engine
        self.rule_engine = rule_engine
        self.llm_engine = llm_engine
        
        # 初始化处理器
        self.text_processor = TextProcessor()
        self.icebreak_processor = IcebreakProcessor(vector_engine, rule_engine, llm_engine)
        self.deduction_processor = DeductionProcessor(vector_engine, rule_engine, llm_engine) 
        self.process_processor = ProcessProcessor()
        self.customer_processor = CustomerProcessor(llm_engine)
        self.action_processor = ActionProcessor()
        self.customer_probing_processor = CustomerProbingProcessor(llm_engine)
        self.pain_point_processor = PainPointProcessor(vector_engine, rule_engine, llm_engine)
    
    async def execute(self, 
                     call_input: CallInput, 
                     config: Optional[AnalysisConfig] = None) -> CallAnalysisResult:
        """执行工作流 - 串行处理避免并发问题"""
        
        if config is None:
            config = AnalysisConfig()
        
        execution_times = {}
        errors = []
        
        try:
            # 1. 文本预处理
            start_time = asyncio.get_event_loop().time()
            logger.info(f"开始文本预处理: {call_input.call_id}")
            processed_text = await self.text_processor.process(call_input.transcript)
            execution_times["text_processing"] = asyncio.get_event_loop().time() - start_time
            logger.info(f"文本预处理完成: {call_input.call_id}")
            
            # 2. 破冰分析
            start_time = asyncio.get_event_loop().time()
            logger.info(f"开始破冰分析: {call_input.call_id}")
            icebreak_result = await self.icebreak_processor.analyze(
                processed_text, 
                config
            )
            execution_times["icebreak_analysis"] = asyncio.get_event_loop().time() - start_time
            logger.info(f"破冰分析完成: {call_input.call_id}")
            
            # 3. 功能演绎分析
            start_time = asyncio.get_event_loop().time()
            logger.info(f"开始功能演绎分析: {call_input.call_id}")
            deduction_result = await self.deduction_processor.analyze(
                processed_text,
                config
            )
            execution_times["deduction_analysis"] = asyncio.get_event_loop().time() - start_time
            logger.info(f"功能演绎分析完成: {call_input.call_id}")
            
            # 4. 过程分析
            start_time = asyncio.get_event_loop().time()
            logger.info(f"开始过程分析: {call_input.call_id}")
            process_result = await self.process_processor.analyze(processed_text, config)
            execution_times["process_analysis"] = asyncio.get_event_loop().time() - start_time
            logger.info(f"过程分析完成: {call_input.call_id}")
            
            # 5. 客户分析
            start_time = asyncio.get_event_loop().time()
            logger.info(f"开始客户分析: {call_input.call_id}")
            customer_result = await self.customer_processor.analyze(processed_text, config)
            execution_times["customer_analysis"] = asyncio.get_event_loop().time() - start_time
            logger.info(f"客户分析完成: {call_input.call_id}")
            
            # 6. 动作分析
            start_time = asyncio.get_event_loop().time()
            logger.info(f"开始动作分析: {call_input.call_id}")
            action_result = await self.action_processor.analyze(
                icebreak_result, deduction_result, config
            )
            execution_times["action_analysis"] = asyncio.get_event_loop().time() - start_time
            logger.info(f"动作分析完成: {call_input.call_id}")
            
            # 7. 客户情况考察分析
            start_time = asyncio.get_event_loop().time()
            logger.info(f"开始客户情况考察分析: {call_input.call_id}")
            customer_probing_result = await self.customer_probing_processor.analyze(
                processed_text, config
            )
            execution_times["customer_probing_analysis"] = asyncio.get_event_loop().time() - start_time
            logger.info(f"客户情况考察分析完成: {call_input.call_id}")
            
            # 8. 痛点量化分析
            start_time = asyncio.get_event_loop().time()
            logger.info(f"开始痛点量化分析: {call_input.call_id}")
            pain_point_result = await self.pain_point_processor.analyze(
                processed_text, config
            )
            execution_times["pain_point_analysis"] = asyncio.get_event_loop().time() - start_time
            logger.info(f"痛点量化分析完成: {call_input.call_id}")
            
            # 9. 结果聚合
            confidence_score = self._calculate_confidence(
                icebreak_result, deduction_result
            )
            
            # 创建最终结果
            final_result = CallAnalysisResult(
                call_id=call_input.call_id,
                customer_id=call_input.customer_id or "",
                sales_id=call_input.sales_id or "",
                call_time=call_input.call_time or datetime.now().isoformat(),
                analysis_timestamp=datetime.now().isoformat(),
                
                icebreak=icebreak_result,
                演绎=deduction_result,
                process=process_result,
                customer=customer_result,
                actions=action_result,
                customer_probing=customer_probing_result,
                pain_point_quantification=pain_point_result,
                
                confidence_score=confidence_score,
                model_version="1.0.0"
            )
            
            logger.info(f"工作流执行完成: {call_input.call_id}, 置信度: {confidence_score:.3f}")
            return final_result
            
        except Exception as e:
            logger.error(f"工作流执行失败: {call_input.call_id}, 错误: {e}")
            raise
    
    def _calculate_confidence(self, icebreak_result, deduction_result) -> float:
        """计算置信度"""
        confidence_scores = []
        
        # 收集破冰模块置信度
        for attr_name in ['professional_identity', 'value_help', 'time_notice', 
                         'company_background', 'free_teach']:
            attr = getattr(icebreak_result, attr_name, None)
            if attr and hasattr(attr, 'confidence'):
                confidence_scores.append(attr.confidence)
        
        # 收集演绎模块置信度
        for attr_name in ['bs_explained', 'period_resonance_explained', 
                         'control_funds_explained', 'bubugao_explained',
                         'value_quantify_explained', 'customer_stock_explained']:
            attr = getattr(deduction_result, attr_name, None)
            if attr and hasattr(attr, 'confidence'):
                confidence_scores.append(attr.confidence)
        
        return sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
    
    async def execute_batch(self,
                           inputs: list[CallInput],
                           config: Optional[AnalysisConfig] = None,
                           max_concurrency: int = 3) -> list[CallAnalysisResult]:
        """批量执行工作流"""
        
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def process_single(call_input: CallInput) -> CallAnalysisResult:
            async with semaphore:
                return await self.execute(call_input, config)
        
        # 并发执行所有任务
        tasks = [process_single(call_input) for call_input in inputs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"批量处理第{i}个任务失败: {result}")
                # 创建错误结果
                from ..models.schemas import IcebreakModel, DeductionModel, ProcessModel, CustomerModel, ActionsModel, CustomerProbingModel
                error_result = CallAnalysisResult(
                    call_id=inputs[i].call_id,
                    icebreak=IcebreakModel(),
                    演绎=DeductionModel(),
                    process=ProcessModel(),
                    customer=CustomerModel(),
                    actions=ActionsModel(),
                    customer_probing=CustomerProbingModel(),
                    confidence_score=0.0,
                    model_version="1.0.0"
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)
        
        return processed_results
