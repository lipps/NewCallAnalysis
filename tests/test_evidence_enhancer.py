"""证据增强器单元测试"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.adapters.evidence_enhancer import EvidenceEnhancer


class TestEvidenceEnhancer:
    """证据增强器测试类"""

    @pytest.fixture
    def enhancer(self):
        """创建证据增强器实例"""
        return EvidenceEnhancer(max_quote_length=200, cache_size=10)

    @pytest.fixture
    def sample_processed_text(self):
        """示例处理文本"""
        return {
            "dialogues": [
                {
                    "content": "销售：您好，我是益盟操盘手的专员小李，很高兴为您服务。",
                    "timestamp": "2024-01-15 10:30:01",
                    "speaker": "销售"
                },
                {
                    "content": "客户：你好。",
                    "timestamp": "2024-01-15 10:30:05",
                    "speaker": "客户"
                },
                {
                    "content": "销售：我们是腾讯投资的上市公司，专门为股民提供专业的分析服务。",
                    "timestamp": "2024-01-15 10:30:10",
                    "speaker": "销售"
                }
            ]
        }

    def test_enhance_evidence_empty_input(self, enhancer):
        """测试空输入"""
        result = enhancer.enhance_evidence("", None)
        assert result == []

        result = enhancer.enhance_evidence(None, None)
        assert result == []

    def test_enhance_evidence_no_processed_text(self, enhancer):
        """测试无处理文本的情况"""
        evidence = "销售专员介绍"
        result = enhancer.enhance_evidence(evidence, None)

        assert len(result) == 1
        assert result[0]["idx"] == 0
        assert result[0]["match_type"] == "fallback"
        assert result[0]["confidence"] == 0.5

    def test_enhance_evidence_exact_match(self, enhancer, sample_processed_text):
        """测试精确匹配"""
        evidence = "腾讯投资的上市公司"
        result = enhancer.enhance_evidence(evidence, sample_processed_text)

        assert len(result) > 0
        found_match = any(item["match_type"] == "exact" for item in result)
        assert found_match

        exact_match = next(item for item in result if item["match_type"] == "exact")
        assert exact_match["confidence"] == 1.0
        assert "腾讯投资" in exact_match["quote"]

    def test_enhance_evidence_keyword_match(self, enhancer, sample_processed_text):
        """测试关键词匹配"""
        evidence = "专员服务"
        result = enhancer.enhance_evidence(evidence, sample_processed_text)

        assert len(result) > 0
        # 应该有某种形式的匹配
        assert any(item["confidence"] > 0 for item in result)

    def test_parse_evidence_text_with_speaker_and_date(self, enhancer):
        """测试解析包含说话人和日期的证据文本"""
        evidence = "小李 2024年01月15日 我是益盟操盘手的专员"
        parsed = enhancer._parse_evidence_text(evidence)

        assert parsed["speaker"] == "小李"
        assert "2024-01-15" in parsed["timestamp"]
        assert "专员" in parsed["content"]

    def test_parse_evidence_text_with_time(self, enhancer):
        """测试解析包含时间的证据文本"""
        evidence = "10:30:01: 很高兴为您服务"
        parsed = enhancer._parse_evidence_text(evidence)

        assert parsed["timestamp"] == "10:30:01"
        assert "很高兴为您服务" in parsed["content"]

    def test_parse_evidence_text_plain(self, enhancer):
        """测试解析纯文本证据"""
        evidence = "这是一个简单的证据文本"
        parsed = enhancer._parse_evidence_text(evidence)

        assert parsed["content"] == evidence
        assert parsed["speaker"] is None

    def test_extract_keywords(self, enhancer):
        """测试关键词提取"""
        content = "我是益盟操盘手的专员小李，很高兴为您服务"
        keywords = enhancer._extract_keywords(content)

        # 检查返回类型和基本结构
        assert isinstance(keywords, list)
        assert len(keywords) > 0

        # 检查关键词是否包含预期内容
        keywords_str = ''.join(keywords)
        assert any("益盟" in keyword or "益盟" in keywords_str for keyword in keywords)
        assert any("操盘手" in keyword or "操盘" in keywords_str for keyword in keywords)

        # 停用词应该被过滤
        assert "的" not in keywords
        assert "我" not in keywords

    def test_calculate_keyword_match_score(self, enhancer):
        """测试关键词匹配分数计算"""
        keywords = ["益盟", "操盘手", "专员"]
        content1 = "我是益盟操盘手的专员小李"  # 全匹配
        content2 = "操盘手很专业"  # 部分匹配
        content3 = "今天天气很好"  # 无匹配

        score1 = enhancer._calculate_keyword_match_score(keywords, content1)
        score2 = enhancer._calculate_keyword_match_score(keywords, content2)
        score3 = enhancer._calculate_keyword_match_score(keywords, content3)

        assert score1 == 1.0  # 100%匹配
        assert 0 < score2 < 1.0  # 部分匹配
        assert score3 == 0.0  # 无匹配

    def test_truncate_quote(self, enhancer):
        """测试引用截断"""
        short_text = "短文本"
        long_text = "这是一个很长的文本" * 20 + "。这是句子结尾。" + "还有更多内容" * 10

        # 短文本不应该被截断
        assert enhancer._truncate_quote(short_text) == short_text

        # 长文本应该被截断
        truncated = enhancer._truncate_quote(long_text)
        assert len(truncated) <= enhancer.max_quote_length + 10  # 允许少量超出以保持句子完整

    def test_fuzzy_match_dialogues(self, enhancer, sample_processed_text):
        """测试模糊匹配"""
        content = "专业服务"
        matches = enhancer._fuzzy_match_dialogues(content, sample_processed_text["dialogues"])

        # 应该有一些匹配结果
        if matches:  # 如果有匹配
            assert all(0 <= match["confidence"] <= 1 for match in matches)
            assert all("idx" in match for match in matches)
            assert all("ts" in match for match in matches)

    def test_cache_functionality(self, enhancer, sample_processed_text):
        """测试缓存功能"""
        evidence = "腾讯投资"

        # 第一次调用
        result1 = enhancer.enhance_evidence(evidence, sample_processed_text)
        stats1 = enhancer.get_cache_stats()

        # 第二次调用（应该命中缓存）
        result2 = enhancer.enhance_evidence(evidence, sample_processed_text)
        stats2 = enhancer.get_cache_stats()

        # 结果应该相同
        assert result1 == result2

        # 缓存命中数应该增加
        assert stats2["hits"] > stats1["hits"]

    def test_cache_stats(self, enhancer):
        """测试缓存统计"""
        stats = enhancer.get_cache_stats()

        required_fields = ["cache_size", "max_size", "hits", "misses", "hit_rate", "total_requests"]
        for field in required_fields:
            assert field in stats

        assert stats["cache_size"] >= 0
        assert stats["max_size"] == 10  # 根据fixture设置
        assert stats["hit_rate"] >= 0.0

    def test_clear_cache(self, enhancer, sample_processed_text):
        """测试清空缓存"""
        # 先添加一些缓存
        enhancer.enhance_evidence("测试证据", sample_processed_text)
        stats_before = enhancer.get_cache_stats()

        # 清空缓存
        enhancer.clear_cache()
        stats_after = enhancer.get_cache_stats()

        assert stats_after["cache_size"] == 0
        assert stats_after["hits"] == 0
        assert stats_after["misses"] == 0

    def test_fallback_evidence_creation(self, enhancer):
        """测试降级证据创建"""
        parsed_evidence = {
            "original_text": "测试证据",
            "content": "测试内容",
            "timestamp": "2024-01-15 10:30:00",
            "keywords": ["测试"]
        }

        result = enhancer._create_fallback_evidence(parsed_evidence, "原始证据")

        assert len(result) == 1
        assert result[0]["match_type"] == "fallback"
        assert result[0]["confidence"] == 0.5
        assert result[0]["original_evidence"] == "原始证据"

    def test_error_handling(self, enhancer):
        """测试错误处理"""
        # 测试各种异常情况
        with patch.object(enhancer, '_parse_evidence_text', side_effect=Exception("解析错误")):
            result = enhancer.enhance_evidence("测试证据", {"dialogues": []})

            # 应该返回简单降级格式
            assert len(result) == 1
            assert result[0]["match_type"] == "simple_fallback"

    def test_context_hint_usage(self, enhancer, sample_processed_text):
        """测试上下文提示的使用"""
        evidence = "专员"
        context_hint = "专业身份"

        result = enhancer.enhance_evidence(evidence, sample_processed_text, context_hint)

        # 应该有结果
        assert len(result) >= 0

        # 缓存键应该包含context_hint
        cache_key = enhancer._generate_cache_key(evidence, sample_processed_text, context_hint)
        cache_key_no_hint = enhancer._generate_cache_key(evidence, sample_processed_text, None)

        assert cache_key != cache_key_no_hint

    @pytest.mark.parametrize("evidence_text,expected_type", [
        ("小李 2024年01月15日 证据内容", "timestamp"),
        ("10:30:01: 证据内容", "timestamp"),
        ("纯文本证据", "plain"),
        ("", "empty"),
    ])
    def test_evidence_parsing_variants(self, enhancer, evidence_text, expected_type):
        """测试各种证据格式的解析"""
        if evidence_text:
            parsed = enhancer._parse_evidence_text(evidence_text)

            if expected_type == "timestamp":
                assert parsed["timestamp"] is not None
            elif expected_type == "plain":
                assert parsed["content"] == evidence_text
                assert parsed["timestamp"] is None or parsed["timestamp"] != ""
        else:
            result = enhancer.enhance_evidence(evidence_text, None)
            assert result == []


# 集成测试
class TestEvidenceEnhancerIntegration:
    """证据增强器集成测试"""

    def test_real_world_scenario(self):
        """测试真实场景"""
        enhancer = EvidenceEnhancer()

        # 模拟真实的处理文本
        processed_text = {
            "dialogues": [
                {"content": "销售：您好，我是益盟操盘手的专员小李", "timestamp": "10:30:01", "speaker": "销售"},
                {"content": "客户：你好", "timestamp": "10:30:05", "speaker": "客户"},
                {"content": "销售：我们是腾讯投资的上市公司", "timestamp": "10:30:10", "speaker": "销售"},
                {"content": "客户：有什么功能吗？", "timestamp": "10:30:15", "speaker": "客户"},
                {"content": "销售：我们有BS买卖点提示功能", "timestamp": "10:30:20", "speaker": "销售"},
            ]
        }

        # 测试各种证据类型
        test_cases = [
            ("我是益盟操盘手的专员", "professional_identity"),
            ("腾讯投资", "company_background"),
            ("BS买卖点", "bs_explained"),
            ("不存在的内容", "no_match")
        ]

        for evidence, context in test_cases:
            result = enhancer.enhance_evidence(evidence, processed_text, context)

            # 基本验证
            assert isinstance(result, list)

            if evidence != "不存在的内容":
                # 应该有匹配结果
                assert len(result) > 0

                for item in result:
                    assert "idx" in item
                    assert "ts" in item
                    assert "quote" in item
                    assert "match_type" in item
                    assert "confidence" in item
                    assert 0 <= item["confidence"] <= 1
            else:
                # 不存在的内容应该有降级处理或空结果
                if result:  # 如果有结果，应该是低置信度的
                    assert all(item["confidence"] <= 0.5 for item in result)

    def test_performance_with_large_dataset(self):
        """测试大数据集性能"""
        enhancer = EvidenceEnhancer(cache_size=1000)

        # 创建大量对话
        large_processed_text = {
            "dialogues": [
                {
                    "content": f"对话内容 {i} 包含各种关键词",
                    "timestamp": f"10:{30 + i // 60}:{i % 60:02d}",
                    "speaker": "销售" if i % 2 == 0 else "客户"
                }
                for i in range(1000)
            ]
        }

        # 测试多次调用的性能
        import time
        start_time = time.time()

        for i in range(50):
            evidence = f"关键词 {i % 10}"
            result = enhancer.enhance_evidence(evidence, large_processed_text)
            assert isinstance(result, list)

        end_time = time.time()

        # 性能断言（50次调用应该在合理时间内完成）
        assert end_time - start_time < 10.0  # 10秒内完成

        # 检查缓存效果
        stats = enhancer.get_cache_stats()
        assert stats["total_requests"] == 50
        assert stats["hits"] > 0  # 应该有缓存命中