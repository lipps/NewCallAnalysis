"""LangGraph工作流引擎 - 通话分析工作流"""

from typing import Dict, Any, List, Optional, Annotated
import asyncio
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel
import uuid
from operator import add

from ..models.schemas import CallInput, CallAnalysisResult, AnalysisConfig
from ..processors.text_processor import TextProcessor
from ..processors.icebreak_processor import IcebreakProcessor
from ..processors.deduction_processor import DeductionProcessor
from ..processors.process_processor import ProcessProcessor
from ..processors.customer_processor import CustomerProcessor
from ..processors.action_processor import ActionProcessor
from ..processors.customer_probing_processor import CustomerProbingProcessor
from ..engines.vector_engine import VectorSearchEngine
from ..engines.rule_engine import RuleEngine
from ..engines.llm_engine import LLMEngine
from ..utils.logger import get_logger

logger = get_logger(__name__)


class WorkflowState(BaseModel):
    """工作流状态"""
    call_input: CallInput
    config: AnalysisConfig
    
    # 处理结果
    processed_text: Optional[Dict[str, Any]] = None
    icebreak_result: Optional[Dict[str, Any]] = None
    deduction_result: Optional[Dict[str, Any]] = None
    process_result: Optional[Dict[str, Any]] = None
    customer_result: Optional[Dict[str, Any]] = None
    action_result: Optional[Dict[str, Any]] = None
    customer_probing_result: Optional[Dict[str, Any]] = None
    
    # 最终结果
    final_result: Optional[CallAnalysisResult] = None
    
    # 执行状态 - 使用 Annotated 来支持并发更新
    errors: Annotated[List[str], add] = []
    warnings: Annotated[List[str], add] = []
    execution_time: Dict[str, float] = {}


