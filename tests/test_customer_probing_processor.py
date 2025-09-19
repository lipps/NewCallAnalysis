"""客户情况考察处理器测试"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processors.customer_probing_processor import CustomerProbingProcessor
from src.models.schemas import AnalysisConfig

# Mock LLMEngine for testing
@pytest.fixture
def mock_llm_engine():
    return AsyncMock()

@pytest.mark.asyncio
async def test_customer_probing_processor_positive_case(mock_llm_engine):
    """
    Test case where the transcript contains customer probing.
    """
    # Arrange
    transcript = "销售：您好，为了给您更好的建议，我想了解一下您目前的仓位情况和投资风格？"
    processed_text = {"full_text": transcript}
    config = AnalysisConfig()
    
    mock_llm_engine.generate.return_value = "YES, 客户询问了仓位情况和投资风格。"
    
    processor = CustomerProbingProcessor(mock_llm_engine)
    
    # Act
    result = await processor.analyze(processed_text, config)
    
    # Assert
    assert result['has_customer_probing'] is True
    assert "客户询问了仓位情况和投资风格" in result['customer_probing_details']
    mock_llm_engine.generate.assert_called_once()

@pytest.mark.asyncio
async def test_customer_probing_processor_negative_case(mock_llm_engine):
    """
    Test case where the transcript does not contain customer probing.
    """
    # Arrange
    transcript = "销售：您好，我们这款产品非常好用，功能强大。"
    processed_text = {"full_text": transcript}
    config = AnalysisConfig()
    
    mock_llm_engine.generate.return_value = "NO"
    
    processor = CustomerProbingProcessor(mock_llm_engine)
    
    # Act
    result = await processor.analyze(processed_text, config)
    
    # Assert
    assert result['has_customer_probing'] is False
    assert result['customer_probing_details'] == ""
    mock_llm_engine.generate.assert_called_once()

@pytest.mark.asyncio
async def test_customer_probing_processor_empty_transcript(mock_llm_engine):
    """
    Test case with an empty transcript.
    """
    # Arrange
    processed_text = {"full_text": ""}
    config = AnalysisConfig()

    processor = CustomerProbingProcessor(mock_llm_engine)

    # Act
    result = await processor.analyze(processed_text, config)

    # Assert
    assert result['has_customer_probing'] is False
    assert result['customer_probing_details'] == ""
    mock_llm_engine.generate.assert_not_called()

@pytest.mark.asyncio
async def test_customer_probing_processor_short_transcript(mock_llm_engine):
    """
    Test case with a very short transcript.
    """
    # Arrange
    processed_text = {"full_text": "您好"}
    config = AnalysisConfig()

    processor = CustomerProbingProcessor(mock_llm_engine)

    # Act
    result = await processor.analyze(processed_text, config)

    # Assert
    assert result['has_customer_probing'] is False
    assert result['customer_probing_details'] == ""
    mock_llm_engine.generate.assert_not_called()

@pytest.mark.asyncio
async def test_customer_probing_processor_llm_disabled(mock_llm_engine):
    """
    Test case where LLM validation is disabled.
    """
    # Arrange
    transcript = "销售：您的仓位情况如何？投资风格是怎样的？"
    processed_text = {"full_text": transcript}
    config = AnalysisConfig(enable_llm_validation=False)

    processor = CustomerProbingProcessor(mock_llm_engine)

    # Act
    result = await processor.analyze(processed_text, config)

    # Assert
    assert result['has_customer_probing'] is False
    assert result['customer_probing_details'] == ""
    mock_llm_engine.generate.assert_not_called()

@pytest.mark.asyncio
async def test_customer_probing_processor_timeout_error(mock_llm_engine):
    """
    Test case where LLM times out.
    """
    # Arrange
    transcript = "销售：您的仓位情况如何？投资风格是怎样的？"
    processed_text = {"full_text": transcript}
    config = AnalysisConfig(enable_llm_validation=True)

    mock_llm_engine.generate.side_effect = asyncio.TimeoutError()

    processor = CustomerProbingProcessor(mock_llm_engine)

    # Act
    result = await processor.analyze(processed_text, config)

    # Assert
    assert result['has_customer_probing'] is False
    assert result['customer_probing_details'] == ""

@pytest.mark.asyncio
async def test_customer_probing_processor_invalid_input(mock_llm_engine):
    """
    Test case with invalid input data.
    """
    # Arrange
    processed_text = {"invalid_key": "some text"}  # Missing 'full_text' key
    config = AnalysisConfig()

    processor = CustomerProbingProcessor(mock_llm_engine)

    # Act
    result = await processor.analyze(processed_text, config)

    # Assert
    assert result['has_customer_probing'] is False
    assert result['customer_probing_details'] == ""
    mock_llm_engine.generate.assert_not_called()

@pytest.mark.asyncio
async def test_customer_probing_processor_various_positive_responses(mock_llm_engine):
    """
    Test case with various positive response formats.
    """
    test_cases = [
        "YES, 询问了客户的仓位情况",
        "是，有考察客户投资风格",
        "TRUE，存在考察客户情况的内容",
        "有询问客户的资金量和风险偏好"
    ]

    transcript = "销售：您目前的仓位大概是多少？风险承受能力如何？"
    processed_text = {"full_text": transcript}
    config = AnalysisConfig(enable_llm_validation=True)

    for response in test_cases:
        mock_llm_engine.generate.return_value = response
        processor = CustomerProbingProcessor(mock_llm_engine)

        # Act
        result = await processor.analyze(processed_text, config)

        # Assert
        assert result['has_customer_probing'] is True, f"Failed for response: {response}"
        assert len(result['customer_probing_details']) > 0
