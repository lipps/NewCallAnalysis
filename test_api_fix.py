"""测试API修复"""

import asyncio
import json
from src.models.schemas import CallInput, AnalysisConfig
from src.workflows.simplified_workflow import SimpleCallAnalysisWorkflow
from src.engines.vector_engine import get_vector_engine
from src.engines.rule_engine import RuleEngine
from src.engines.llm_engine import get_llm_engine

async def test_api_workflow():
    """测试API工作流修复"""
    
    # 示例数据
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
    
    call_input = CallInput(
        call_id="test_api_fix_001",
        transcript=sample_transcript
    )
    
    try:
        print("🧪 测试API工作流修复")
        print("=" * 50)
        
        # 初始化引擎
        print("初始化引擎...")
        vector_engine = await get_vector_engine()
        rule_engine = RuleEngine()
        llm_engine = get_llm_engine()
        
        # 创建简化工作流
        print("创建简化工作流...")
        workflow = SimpleCallAnalysisWorkflow(
            vector_engine=vector_engine,
            rule_engine=rule_engine,
            llm_engine=llm_engine
        )
        
        # 执行分析（禁用LLM验证避免超时）
        config = AnalysisConfig(
            enable_llm_validation=False,  # 禁用LLM验证
            confidence_threshold=0.5
        )
        
        print("开始分析...")
        result = await workflow.execute(call_input, config)
        
        print("✅ 分析成功完成！")
        print(f"通话ID: {result.call_id}")
        print(f"置信度: {result.confidence_score:.3f}")
        
        # 检查客户分析
        print(f"\n客户分析:")
        print(f"  总结: {result.customer.summary}")
        print(f"  态度评分: {result.customer.attitude_score}")
        print(f"  价值认同: {result.customer.value_recognition.value}")
        
        # 检查破冰分析
        icebreak_hits = sum([
            result.icebreak.professional_identity.hit,
            result.icebreak.value_help.hit,
            result.icebreak.time_notice.hit,
            result.icebreak.company_background.hit,
            result.icebreak.free_teach.hit
        ])
        print(f"\n破冰要点命中: {icebreak_hits}/5")
        
        # 检查演绎分析
        deduction_hits = sum([
            result.演绎.bs_explained.hit,
            result.演绎.period_resonance_explained.hit,
            result.演绎.control_funds_explained.hit,
            result.演绎.bubugao_explained.hit,
            result.演绎.value_quantify_explained.hit,
            result.演绎.customer_stock_explained.hit
        ])
        print(f"演绎覆盖: {deduction_hits}/6")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_api_workflow())
    if success:
        print("\n🎉 API工作流修复成功！")
        print("📋 现在服务器应该使用简化工作流，避免LangGraph并发问题")
    else:
        print("\n💥 测试失败，需要进一步调试")