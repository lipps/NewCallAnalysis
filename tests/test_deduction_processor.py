"""DeductionProcessor 单元与集成测试"""

import pytest
from unittest.mock import Mock, AsyncMock

from src.processors.deduction_processor import DeductionProcessor
from src.models.schemas import AnalysisConfig


def _build_processor():
    vector_engine = Mock()
    rule_engine = Mock()
    llm_engine = Mock()
    return DeductionProcessor(vector_engine, rule_engine, llm_engine), vector_engine, rule_engine, llm_engine


def test_llm_confidence_percentage_parsing():
    processor, *_ = _build_processor()

    response = "判定结果：是\n置信度：85%\n证据片段：B点代表买入信号"
    parsed = processor._parse_llm_response(response, 'bs_explained')

    assert parsed['hit'] is True
    assert 0.84 <= parsed['confidence'] <= 0.86


def test_combine_results_rule_fallback_and_truncation():
    processor, *_ = _build_processor()

    long_evidence = 'x' * 500
    res = processor._combine_results(
        rule_result={'hit': True, 'confidence': 0.3, 'evidence': long_evidence},
        vector_result=None,
        llm_result=None,
        threshold=0.6,
        max_evidence_length=120,
        rule_floor=0.6,
        vector_enabled=False,
        llm_enabled=False,
    )

    assert res['hit'] is True
    assert res['confidence'] >= 0.6
    assert len(res['evidence']) == 120


def test_combine_results_with_vector_evidence():
    processor, *_ = _build_processor()

    vec_doc = '向量文档' * 100  # 长文档
    res = processor._combine_results(
        rule_result={'hit': False, 'confidence': 0.0, 'evidence': ''},
        vector_result={'similarity': 0.9, 'document': vec_doc},
        llm_result=None,
        threshold=0.7,
        max_evidence_length=80,
        rule_floor=0.6,
        vector_enabled=True,
        llm_enabled=False,
    )

    assert res['hit'] is True
    assert 0.89 <= res['confidence'] <= 0.91
    assert len(res['evidence']) == 80


@pytest.mark.asyncio
async def test_analyze_rule_fallback_integration():
    processor, vector_engine, rule_engine, llm_engine = _build_processor()

    async def fake_detect(category: str, point: str, text: str, min_confidence: float = 0.3):
        if category == 'deduction' and point == 'bs_explained':
            return {'hit': True, 'confidence': 0.25, 'evidence': 'B点代表最佳买入时机'}
        return {'hit': False, 'confidence': 0.0, 'evidence': ''}

    rule_engine.detect = AsyncMock(side_effect=fake_detect)
    vector_engine.search_similar = AsyncMock(return_value=None)
    llm_engine.generate = AsyncMock(return_value='')

    processed_text = {
        'content_analysis': {
            'sales_content': ['我们的B点代表买入信号，S点代表卖出信号。']
        },
        'cleaned_text': '我们的B点代表买入信号，S点代表卖出信号。'
    }

    config = AnalysisConfig(
        enable_vector_search=False,
        enable_llm_validation=False,
        confidence_threshold=0.6,
        max_evidence_length=100,
    )

    result = await processor.analyze(processed_text, config)

    assert result.bs_explained.hit is True
    assert result.bs_explained.confidence >= 0.6
    # 非命中项
    assert result.period_resonance_explained.hit is False
    assert result.control_funds_explained.hit is False
    assert result.bubugao_explained.hit is False
    assert result.value_quantify_explained.hit is False
    assert result.customer_stock_explained.hit is False

