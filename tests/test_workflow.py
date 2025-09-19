"""工作流测试用例"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
import json
import time

from src.models.schemas import CallInput, AnalysisConfig, CallAnalysisResult
from src.workflows.simplified_workflow import SimpleCallAnalysisWorkflow
from src.engines.vector_engine import VectorSearchEngine
from src.engines.rule_engine import RuleEngine
from src.engines.llm_engine import LLMEngine


@pytest.fixture(scope="module")
def mock_engines():
    """模拟引擎"""
    vector_engine = Mock(spec=VectorSearchEngine)
    rule_engine = Mock(spec=RuleEngine)
    llm_engine = Mock(spec=LLMEngine)
    
    # 配置异步mock
    vector_engine.search_similar = AsyncMock(return_value=None)
    rule_engine.detect = AsyncMock(return_value={
        'hit': True, 'confidence': 0.8, 'evidence': '测试证据'
    })
    llm_engine.generate = AsyncMock(return_value='判定结果：是\n置信度：0.9\n证据片段：我是益盟操盘手专员')
    
    return vector_engine, rule_engine, llm_engine


@pytest.fixture(scope="module")
def workflow(mock_engines):
    """工作流实例"""
    vector_engine, rule_engine, llm_engine = mock_engines
    return SimpleCallAnalysisWorkflow(vector_engine, rule_engine, llm_engine)


@pytest.fixture(scope="module")
def sample_call_input():
    """示例通话输入"""
    return CallInput(
        call_id="test_call_001",
        transcript="""销售：您好，我是益盟操盘手的专员小王。
客户：你好。
销售：我们是腾讯投资的上市公司，耽误您两分钟时间，免费给您讲解一下我们的买卖点功能。
客户：好的，你说。
销售：我们的B点代表买入信号，S点代表卖出信号。根据历史数据，能提升20%收益率。
客户：这个功能听起来不错。""",
        customer_id="customer_001",
        sales_id="sales_001"
    )


class TestCallAnalysisWorkflow:
    """通话分析工作流测试"""
    
    @pytest.mark.asyncio
    async def test_single_call_analysis(self, workflow, sample_call_input):
        """测试单个通话分析"""
        config = AnalysisConfig()
        
        result = await workflow.execute(sample_call_input, config)
        
        # 验证结果
        assert isinstance(result, CallAnalysisResult)
        assert result.call_id == sample_call_input.call_id
        assert result.customer_id == sample_call_input.customer_id
        assert result.sales_id == sample_call_input.sales_id
        
        # 验证各模块结果存在
        assert result.icebreak is not None
        assert result.演绎 is not None
        assert result.process is not None
        assert result.customer is not None
        assert result.actions is not None
    
    @pytest.mark.asyncio
    async def test_batch_analysis(self, workflow, sample_call_input):
        """测试批量分析"""
        # 创建多个输入
        inputs = []
        for i in range(3):
            call_input = CallInput(
                call_id=f"test_call_{i:03d}",
                transcript=sample_call_input.transcript,
                customer_id=f"customer_{i:03d}",
                sales_id=f"sales_{i:03d}"
            )
            inputs.append(call_input)
        
        config = AnalysisConfig()
        results = await workflow.execute_batch(inputs, config, max_concurrency=2)
        
        # 验证结果
        assert len(results) == 3
        for i, result in enumerate(results):
            assert isinstance(result, CallAnalysisResult)
            assert result.call_id == f"test_call_{i:03d}"
    
    @pytest.mark.asyncio
    async def test_workflow_error_handling(self, mock_engines):
        """测试工作流错误处理"""
        vector_engine, rule_engine, llm_engine = mock_engines
        
        # 配置LLM引擎抛出异常
        llm_engine.generate = AsyncMock(side_effect=Exception("LLM服务不可用"))
        
        workflow = SimpleCallAnalysisWorkflow(vector_engine, rule_engine, llm_engine)
        
        call_input = CallInput(
            call_id="error_test",
            transcript="测试文本"
        )
        
        # 应该能处理错误并返回结果（即使某些模块失败）
        result = await workflow.execute(call_input)
        assert isinstance(result, CallAnalysisResult)
        assert result.call_id == "error_test"


class TestQualityMetrics:
    """质量指标测试"""
    
    def test_icebreak_score_calculation(self):
        """测试破冰得分计算"""
        from src.api.main import _calculate_icebreak_score
        from src.models.schemas import IcebreakModel, EvidenceHit
        
        # 创建测试数据
        icebreak_data = IcebreakModel(
            professional_identity=EvidenceHit(hit=True, evidence="我是专员"),
            value_help=EvidenceHit(hit=True, evidence="帮助您"),
            time_notice=EvidenceHit(hit=False, evidence=""),
            company_background=EvidenceHit(hit=True, evidence="腾讯投资"),
            free_teach=EvidenceHit(hit=False, evidence="")
        )
        
        score = _calculate_icebreak_score(icebreak_data)
        
        # 3/5 = 60分
        assert score == 60.0
    
    def test_completion_rate_calculation(self):
        """测试完成度计算"""
        from src.api.main import _calculate_completion_rate
        from src.models.schemas import ActionsModel, ActionExecution
        
        # 创建测试数据
        actions_data = ActionsModel(
            professional_identity=ActionExecution(executed=True, count=1),
            value_help=ActionExecution(executed=True, count=1),
            time_notice=ActionExecution(executed=False, count=0),
            company_background=ActionExecution(executed=False, count=0),
            free_teach=ActionExecution(executed=False, count=0),
            bs_explained=ActionExecution(executed=True, count=2),
            period_resonance_explained=ActionExecution(executed=False, count=0),
            control_funds_explained=ActionExecution(executed=False, count=0),
            bubugao_explained=ActionExecution(executed=False, count=0),
            value_quantify_explained=ActionExecution(executed=True, count=1),
            customer_stock_explained=ActionExecution(executed=False, count=0)
        )
        
        completion_rate = _calculate_completion_rate(actions_data)
        
        # 4/11 ≈ 0.36
        assert abs(completion_rate - 4/11) < 0.01


class TestPerformance:
    """性能测试"""
    
    @pytest.mark.asyncio
    async def test_concurrent_analysis(self, workflow, sample_call_input):
        """测试并发分析性能"""
        # 创建多个输入
        inputs = []
        for i in range(5):
            call_input = CallInput(
                call_id=f"perf_test_{i}",
                transcript=sample_call_input.transcript
            )
            inputs.append(call_input)
        
        # 测试并发执行时间
        start_time = time.time()
        
        tasks = [workflow.execute(call_input) for call_input in inputs]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 验证结果
        assert len(results) == 5
        for result in results:
            assert isinstance(result, CallAnalysisResult)
        
        # 性能验证（并发执行应该比串行快）
        print(f"并发执行5个分析耗时: {execution_time:.2f}秒")
        
        # 每个分析不应超过10秒
        assert execution_time < 50  # 允许一定的误差


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
