"""测试修复效果"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.models.schemas import CallInput, AnalysisConfig
from simplified_workflow import SimpleCallAnalysisWorkflow
from src.engines.vector_engine import get_vector_engine
from src.engines.rule_engine import RuleEngine
from src.engines.llm_engine import get_llm_engine

async def test_workflow_fix():
    """测试工作流修复"""
    
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
        call_id="test_fix_001",
        transcript=sample_transcript
    )
    
    try:
        print("🧪 测试工作流修复")
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
        
        # 执行分析（只进行基础分析，不调用LLM避免超时）
        config = AnalysisConfig(
            enable_llm_validation=False,  # 禁用LLM验证避免超时
            confidence_threshold=0.5
        )
        
        print("开始分析...")
        result = await workflow.execute(call_input, config)
        
        print("✅ 分析成功完成！")
        print(f"通话ID: {result.call_id}")
        print(f"置信度: {result.confidence_score:.3f}")
        print(f"客户分析: {result.customer}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_workflow_fix())
    if success:
        print("\n🎉 所有修复测试通过！")
    else:
        print("\n💥 测试失败，需要进一步修复")