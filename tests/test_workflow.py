"""工作流测试用例"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
import json

from src.models.schemas import CallInput, AnalysisConfig, CallAnalysisResult
from src.workflows.call_analysis_workflow import CallAnalysisWorkflow
from src.engines.vector_engine import VectorSearchEngine
from src.engines.rule_engine import RuleEngine
from src.engines.llm_engine import LLMEngine


class TestCallAnalysisWorkflow:
    """通话分析工作流测试"""
    
    @pytest.fixture
    def mock_engines(self):
        """模拟引擎"""
        vector_engine = Mock(spec=VectorSearchEngine)
        rule_engine = Mock(spec=RuleEngine)
        llm_engine = Mock(spec=LLMEngine)
        
        # 配置异步mock
        vector_engine.search_similar = AsyncMock(return_value=None)
        rule_engine.detect = AsyncMock(return_value={
            'hit': True, 'confidence': 0.8, 'evidence': '测试证据'
        })
        llm_engine.generate = AsyncMock(return_value='判定结果：是\\n置信度：0.9\\n证据片段：我是益盟操盘手专员')
        
        return vector_engine, rule_engine, llm_engine
    
    @pytest.fixture
    def workflow(self, mock_engines):
        """工作流实例"""
        vector_engine, rule_engine, llm_engine = mock_engines
        return CallAnalysisWorkflow(vector_engine, rule_engine, llm_engine)
    
    @pytest.fixture
    def sample_call_input(self):
        """示例通话输入"""
        return CallInput(
            call_id="test_call_001",
            transcript=\"\"\"销售：您好，我是益盟操盘手的专员小王。\n客户：你好。\n销售：我们是腾讯投资的上市公司，耽误您两分钟时间，免费给您讲解一下我们的买卖点功能。\n客户：好的，你说。\n销售：我们的B点代表买入信号，S点代表卖出信号。根据历史数据，能提升20%收益率。\n客户：这个功能听起来不错。\"\"\",\n            customer_id=\"customer_001\",\n            sales_id=\"sales_001\"\n        )\n    \n    @pytest.mark.asyncio\n    async def test_single_call_analysis(self, workflow, sample_call_input):\n        \"\"\"测试单个通话分析\"\"\"\n        config = AnalysisConfig()\n        \n        result = await workflow.execute(sample_call_input, config)\n        \n        # 验证结果\n        assert isinstance(result, CallAnalysisResult)\n        assert result.call_id == sample_call_input.call_id\n        assert result.customer_id == sample_call_input.customer_id\n        assert result.sales_id == sample_call_input.sales_id\n        \n        # 验证各模块结果存在\n        assert result.icebreak is not None\n        assert result.演绎 is not None\n        assert result.process is not None\n        assert result.customer is not None\n        assert result.actions is not None\n    \n    @pytest.mark.asyncio\n    async def test_batch_analysis(self, workflow, sample_call_input):\n        \"\"\"测试批量分析\"\"\"\n        # 创建多个输入\n        inputs = []\n        for i in range(3):\n            call_input = CallInput(\n                call_id=f\"test_call_{i:03d}\",\n                transcript=sample_call_input.transcript,\n                customer_id=f\"customer_{i:03d}\",\n                sales_id=f\"sales_{i:03d}\"\n            )\n            inputs.append(call_input)\n        \n        config = AnalysisConfig()\n        results = await workflow.execute_batch(inputs, config, max_concurrency=2)\n        \n        # 验证结果\n        assert len(results) == 3\n        for i, result in enumerate(results):\n            assert isinstance(result, CallAnalysisResult)\n            assert result.call_id == f\"test_call_{i:03d}\"\n    \n    @pytest.mark.asyncio\n    async def test_workflow_error_handling(self, mock_engines):\n        \"\"\"测试工作流错误处理\"\"\"\n        vector_engine, rule_engine, llm_engine = mock_engines\n        \n        # 配置LLM引擎抛出异常\n        llm_engine.generate = AsyncMock(side_effect=Exception(\"LLM服务不可用\"))\n        \n        workflow = CallAnalysisWorkflow(vector_engine, rule_engine, llm_engine)\n        \n        call_input = CallInput(\n            call_id=\"error_test\",\n            transcript=\"测试文本\"\n        )\n        \n        # 应该能处理错误并返回结果（即使某些模块失败）\n        result = await workflow.execute(call_input)\n        assert isinstance(result, CallAnalysisResult)\n        assert result.call_id == \"error_test\"\n\n\nclass TestQualityMetrics:\n    \"\"\"质量指标测试\"\"\"\n    \n    def test_icebreak_score_calculation(self):\n        \"\"\"测试破冰得分计算\"\"\"\n        from src.api.main import _calculate_icebreak_score\n        from src.models.schemas import IcebreakModel, EvidenceHit\n        \n        # 创建测试数据\n        icebreak_data = IcebreakModel(\n            professional_identity=EvidenceHit(hit=True, evidence=\"我是专员\"),\n            value_help=EvidenceHit(hit=True, evidence=\"帮助您\"),\n            time_notice=EvidenceHit(hit=False, evidence=\"\"),\n            company_background=EvidenceHit(hit=True, evidence=\"腾讯投资\"),\n            free_teach=EvidenceHit(hit=False, evidence=\"\")\n        )\n        \n        score = _calculate_icebreak_score(icebreak_data)\n        \n        # 3/5 = 60分\n        assert score == 60.0\n    \n    def test_completion_rate_calculation(self):\n        \"\"\"测试完成度计算\"\"\"\n        from src.api.main import _calculate_completion_rate\n        from src.models.schemas import ActionsModel, ActionExecution\n        \n        # 创建测试数据\n        actions_data = ActionsModel(\n            professional_identity=ActionExecution(executed=True, count=1),\n            value_help=ActionExecution(executed=True, count=1),\n            time_notice=ActionExecution(executed=False, count=0),\n            company_background=ActionExecution(executed=False, count=0),\n            free_teach=ActionExecution(executed=False, count=0),\n            bs_explained=ActionExecution(executed=True, count=2),\n            period_resonance_explained=ActionExecution(executed=False, count=0),\n            control_funds_explained=ActionExecution(executed=False, count=0),\n            bubugao_explained=ActionExecution(executed=False, count=0),\n            value_quantify_explained=ActionExecution(executed=True, count=1),\n            customer_stock_explained=ActionExecution(executed=False, count=0)\n        )\n        \n        completion_rate = _calculate_completion_rate(actions_data)\n        \n        # 4/11 ≈ 0.36\n        assert abs(completion_rate - 4/11) < 0.01\n\n\nclass TestPerformance:\n    \"\"\"性能测试\"\"\"\n    \n    @pytest.mark.asyncio\n    async def test_concurrent_analysis(self, workflow, sample_call_input):\n        \"\"\"测试并发分析性能\"\"\"\n        import time\n        \n        # 创建多个输入\n        inputs = []\n        for i in range(5):\n            call_input = CallInput(\n                call_id=f\"perf_test_{i}\",\n                transcript=sample_call_input.transcript\n            )\n            inputs.append(call_input)\n        \n        # 测试并发执行时间\n        start_time = time.time()\n        \n        tasks = [workflow.execute(call_input) for call_input in inputs]\n        results = await asyncio.gather(*tasks)\n        \n        end_time = time.time()\n        execution_time = end_time - start_time\n        \n        # 验证结果\n        assert len(results) == 5\n        for result in results:\n            assert isinstance(result, CallAnalysisResult)\n        \n        # 性能验证（并发执行应该比串行快）\n        logger.info(f\"并发执行5个分析耗时: {execution_time:.2f}秒\")\n        \n        # 每个分析不应超过10秒\n        assert execution_time < 50  # 允许一定的误差\n\n\nif __name__ == \"__main__\":\n    pytest.main([__file__, \"-v\"])"