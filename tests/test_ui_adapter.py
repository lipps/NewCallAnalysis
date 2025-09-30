"""UI适配器单元测试"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.adapters.ui_adapter import UIAdapter
from src.adapters.evidence_enhancer import EvidenceEnhancer
from src.models.schemas import (
    CallAnalysisResult, EvidenceHit, IcebreakModel, DeductionModel,
    ProcessModel, CustomerModel, ActionsModel, ActionExecution,
    CustomerProbingModel
)


class TestUIAdapter:
    """UI适配器测试类"""

    @pytest.fixture
    def mock_evidence_enhancer(self):
        """模拟证据增强器"""
        enhancer = Mock(spec=EvidenceEnhancer)
        enhancer.enhance_evidence.return_value = [
            {
                "idx": 0,
                "ts": "2024-01-15 10:30:01",
                "quote": "测试证据片段",
                "match_type": "exact",
                "confidence": 0.9
            }
        ]
        return enhancer

    @pytest.fixture
    def ui_adapter(self, mock_evidence_enhancer):
        """创建UI适配器实例"""
        return UIAdapter(evidence_enhancer=mock_evidence_enhancer)

    @pytest.fixture
    def sample_analysis_result(self):
        """示例分析结果"""
        return CallAnalysisResult(
            call_id="test_001",
            customer_id="customer_001",
            sales_id="sales_001",
            call_time="2024-01-15T10:30:00",
            analysis_timestamp=datetime.now().isoformat(),

            # 破冰模块
            icebreak=IcebreakModel(
                professional_identity=EvidenceHit(hit=True, evidence="我是益盟操盘手专员", confidence=0.9),
                value_help=EvidenceHit(hit=True, evidence="帮助您提升收益", confidence=0.8),
                time_notice=EvidenceHit(hit=True, evidence="耽误您两分钟", confidence=0.7),
                company_background=EvidenceHit(hit=True, evidence="腾讯投资的公司", confidence=0.9),
                free_teach=EvidenceHit(hit=True, evidence="免费讲解功能", confidence=0.8),
                rejection_reasons=[{"type": "忙", "quote": "我现在很忙"}],
                handling_strategies=[{"strategy": "共情", "quote": "理解您很忙"}],
                handle_objection_count=1
            ),

            # 演绎模块
            演绎=DeductionModel(
                bs_explained=EvidenceHit(hit=True, evidence="B点代表买入", confidence=0.9),
                period_resonance_explained=EvidenceHit(hit=False, evidence="", confidence=0.0),
                control_funds_explained=EvidenceHit(hit=True, evidence="控盘资金指标", confidence=0.8),
                bubugao_explained=EvidenceHit(hit=True, evidence="步步高功能", confidence=0.7),
                value_quantify_explained=EvidenceHit(hit=True, evidence="历史收益18%", confidence=0.9),
                customer_stock_explained=EvidenceHit(hit=True, evidence="您的招商银行", confidence=0.8)
            ),

            # 过程模块
            process=ProcessModel(
                explain_duration_min=15.5,
                interaction_rounds_per_min=2.3,
                deal_or_visit=True,
                total_words=1200,
                sales_words=800,
                customer_words=400,
                money_ask_count=2,
                money_ask_quotes=["试用一下我们的服务", "可以先体验一下"]
            ),

            # 客户模块
            customer=CustomerModel(
                summary="客户对产品表现出兴趣，询问了功能细节",
                questions=["有什么功能？", "费用多少？", "效果如何？"],
                value_recognition="YES",
                attitude_score=0.7
            ),

            # 动作模块
            actions=ActionsModel(
                professional_identity=ActionExecution(executed=True, count=1, evidence_list=["专员介绍"]),
                value_help=ActionExecution(executed=True, count=1, evidence_list=["价值说明"]),
                time_notice=ActionExecution(executed=True, count=1, evidence_list=["时间说明"]),
                company_background=ActionExecution(executed=True, count=1, evidence_list=["公司背景"]),
                free_teach=ActionExecution(executed=True, count=1, evidence_list=["免费讲解"]),
                bs_explained=ActionExecution(executed=True, count=1, evidence_list=["BS点讲解"]),
                period_resonance_explained=ActionExecution(executed=False, count=0, evidence_list=[]),
                control_funds_explained=ActionExecution(executed=True, count=1, evidence_list=["控盘资金"]),
                bubugao_explained=ActionExecution(executed=True, count=1, evidence_list=["步步高"]),
                value_quantify_explained=ActionExecution(executed=True, count=1, evidence_list=["价值量化"]),
                customer_stock_explained=ActionExecution(executed=True, count=1, evidence_list=["客户股票"])
            ),

            # 客户考察模块
            customer_probing=CustomerProbingModel(
                has_customer_probing=True,
                customer_probing_details="询问了持股情况"
            ),

            confidence_score=0.85,
            model_version="1.0.0"
        )

    @pytest.fixture
    def sample_processed_text(self):
        """示例处理文本"""
        return {
            "dialogues": [
                {"content": "销售：您好，我是益盟操盘手专员", "timestamp": "10:30:01", "speaker": "销售"},
                {"content": "客户：你好", "timestamp": "10:30:05", "speaker": "客户"},
                {"content": "销售：我们是腾讯投资的公司", "timestamp": "10:30:10", "speaker": "销售"}
            ]
        }

    def test_convert_to_ui_format_basic(self, ui_adapter, sample_analysis_result, sample_processed_text):
        """测试基本UI格式转换"""
        result = ui_adapter.convert_to_ui_format(sample_analysis_result, sample_processed_text)

        # 检查基本结构
        assert "output" in result
        output = result["output"]

        required_sections = [
            "customer_side", "standard_actions", "opening", "meta",
            "metrics", "rejects", "demo", "demo_more"
        ]
        for section in required_sections:
            assert section in output, f"Missing section: {section}"

    def test_map_customer_side(self, ui_adapter, sample_analysis_result):
        """测试客户侧数据映射"""
        customer_side = ui_adapter._map_customer_side(sample_analysis_result.customer)

        assert customer_side["questions"] == ["有什么功能？", "费用多少？", "效果如何？"]
        assert customer_side["summary"] == "客户对产品表现出兴趣，询问了功能细节"
        assert customer_side["value_recognition"] == "YES"

    def test_map_standard_actions(self, ui_adapter, sample_analysis_result):
        """测试标准动作映射"""
        actions_result = ui_adapter._map_standard_actions(
            sample_analysis_result.actions,
            sample_analysis_result.process
        )

        # 检查要钱行为
        money_ask = actions_result["money_ask"]
        assert money_ask["count"] == 2
        assert money_ask["total_attempts"] == 2
        assert len(money_ask["quotes"]) == 2

        # 检查动作摘要
        action_summary = actions_result["action_summary"]
        assert action_summary["total_executed"] > 0
        assert 0 <= action_summary["execution_rate"] <= 1
        assert isinstance(action_summary["key_actions"], list)

    def test_map_opening(self, ui_adapter, sample_analysis_result, sample_processed_text):
        """测试开场白映射"""
        opening = ui_adapter._map_opening(sample_analysis_result.icebreak, sample_processed_text)

        required_fields = [
            "professional_identity", "value_help", "time_notice",
            "tencent_invest", "free_teach"
        ]
        for field in required_fields:
            assert field in opening
            assert "hit" in opening[field]
            assert "evidence" in opening[field]
            assert "confidence" in opening[field]

    def test_map_meta(self, ui_adapter, sample_analysis_result):
        """测试元数据映射"""
        meta = ui_adapter._map_meta(sample_analysis_result)

        assert meta["call_id"] == "test_001"
        assert meta["customer_id"] == "customer_001"
        assert meta["sales_id"] == "sales_001"
        assert meta["call_time"] == "2024-01-15T10:30:00"

    def test_map_metrics(self, ui_adapter, sample_analysis_result):
        """测试指标映射"""
        metrics = ui_adapter._map_metrics(sample_analysis_result.process)

        assert metrics["talk_time_min"] == 15.5
        assert metrics["interactions_per_min"] == 2.3
        assert metrics["deal_or_visit"] == True

        word_stats = metrics["word_stats"]
        assert word_stats["total_words"] == 1200
        assert word_stats["sales_words"] == 800
        assert word_stats["customer_words"] == 400
        assert word_stats["sales_ratio"] == round(800/1200, 3)

    def test_map_rejects(self, ui_adapter, sample_analysis_result):
        """测试拒绝处理映射"""
        rejects = ui_adapter._map_rejects(sample_analysis_result.icebreak)

        assert rejects["handle_objection_count"] == 1
        assert len(rejects["rejection_reasons"]) == 1
        assert len(rejects["handling_strategies"]) == 1
        assert rejects["rejection_reasons"][0]["type"] == "忙"

    def test_map_demo(self, ui_adapter, sample_analysis_result, sample_processed_text):
        """测试演绎映射"""
        demo = ui_adapter._map_demo(sample_analysis_result.演绎, sample_processed_text)

        required_fields = [
            "bs_explained", "period_resonance_explained", "control_funds_explained",
            "bubugao_explained", "value_quantify_explained", "customer_stock_explained"
        ]
        for field in required_fields:
            assert field in demo
            assert "hit" in demo[field]
            assert "evidence" in demo[field]
            assert "confidence" in demo[field]

        # 测试命中和未命中的情况
        assert demo["bs_explained"]["hit"] == True
        assert demo["period_resonance_explained"]["hit"] == False

    def test_map_demo_more(self, ui_adapter, sample_analysis_result, sample_processed_text):
        """测试深度演绎映射"""
        demo_more = ui_adapter._map_demo_more(sample_analysis_result.演绎, sample_processed_text)

        # 检查主要字段
        for key in ["bs_explained", "period_resonance_explained", "control_funds_explained",
                   "bubugao_explained", "value_quantify_explained"]:
            assert key in demo_more
            assert "coverage" in demo_more[key]
            assert "depth_effectiveness" in demo_more[key]

            coverage = demo_more[key]["coverage"]
            assert "hit" in coverage
            assert "evidence" in coverage

            depth = demo_more[key]["depth_effectiveness"]
            assert "depth" in depth
            assert "effectiveness_score" in depth
            assert "analysis" in depth

    def test_convert_evidence_hit(self, ui_adapter, mock_evidence_enhancer, sample_processed_text):
        """测试证据命中转换"""
        evidence_hit = EvidenceHit(hit=True, evidence="测试证据", confidence=0.8)

        result = ui_adapter._convert_evidence_hit(evidence_hit, sample_processed_text, "测试上下文")

        assert result["hit"] == True
        assert result["confidence"] == 0.8
        assert "evidence" in result
        assert len(result["evidence"]) > 0

        # 验证证据增强器被调用
        mock_evidence_enhancer.enhance_evidence.assert_called_once()

    def test_analyze_depth_effectiveness(self, ui_adapter):
        """测试深度有效性分析"""
        # 测试命中的情况
        hit_evidence = EvidenceHit(hit=True, evidence="详细的功能讲解内容" * 10, confidence=0.9)
        result = ui_adapter._analyze_depth_effectiveness(hit_evidence, "BS点讲解")

        assert result["depth"] in ["浅显", "适中", "深入"]
        assert 0 <= result["effectiveness_score"] <= 1
        assert "BS点讲解" in result["analysis"]

        # 测试未命中的情况
        no_hit_evidence = EvidenceHit(hit=False, evidence="", confidence=0.0)
        result = ui_adapter._analyze_depth_effectiveness(no_hit_evidence, "周期共振")

        assert result["depth"] == "无"
        assert result["effectiveness_score"] == 0

    def test_count_executed_actions(self, ui_adapter, sample_analysis_result):
        """测试已执行动作计数"""
        count = ui_adapter._count_executed_actions(sample_analysis_result.actions)
        assert count > 0  # 示例数据中有多个已执行的动作

    def test_calculate_execution_rate(self, ui_adapter, sample_analysis_result):
        """测试执行率计算"""
        rate = ui_adapter._calculate_execution_rate(sample_analysis_result.actions)
        assert 0 <= rate <= 1

    def test_get_key_executed_actions(self, ui_adapter, sample_analysis_result):
        """测试关键已执行动作获取"""
        actions = ui_adapter._get_key_executed_actions(sample_analysis_result.actions)
        assert isinstance(actions, list)
        assert len(actions) > 0
        # 应该包含中文名称
        assert all(isinstance(action, str) for action in actions)

    def test_cache_functionality(self, ui_adapter, sample_analysis_result, sample_processed_text):
        """测试缓存功能"""
        # 第一次调用
        result1 = ui_adapter.convert_to_ui_format(sample_analysis_result, sample_processed_text)
        stats1 = ui_adapter.get_cache_stats()

        # 第二次调用（应该命中缓存）
        result2 = ui_adapter.convert_to_ui_format(sample_analysis_result, sample_processed_text)
        stats2 = ui_adapter.get_cache_stats()

        # 结果应该相同
        assert result1 == result2

        # 缓存命中应该增加
        if ui_adapter.enable_cache:
            assert stats2["hits"] > stats1["hits"]

    def test_fallback_ui_result(self, ui_adapter, sample_analysis_result):
        """测试降级UI结果"""
        fallback = ui_adapter._create_fallback_ui_result(sample_analysis_result)

        # 检查基本结构
        assert "output" in fallback
        assert "_adapter_metadata" in fallback
        assert fallback["_adapter_metadata"]["conversion_status"] == "fallback"

        # 检查所有必需字段都存在
        output = fallback["output"]
        required_sections = [
            "customer_side", "standard_actions", "opening", "meta",
            "metrics", "rejects", "demo", "demo_more"
        ]
        for section in required_sections:
            assert section in output

    def test_error_handling(self, ui_adapter, sample_analysis_result):
        """测试错误处理"""
        # 模拟证据增强器抛出异常
        ui_adapter.evidence_enhancer.enhance_evidence.side_effect = Exception("增强失败")

        # 应该仍然能够返回结果（使用降级处理）
        result = ui_adapter.convert_to_ui_format(sample_analysis_result, None)
        assert "output" in result

    def test_conversion_stats(self, ui_adapter):
        """测试转换统计"""
        stats = ui_adapter.get_conversion_stats()

        assert "adapter_cache" in stats
        assert "evidence_enhancer_cache" in stats
        assert "adapter_version" in stats

    def test_clear_cache(self, ui_adapter, sample_analysis_result, sample_processed_text):
        """测试清空缓存"""
        if not ui_adapter.enable_cache:
            return

        # 先添加一些缓存
        ui_adapter.convert_to_ui_format(sample_analysis_result, sample_processed_text)

        # 清空缓存
        ui_adapter.clear_cache()

        # 验证缓存被清空
        stats = ui_adapter.get_cache_stats()
        assert stats["cache_size"] == 0

    def test_without_processed_text(self, ui_adapter, sample_analysis_result):
        """测试没有处理文本的情况"""
        result = ui_adapter.convert_to_ui_format(sample_analysis_result, None)

        # 应该仍然能够生成结果
        assert "output" in result
        assert "_adapter_metadata" in result
        assert result["_adapter_metadata"]["has_processed_text"] == False

    def test_disabled_cache(self, mock_evidence_enhancer, sample_analysis_result, sample_processed_text):
        """测试禁用缓存的情况"""
        ui_adapter = UIAdapter(evidence_enhancer=mock_evidence_enhancer, enable_cache=False)

        result = ui_adapter.convert_to_ui_format(sample_analysis_result, sample_processed_text)
        stats = ui_adapter.get_cache_stats()

        assert result is not None
        assert stats["cache_enabled"] == False

    @pytest.mark.parametrize("include_metadata", [True, False])
    def test_metadata_inclusion(self, ui_adapter, sample_analysis_result, sample_processed_text, include_metadata):
        """测试元数据包含选项"""
        result = ui_adapter.convert_to_ui_format(
            sample_analysis_result, sample_processed_text, include_metadata=include_metadata
        )

        if include_metadata:
            assert "_adapter_metadata" in result
            assert "meta" in result["output"] and result["output"]["meta"]
        else:
            assert result["output"]["meta"] == {}


# 集成测试
class TestUIAdapterIntegration:
    """UI适配器集成测试"""

    def test_full_conversion_pipeline(self):
        """测试完整转换管道"""
        # 创建真实的适配器组件
        evidence_enhancer = EvidenceEnhancer(max_quote_length=200, cache_size=50)
        ui_adapter = UIAdapter(evidence_enhancer=evidence_enhancer)

        # 创建示例数据
        analysis_result = CallAnalysisResult(
            call_id="integration_test",
            customer_id="customer_test",
            sales_id="sales_test",
            call_time="2024-01-15T10:30:00",
            analysis_timestamp=datetime.now().isoformat(),

            icebreak=IcebreakModel(
                professional_identity=EvidenceHit(hit=True, evidence="我是专员小李", confidence=0.9),
                value_help=EvidenceHit(hit=True, evidence="帮助您获得收益", confidence=0.8),
                time_notice=EvidenceHit(hit=True, evidence="占用您几分钟", confidence=0.7),
                company_background=EvidenceHit(hit=True, evidence="腾讯投资背景", confidence=0.9),
                free_teach=EvidenceHit(hit=True, evidence="免费为您讲解", confidence=0.8)
            ),

            演绎=DeductionModel(
                bs_explained=EvidenceHit(hit=True, evidence="B点S点买卖信号", confidence=0.9),
                period_resonance_explained=EvidenceHit(hit=False, evidence="", confidence=0.0),
                control_funds_explained=EvidenceHit(hit=True, evidence="主力控盘资金", confidence=0.8),
                bubugao_explained=EvidenceHit(hit=True, evidence="步步高指标", confidence=0.7),
                value_quantify_explained=EvidenceHit(hit=True, evidence="客户收益18%", confidence=0.9),
                customer_stock_explained=EvidenceHit(hit=True, evidence="分析您的股票", confidence=0.8)
            ),

            process=ProcessModel(
                explain_duration_min=12.5,
                interaction_rounds_per_min=1.8,
                deal_or_visit=True,
                total_words=1000,
                sales_words=650,
                customer_words=350,
                money_ask_count=1,
                money_ask_quotes=["可以先体验一下"]
            ),

            customer=CustomerModel(
                summary="客户表现出浓厚兴趣",
                questions=["怎么使用？", "费用多少？"],
                value_recognition="YES",
                attitude_score=0.8
            ),

            actions=ActionsModel(
                professional_identity=ActionExecution(executed=True, count=1, evidence_list=["专员介绍"]),
                value_help=ActionExecution(executed=True, count=1, evidence_list=["价值说明"]),
                time_notice=ActionExecution(executed=True, count=1, evidence_list=["时间说明"]),
                company_background=ActionExecution(executed=True, count=1, evidence_list=["公司背景"]),
                free_teach=ActionExecution(executed=True, count=1, evidence_list=["免费讲解"]),
                bs_explained=ActionExecution(executed=True, count=1, evidence_list=["BS讲解"]),
                period_resonance_explained=ActionExecution(executed=False, count=0, evidence_list=[]),
                control_funds_explained=ActionExecution(executed=True, count=1, evidence_list=["控盘资金"]),
                bubugao_explained=ActionExecution(executed=True, count=1, evidence_list=["步步高"]),
                value_quantify_explained=ActionExecution(executed=True, count=1, evidence_list=["价值量化"]),
                customer_stock_explained=ActionExecution(executed=True, count=1, evidence_list=["客户股票"])
            ),

            customer_probing=CustomerProbingModel(
                has_customer_probing=True,
                customer_probing_details="询问持股情况和投资经验"
            ),

            confidence_score=0.85,
            model_version="1.0.0"
        )

        processed_text = {
            "dialogues": [
                {"content": "销售：您好，我是专员小李", "timestamp": "10:30:01", "speaker": "销售"},
                {"content": "客户：你好", "timestamp": "10:30:05", "speaker": "客户"},
                {"content": "销售：我们有腾讯投资背景", "timestamp": "10:30:10", "speaker": "销售"},
                {"content": "客户：有什么功能？", "timestamp": "10:30:15", "speaker": "客户"},
                {"content": "销售：B点S点买卖信号功能", "timestamp": "10:30:20", "speaker": "销售"},
                {"content": "客户：怎么使用？", "timestamp": "10:30:25", "speaker": "客户"},
            ]
        }

        # 执行转换
        result = ui_adapter.convert_to_ui_format(analysis_result, processed_text)

        # 全面验证
        assert isinstance(result, dict)
        assert "output" in result
        assert "_adapter_metadata" in result

        output = result["output"]

        # 验证每个部分的数据完整性
        assert output["customer_side"]["questions"] == ["怎么使用？", "费用多少？"]
        assert output["customer_side"]["value_recognition"] == "YES"

        assert output["metrics"]["talk_time_min"] == 12.5
        assert output["metrics"]["deal_or_visit"] == True

        assert output["opening"]["professional_identity"]["hit"] == True
        assert len(output["opening"]["professional_identity"]["evidence"]) > 0

        assert output["demo"]["bs_explained"]["hit"] == True
        assert output["demo"]["period_resonance_explained"]["hit"] == False

        # 验证demo_more的深度分析
        bs_demo_more = output["demo_more"]["bs_explained"]
        assert "coverage" in bs_demo_more
        assert "depth_effectiveness" in bs_demo_more
        assert bs_demo_more["depth_effectiveness"]["effectiveness_score"] > 0

        # 验证标准动作
        actions = output["standard_actions"]
        assert actions["money_ask"]["count"] == 1
        assert actions["action_summary"]["total_executed"] > 0

        # 验证元数据
        metadata = result["_adapter_metadata"]
        assert metadata["adapter_version"] == "1.0.0"
        assert metadata["source_call_id"] == "integration_test"
        assert metadata["has_processed_text"] == True

    def test_performance_benchmark(self):
        """性能基准测试"""
        import time

        evidence_enhancer = EvidenceEnhancer(cache_size=200)
        ui_adapter = UIAdapter(evidence_enhancer=evidence_enhancer, cache_size=100)

        # 创建测试数据
        analysis_result = self._create_minimal_analysis_result()
        processed_text = self._create_large_processed_text(100)  # 100条对话

        # 性能测试
        start_time = time.time()

        for i in range(20):  # 20次转换
            result = ui_adapter.convert_to_ui_format(analysis_result, processed_text)
            assert "output" in result

        end_time = time.time()

        # 性能断言
        total_time = end_time - start_time
        avg_time = total_time / 20

        print(f"平均转换时间: {avg_time:.3f}秒")
        assert avg_time < 1.0, f"转换时间过长: {avg_time}秒"

        # 验证缓存效果
        cache_stats = ui_adapter.get_cache_stats()
        if ui_adapter.enable_cache:
            assert cache_stats["hits"] > 0

    def _create_minimal_analysis_result(self):
        """创建最小的分析结果"""
        from src.models.schemas import EvidenceHit, ActionExecution

        # 创建默认的EvidenceHit
        default_evidence = EvidenceHit(hit=False, evidence="", confidence=0.0)

        return CallAnalysisResult(
            call_id="perf_test",
            customer_id="customer_perf",
            sales_id="sales_perf",
            call_time="2024-01-15T10:30:00",
            analysis_timestamp=datetime.now().isoformat(),

            icebreak=IcebreakModel(
                professional_identity=default_evidence,
                value_help=default_evidence,
                time_notice=default_evidence,
                company_background=default_evidence,
                free_teach=default_evidence
            ),
            演绎=DeductionModel(
                bs_explained=default_evidence,
                period_resonance_explained=default_evidence,
                control_funds_explained=default_evidence,
                bubugao_explained=default_evidence,
                value_quantify_explained=default_evidence,
                customer_stock_explained=default_evidence
            ),
            process=ProcessModel(),
            customer=CustomerModel(),
            actions=ActionsModel(
                # 创建默认的ActionExecution
                professional_identity=ActionExecution(executed=False, count=0),
                value_help=ActionExecution(executed=False, count=0),
                time_notice=ActionExecution(executed=False, count=0),
                company_background=ActionExecution(executed=False, count=0),
                free_teach=ActionExecution(executed=False, count=0),
                bs_explained=ActionExecution(executed=False, count=0),
                period_resonance_explained=ActionExecution(executed=False, count=0),
                control_funds_explained=ActionExecution(executed=False, count=0),
                bubugao_explained=ActionExecution(executed=False, count=0),
                value_quantify_explained=ActionExecution(executed=False, count=0),
                customer_stock_explained=ActionExecution(executed=False, count=0)
            ),
            customer_probing=CustomerProbingModel(),

            confidence_score=0.5,
            model_version="1.0.0"
        )

    def _create_large_processed_text(self, dialogue_count):
        """创建大量对话的处理文本"""
        return {
            "dialogues": [
                {
                    "content": f"对话内容 {i}，包含各种测试关键词",
                    "timestamp": f"10:{30 + i // 60}:{i % 60:02d}",
                    "speaker": "销售" if i % 2 == 0 else "客户"
                }
                for i in range(dialogue_count)
            ]
        }