class CallAnalysisWorkflow:
    """通话分析工作流"""
    
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
        
        # 创建工作流图
        self.workflow = self._create_workflow()
        
    def _create_workflow(self) -> StateGraph:
        """创建工作流图"""
        # 使用字典类型状态，避免 Pydantic 模型的复杂性
        workflow = StateGraph(dict)
        
        # 添加节点
        workflow.add_node("text_processing", self._text_processing_node)
        workflow.add_node("icebreak_analysis", self._icebreak_analysis_node)
        workflow.add_node("deduction_analysis", self._deduction_analysis_node)
        workflow.add_node("process_analysis", self._process_analysis_node)
        workflow.add_node("customer_analysis", self._customer_analysis_node)
        workflow.add_node("customer_probing_analysis", self._customer_probing_analysis_node)
        workflow.add_node("action_analysis", self._action_analysis_node)
        workflow.add_node("result_aggregation", self._result_aggregation_node)
        
        # 设置入口点
        workflow.set_entry_point("text_processing")
        
        # 串行执行避免并发冲突
        workflow.add_edge("text_processing", "icebreak_analysis")
        workflow.add_edge("icebreak_analysis", "deduction_analysis")
        workflow.add_edge("deduction_analysis", "process_analysis")
        workflow.add_edge("process_analysis", "customer_analysis")
        workflow.add_edge("customer_analysis", "customer_probing_analysis")
        workflow.add_edge("customer_probing_analysis", "action_analysis")
        workflow.add_edge("action_analysis", "result_aggregation")
        
        # 结束
        workflow.add_edge("result_aggregation", END)
        
        return workflow
    
    async def _text_processing_node(self, state: dict) -> dict:
        """文本预处理节点"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            call_input = state["call_input"]
            logger.info(f"开始文本预处理: {call_input.call_id}")
            
            processed_text = await self.text_processor.process(
                call_input.transcript
            )
            
            logger.info(f"文本预处理完成: {call_input.call_id}")
            
            # 返回更新的状态
            return {
                **state,
                "processed_text": processed_text,
                "execution_time": {
                    **state.get("execution_time", {}),
                    "text_processing": asyncio.get_event_loop().time() - start_time
                }
            }
            
        except Exception as e:
            logger.error(f"文本预处理失败: {e}")
            return {
                **state,
                "errors": state.get("errors", []) + [f"文本预处理失败: {str(e)}"],
                "execution_time": {
                    **state.get("execution_time", {}),
                    "text_processing": asyncio.get_event_loop().time() - start_time
                }
            }
    
    async def _icebreak_analysis_node(self, state: dict) -> dict:
        """破冰分析节点"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if state.get("processed_text") is None:
                raise ValueError("需要先完成文本预处理")
                
            call_input = state["call_input"]
            config = state["config"]
            logger.info(f"开始破冰分析: {call_input.call_id}")
            
            icebreak_result = await self.icebreak_processor.analyze(
                state["processed_text"],
                config
            )
            
            # 确保结果是字典格式
            if hasattr(icebreak_result, 'dict'):
                icebreak_result = icebreak_result.dict()
            
            logger.info(f"破冰分析完成: {call_input.call_id}")
            
            return {
                **state,
                "icebreak_result": icebreak_result,
                "execution_time": {
                    **state.get("execution_time", {}),
                    "icebreak_analysis": asyncio.get_event_loop().time() - start_time
                }
            }
            
        except Exception as e:
            logger.error(f"破冰分析失败: {e}")
            return {
                **state,
                "errors": state.get("errors", []) + [f"破冰分析失败: {str(e)}"],
                "execution_time": {
                    **state.get("execution_time", {}),
                    "icebreak_analysis": asyncio.get_event_loop().time() - start_time
                }
            }
    
    async def _deduction_analysis_node(self, state: dict) -> dict:
        """功能演绎分析节点"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if state.get("processed_text") is None:
                raise ValueError("需要先完成文本预处理")
                
            call_input = state["call_input"]
            config = state["config"]
            logger.info(f"开始功能演绎分析: {call_input.call_id}")
            
            deduction_result = await self.deduction_processor.analyze(
                state["processed_text"],
                config
            )
            
            # 确保结果是字典格式
            if hasattr(deduction_result, 'dict'):
                deduction_result = deduction_result.dict()
            
            logger.info(f"功能演绎分析完成: {call_input.call_id}")
            
            return {
                **state,
                "deduction_result": deduction_result,
                "execution_time": {
                    **state.get("execution_time", {}),
                    "deduction_analysis": asyncio.get_event_loop().time() - start_time
                }
            }
            
        except Exception as e:
            logger.error(f"功能演绎分析失败: {e}")
            return {
                **state,
                "errors": state.get("errors", []) + [f"功能演绎分析失败: {str(e)}"],
                "execution_time": {
                    **state.get("execution_time", {}),
                    "deduction_analysis": asyncio.get_event_loop().time() - start_time
                }
            }
    
    async def _process_analysis_node(self, state: dict) -> dict:
        """过程分析节点"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if state.get("processed_text") is None:
                raise ValueError("需要先完成文本预处理")
                
            call_input = state["call_input"]
            config = state["config"]
            logger.info(f"开始过程分析: {call_input.call_id}")
            
            process_result = await self.process_processor.analyze(
                state["processed_text"],
                config
            )
            
            # 确保结果是字典格式
            if hasattr(process_result, 'dict'):
                process_result = process_result.dict()
            
            logger.info(f"过程分析完成: {call_input.call_id}")
            
            return {
                **state,
                "process_result": process_result,
                "execution_time": {
                    **state.get("execution_time", {}),
                    "process_analysis": asyncio.get_event_loop().time() - start_time
                }
            }
            
        except Exception as e:
            logger.error(f"过程分析失败: {e}")
            return {
                **state,
                "errors": state.get("errors", []) + [f"过程分析失败: {str(e)}"],
                "execution_time": {
                    **state.get("execution_time", {}),
                    "process_analysis": asyncio.get_event_loop().time() - start_time
                }
            }
    
    async def _customer_analysis_node(self, state: dict) -> dict:
        """客户分析节点"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if state.get("processed_text") is None:
                raise ValueError("需要先完成文本预处理")
                
            call_input = state["call_input"]
            config = state["config"]
            logger.info(f"开始客户分析: {call_input.call_id}")
            
            customer_result = await self.customer_processor.analyze(
                state["processed_text"],
                config
            )
            
            # 确保结果是字典格式
            if hasattr(customer_result, 'dict'):
                customer_result = customer_result.dict()
            
            logger.info(f"客户分析完成: {call_input.call_id}")
            
            return {
                **state,
                "customer_result": customer_result,
                "execution_time": {
                    **state.get("execution_time", {}),
                    "customer_analysis": asyncio.get_event_loop().time() - start_time
                }
            }
            
        except Exception as e:
            logger.error(f"客户分析失败: {e}")
            return {
                **state,
                "errors": state.get("errors", []) + [f"客户分析失败: {str(e)}"],
                "execution_time": {
                    **state.get("execution_time", {}),
                    "customer_analysis": asyncio.get_event_loop().time() - start_time
                }
            }

    async def _customer_probing_analysis_node(self, state: dict) -> dict:
        """客户情况考察分析节点"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if state.get("processed_text") is None:
                raise ValueError("需要先完成文本预处理")
                
            call_input = state["call_input"]
            config = state["config"]
            logger.info(f"开始客户情况考察分析: {call_input.call_id}")
            
            customer_probing_result = await self.customer_probing_processor.analyze(
                state["processed_text"],
                config
            )
            
            # 确保结果是字典格式
            if hasattr(customer_probing_result, 'dict'):
                customer_probing_result = customer_probing_result.dict()
            
            logger.info(f"客户情况考察分析完成: {call_input.call_id}")
            
            return {
                **state,
                "customer_probing_result": customer_probing_result,
                "execution_time": {
                    **state.get("execution_time", {}),
                    "customer_probing_analysis": asyncio.get_event_loop().time() - start_time
                }
            }
            
        except Exception as e:
            logger.error(f"客户情况考察分析失败: {e}")
            return {
                **state,
                "errors": state.get("errors", []) + [f"客户情况考察分析失败: {str(e)}"],
                "execution_time": {
                    **state.get("execution_time", {}),
                    "customer_probing_analysis": asyncio.get_event_loop().time() - start_time
                }
            }
    
    async def _action_analysis_node(self, state: dict) -> dict:
        """动作分析节点"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            call_input = state["call_input"]
            config = state["config"]
            logger.info(f"开始动作分析: {call_input.call_id}")
            
            # 检查破冰和演绎分析结果
            warnings = state.get("warnings", [])
            if state.get("icebreak_result") is None or state.get("deduction_result") is None:
                warnings.append("破冰或演绎分析未完成，使用空结果进行动作分析")
                
            action_result = await self.action_processor.analyze(
                state.get("icebreak_result", {}),
                state.get("deduction_result", {}),
                config
            )
            
            # 确保结果是字典格式
            if hasattr(action_result, 'dict'):
                action_result = action_result.dict()
            
            logger.info(f"动作分析完成: {call_input.call_id}")
            
            return {
                **state,
                "action_result": action_result,
                "warnings": warnings,
                "execution_time": {
                    **state.get("execution_time", {}),
                    "action_analysis": asyncio.get_event_loop().time() - start_time
                }
            }
            
        except Exception as e:
            logger.error(f"动作分析失败: {e}")
            return {
                **state,
                "errors": state.get("errors", []) + [f"动作分析失败: {str(e)}"],
                "execution_time": {
                    **state.get("execution_time", {}),
                    "action_analysis": asyncio.get_event_loop().time() - start_time
                }
            }
    
    async def _result_aggregation_node(self, state: dict) -> dict:
        """结果聚合节点"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            call_input = state["call_input"]
            logger.info(f"开始结果聚合: {call_input.call_id}")
            
            # 构建最终结果
            final_result = CallAnalysisResult(
                call_id=call_input.call_id,
                customer_id=call_input.customer_id,
                sales_id=call_input.sales_id,
                call_time=call_input.call_time,
                
                icebreak=state.get("icebreak_result", {}),
                演绎=state.get("deduction_result", {}),
                process=state.get("process_result", {}),
                customer=state.get("customer_result", {}),
                actions=state.get("action_result", {}),
                customer_probing=state.get("customer_probing_result", {}),
                
                analysis_timestamp=datetime.now().isoformat(),
                model_version="1.0",
                confidence_score=self._calculate_confidence(state)
            )
            
            # 计算总执行时间
            total_time = sum(state.get("execution_time", {}).values())
            logger.info(f"结果聚合完成: {call_input.call_id}, 总耗时: {total_time:.2f}秒")
            
            return {
                **state,
                "final_result": final_result,
                "execution_time": {
                    **state.get("execution_time", {}),
                    "result_aggregation": asyncio.get_event_loop().time() - start_time
                }
            }
            
        except Exception as e:
            logger.error(f"结果聚合失败: {e}")
            return {
                **state,
                "errors": state.get("errors", []) + [f"结果聚合失败: {str(e)}"],
                "execution_time": {
                    **state.get("execution_time", {}),
                    "result_aggregation": asyncio.get_event_loop().time() - start_time
                }
            }
    
    def _calculate_confidence(self, state: dict) -> float:
        """计算整体置信度"""
        confidence_scores = []
        
        # 收集各模块的置信度
        icebreak_result = state.get("icebreak_result")
        if icebreak_result:
            # 计算破冰模块平均置信度
            icebreak_confidences = []
            for key, value in icebreak_result.items():
                if isinstance(value, dict) and 'confidence' in value:
                    icebreak_confidences.append(value['confidence'])
            if icebreak_confidences:
                confidence_scores.append(sum(icebreak_confidences) / len(icebreak_confidences))
                
        deduction_result = state.get("deduction_result")
        if deduction_result:
            # 计算演绎模块平均置信度
            deduction_confidences = []
            for key, value in deduction_result.items():
                if isinstance(value, dict) and 'confidence' in value:
                    deduction_confidences.append(value['confidence'])
            if deduction_confidences:
                confidence_scores.append(sum(deduction_confidences) / len(deduction_confidences))
        
        # 返回平均置信度
        return sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
    
    async def execute(self, 
                     call_input: CallInput, 
                     config: Optional[AnalysisConfig] = None) -> CallAnalysisResult:
        """执行工作流"""
        
        if config is None:
            config = AnalysisConfig()
            
        # 创建初始状态
        initial_state = {
            "call_input": call_input,
            "config": config,
            "execution_time": {},
            "errors": [],
            "warnings": []
        }
        
        # 编译并运行工作流
        app = self.workflow.compile(checkpointer=MemorySaver())
        
        try:
            # 执行工作流
            final_state = await app.ainvoke(
                initial_state,
                config={"configurable": {"thread_id": str(uuid.uuid4())}}
            )
            
            if final_state.get("final_result") is None:
                raise ValueError("工作流执行完成但未产生结果")
                
            return final_state["final_result"]
            
        except Exception as e:
            logger.error(f"工作流执行失败: {e}")
            raise
    
    async def execute_batch(self, 
                           inputs: List[CallInput],
                           config: Optional[AnalysisConfig] = None,
                           max_concurrency: int = 5) -> List[CallAnalysisResult]:
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
                error_result = CallAnalysisResult(
                    call_id=inputs[i].call_id,
                    analysis_timestamp=datetime.now().isoformat(),
                    confidence_score=0.0
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)
        
        return processed_results
