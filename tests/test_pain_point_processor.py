"""痛点量化处理器测试用例"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock

from src.models.schemas import (
    CallInput, 
    AnalysisConfig, 
    PainPointType, 
    PainPointQuantificationModel
)
from src.processors.pain_point_processor import PainPointProcessor
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
    vector_engine.search_similar = AsyncMock(return_value={
        'document': '亏损严重的投资案例',
        'similarity': 0.7,
        'category': 'pain_point'
    })
    
    rule_engine.detect = AsyncMock(return_value={
        'hit': True, 
        'confidence': 0.8, 
        'evidence': '亏了30万'
    })
    
    llm_engine.generate = AsyncMock(return_value='''
    {
        "detected": true,
        "confidence": 0.9,
        "evidence_segments": ["亏了30万"],
        "reasoning": "客户明确提到了严重的投资损失"
    }
    ''')
    
    return vector_engine, rule_engine, llm_engine


@pytest.fixture(scope="module")
def pain_point_processor(mock_engines):
    """痛点处理器实例"""
    vector_engine, rule_engine, llm_engine = mock_engines
    return PainPointProcessor(vector_engine, rule_engine, llm_engine)


@pytest.mark.asyncio
async def test_pain_point_detection(pain_point_processor):
    """测试痛点检测"""
    
    # 准备测试数据
    processed_text = {
        'content_analysis': {
            'customer_content': [
                "我去年炒股亏了30万，现在都不敢告诉家人。真的很后悔没有及时止损。"
            ]
        }
    }
    config = AnalysisConfig()
    
    # 执行痛点分析
    result = await pain_point_processor.analyze(processed_text, config)
    
    # 验证结果
    assert isinstance(result, PainPointQuantificationModel)
    
    # 验证亏损痛点
    loss_pain = result.loss_pain
    assert loss_pain.detected is True
    assert loss_pain.pain_type == PainPointType.LOSS
    assert loss_pain.confidence > 0.7
    assert loss_pain.quantification.amount == 30.0
    assert len(loss_pain.evidence_segments) > 0
    
    # 验证总体痛点评分
    assert result.total_pain_score > 0
    assert result.dominant_pain_type == PainPointType.LOSS


@pytest.mark.asyncio
async def test_multiple_pain_points(pain_point_processor):
    """测试多重痛点检测"""
    
    # 准备测试数据
    processed_text = {
        'content_analysis': {
            'customer_content': [
                "我去年炒股亏了30万，错过了腾讯的大涨，现在追高买了很多股票，真是太难了。"
            ]
        }
    }
    config = AnalysisConfig()
    
    # 执行痛点分析
    result = await pain_point_processor.analyze(processed_text, config)
    
    # 验证结果
    assert isinstance(result, PainPointQuantificationModel)
    
    # 验证亏损痛点
    loss_pain = result.loss_pain
    assert loss_pain.detected is True
    assert loss_pain.pain_type == PainPointType.LOSS
    
    # 验证踏空痛点
    miss_opportunity_pain = result.miss_opportunity_pain
    assert miss_opportunity_pain.detected is True
    assert miss_opportunity_pain.pain_type == PainPointType.MISS_OPPORTUNITY
    
    # 验证追高痛点
    chase_high_pain = result.chase_high_pain
    assert chase_high_pain.detected is True
    assert chase_high_pain.pain_type == PainPointType.CHASE_HIGH


@pytest.mark.asyncio
async def test_no_pain_points(pain_point_processor):
    """测试无痛点场景"""
    
    # 准备测试数据
    processed_text = {
        'content_analysis': {
            'customer_content': [
                "我最近的投资还不错，基本保持稳定。"
            ]
        }
    }
    config = AnalysisConfig()
    
    # 执行痛点分析
    result = await pain_point_processor.analyze(processed_text, config)
    
    # 验证结果
    assert isinstance(result, PainPointQuantificationModel)
    
    # 验证所有痛点都未检测到
    assert not result.loss_pain.detected
    assert not result.miss_opportunity_pain.detected
    assert not result.chase_high_pain.detected
    assert not result.panic_sell_pain.detected
    
    # 验证总体痛点评分为0
    assert result.total_pain_score == 0.0
    assert result.dominant_pain_type is None


@pytest.mark.asyncio
async def test_quantification_reliability(pain_point_processor):
    """测试量化可信度"""
    
    # 准备测试数据
    processed_text = {
        'content_analysis': {
            'customer_content': [
                "我去年炒股亏了30万，错过了腾讯的大涨，现在追高买了很多股票，真是太难了。"
            ]
        }
    }
    config = AnalysisConfig()
    
    # 执行痛点分析
    result = await pain_point_processor.analyze(processed_text, config)
    
    # 验证量化可信度
    assert result.quantification_reliability > 0.5
    assert result.quantification_reliability <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
