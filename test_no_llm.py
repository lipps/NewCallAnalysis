#!/usr/bin/env python3
"""无LLM依赖的测试脚本"""

import asyncio
import json
import sys
from datetime import datetime

from src.models.schemas import CallInput, AnalysisConfig
from src.workflows.simplified_workflow import SimpleCallAnalysisWorkflow
from src.engines.vector_engine import get_vector_engine
from src.engines.rule_engine import RuleEngine
from src.engines.llm_engine import get_llm_engine
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def test_without_llm():
    """测试不依赖LLM的功能"""
    
    print("🧪 测试销售通话质检系统（无LLM版本）")
    print("=" * 50)
    
    # 示例通话数据
    sample_transcript = """销售：您好，我是益盟操盘手的专员小王，很高兴为您服务。
客户：你好。
销售：是这样的，我们是腾讯投资的上市公司，专门为股民提供专业的股票分析服务。耽误您两分钟时间，我给您免费讲解一下我们的买卖点功能。
客户：好的，你说。
销售：咱们的核心功能是BS点提示，B点代表最佳买入时机，S点代表卖出信号。另外我们还有主力控盘资金指标，可以看到大资金的进出动向。
客户：听起来不错，有实际效果吗？
销售：根据历史回测数据，使用我们信号的客户平均能提升20%的收益率。咱们看看您现在持有什么股票，我给您具体分析一下。
客户：我持有招商银行。
销售：好的，我们来看看招商银行的买卖点情况。我们还有步步高VIP专属功能，能提供更精准的信号。
客户：这个功能是收费的吗？
销售：我们有不同的服务套餐，您可以先试用一下看效果。
客户：可以，我想了解一下。"""
    
    try:
        # 创建输入
        call_input = CallInput(
            call_id="test_no_llm_001",
            transcript=sample_transcript,
            customer_id="test_customer",
            sales_id="test_sales",
            call_time=datetime.now().isoformat()
        )
        
        # 创建配置（禁用LLM验证）
        config = AnalysisConfig(
            enable_vector_search=True,
            enable_llm_validation=False,  # 关键：禁用LLM验证
            confidence_threshold=0.5
        )
        
        # 初始化引擎
        print("🔧 初始化分析引擎...")
        vector_engine = await get_vector_engine()
        rule_engine = RuleEngine()
        llm_engine = get_llm_engine()
        
        print("✅ 分析引擎初始化完成")
        
        # 创建工作流（使用简化版本避免LangGraph复杂性）
        workflow = SimpleCallAnalysisWorkflow(
            vector_engine=vector_engine,
            rule_engine=rule_engine,
            llm_engine=llm_engine
        )
        
        # 执行分析
        print("\n🔄 开始分析（无LLM模式）...")
        result = await workflow.execute(call_input, config)
        
        # 输出结果
        print(f"\n✅ 分析完成！置信度: {result.confidence_score:.2f}")
        print("\n📊 分析结果概览:")
        
        # 破冰要点
        if hasattr(result.icebreak, 'professional_identity'):
            icebreak_hits = sum([
                result.icebreak.professional_identity.hit,
                result.icebreak.value_help.hit,
                result.icebreak.time_notice.hit,
                result.icebreak.company_background.hit,
                result.icebreak.free_teach.hit
            ])
            print(f"   破冰命中: {icebreak_hits}/5")
        
        # 功能演绎
        if hasattr(result.演绎, 'bs_explained'):
            deduction_hits = sum([
                result.演绎.bs_explained.hit,
                result.演绎.period_resonance_explained.hit,
                result.演绎.control_funds_explained.hit,
                result.演绎.bubugao_explained.hit,
                result.演绎.value_quantify_explained.hit,
                result.演绎.customer_stock_explained.hit
            ])
            print(f"   演绎覆盖: {deduction_hits}/6")
        
        # 过程指标
        if hasattr(result.process, 'explain_duration_min'):
            print(f"   通话时长: {result.process.explain_duration_min:.1f}分钟")
            print(f"   互动频率: {result.process.interaction_rounds_per_min:.1f}次/分钟")
            print(f"   成交约访: {'是' if result.process.deal_or_visit else '否'}")
        
        # 保存结果
        with open("test_no_llm_result.json", 'w', encoding='utf-8') as f:
            json.dump(result.dict(), f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 详细结果已保存到: test_no_llm_result.json")
        
        return result
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        raise

async def test_rule_engine_only():
    """测试仅使用规则引擎的功能"""
    
    print("\n🔧 测试规则引擎功能")
    print("-" * 30)
    
    try:
        rule_engine = RuleEngine()
        
        test_text = "我是益盟操盘手专员，我们的B点信号很准确"
        
        # 测试破冰检测
        icebreak_result = await rule_engine.detect("icebreak", "professional_identity", test_text)
        print(f"专业身份检测: {'命中' if icebreak_result['hit'] else '未命中'}, 置信度: {icebreak_result['confidence']:.2f}")
        
        # 测试演绎检测
        deduction_result = await rule_engine.detect("deduction", "bs_explained", test_text)
        print(f"BS点演绎检测: {'命中' if deduction_result['hit'] else '未命中'}, 置信度: {deduction_result['confidence']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ 规则引擎测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    
    print("🚀 开始无LLM依赖测试")
    print("=" * 60)
    
    # 规则引擎测试
    rule_test = await test_rule_engine_only()
    
    if rule_test:
        print("✅ 规则引擎测试通过")
        
        # 完整工作流测试
        try:
            await test_without_llm()
            print("\n🎉 无LLM测试完成！")
            print("\n💡 说明:")
            print("   - 规则引擎和向量检索正常工作")
            print("   - LLM验证已禁用，避免API Key问题")
            print("   - 所有核心功能可以正常运行")
            
        except Exception as e:
            print(f"\n❌ 完整测试失败: {e}")
    else:
        print("❌ 规则引擎测试失败")

if __name__ == "__main__":
    asyncio.run(main()) 