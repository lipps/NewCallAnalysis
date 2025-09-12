"""Unit tests for IcebreakProcessor LLM prompt building.

These tests assert that `_llm_validate_point` constructs its prompt without
syntax errors for both cases: with and without `vector_result`. We also check
that the produced prompt contains an appropriate, safely formatted
"向量检索结果" line ("N/A" when no vector hit; fixed 3‑decimal string when
provided).
"""

import pytest
from unittest.mock import MagicMock

from src.processors.icebreak_processor import IcebreakProcessor


class _FakeLLM:
    """Minimal async LLM stub capturing the last prompt."""

    def __init__(self, response: str) -> None:
        self._response = response
        self.last_prompt = None

    async def generate(self, *, prompt: str, max_tokens=None, temperature=None, system_prompt=None, stream=False):
        # capture for assertions
        self.last_prompt = prompt
        return self._response


@pytest.mark.asyncio
async def test_llm_validate_point_prompt_without_vector():
    # Arrange: fake engines and processor
    fake_llm = _FakeLLM(
        response=(
            "判定结果：是\n"
            "置信度：0.8\n"
            "证据片段：我是益盟操盘手专员\n"
            "理由：命中了专业身份描述"
        )
    )
    processor = IcebreakProcessor(
        vector_engine=MagicMock(),
        rule_engine=MagicMock(),
        llm_engine=fake_llm,
    )

    # Act
    result = await processor._llm_validate_point(
        point="professional_identity",
        text="销售：您好，我是益盟操盘手的专员。",
        rule_result={"hit": True, "confidence": 0.9, "evidence": "我是专员"},
        vector_result=None,
    )

    # Assert: prompt should contain the N/A fallback and parsing should succeed
    assert fake_llm.last_prompt is not None
    assert "向量检索结果：N/A" in fake_llm.last_prompt
    assert isinstance(result, dict) and result.get("hit") is True
    # confidence clamped/parsed into [0,1]
    assert 0.0 <= result.get("confidence", 0) <= 1.0


@pytest.mark.asyncio
async def test_llm_validate_point_prompt_with_vector_similarity_formatted():
    # Arrange
    fake_llm = _FakeLLM(
        response=(
            "判定结果：是\n"
            "置信度：0.75\n"
            "证据片段：我是益盟操盘手专员\n"
            "理由：命中了专业身份描述"
        )
    )
    processor = IcebreakProcessor(
        vector_engine=MagicMock(),
        rule_engine=MagicMock(),
        llm_engine=fake_llm,
    )

    vector_result = {"similarity": 0.73456, "document": "我是益盟操盘手专员…"}

    # Act
    result = await processor._llm_validate_point(
        point="professional_identity",
        text="销售：您好，我是益盟操盘手的专员。",
        rule_result={"hit": True, "confidence": 0.9, "evidence": "我是专员"},
        vector_result=vector_result,
    )

    # Assert: similarity appears as a fixed 3-decimal string in prompt
    assert fake_llm.last_prompt is not None
    assert "向量检索结果：0.735" in fake_llm.last_prompt
    assert isinstance(result, dict)
    assert 0.0 <= result.get("confidence", 0) <= 1.0

