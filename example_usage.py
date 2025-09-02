"""使用示例和演示脚本"""

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


async def demo_single_analysis():
    """演示单个通话分析"""
    
    print("🔍 演示单个通话分析")
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
        # 检查API Key配置
        from src.config.settings import settings
        has_valid_api_key = (
            settings.model.openai_api_key and 
            settings.model.openai_api_key != "" and 
            settings.model.openai_api_key != "test_key_for_demo" and
            not settings.model.openai_api_key.startswith("你的")
        )
        
        if not has_valid_api_key:
            print("⚠️  使用无LLM模式运行（规则引擎 + 向量检索）")
        
        # 创建输入
        call_input = CallInput(
            call_id="demo_001",
            transcript=sample_transcript,
            customer_id="customer_demo",
            sales_id="sales_demo",
            call_time=datetime.now().isoformat()
        )
        
        # 创建配置（根据API Key可用性动态调整）
        config = AnalysisConfig(
            enable_vector_search=True,
            enable_llm_validation=has_valid_api_key,  # 根据API Key可用性调整
            confidence_threshold=0.7
        )
        
        # 初始化引擎
        print("初始化分析引擎...")
        vector_engine = await get_vector_engine()
        rule_engine = RuleEngine()
        llm_engine = get_llm_engine()
        
        # 创建工作流（使用简化版本）
        workflow = SimpleCallAnalysisWorkflow(
            vector_engine=vector_engine,
            rule_engine=rule_engine,
            llm_engine=llm_engine
        )
        
        # 执行分析
        print("\n🔄 开始分析...")
        result = await workflow.execute(call_input, config)
        
        # 输出结果
        print(f"\n✅ 分析完成！置信度: {result.confidence_score:.2f}")
        print("\n📊 分析结果概览:")
        
        # 破冰要点
        icebreak_hits = sum([
            result.icebreak.professional_identity.hit,
            result.icebreak.value_help.hit,
            result.icebreak.time_notice.hit,
            result.icebreak.company_background.hit,
            result.icebreak.free_teach.hit
        ])
        print(f"   破冰命中: {icebreak_hits}/5")
        
        # 功能演绎
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
        print(f"   通话时长: {result.process.explain_duration_min:.1f}分钟")
        print(f"   互动频率: {result.process.interaction_rounds_per_min:.1f}次/分钟")
        print(f"   成交约访: {'是' if result.process.deal_or_visit else '否'}")
        
        # 客户分析
        print(f"   客户态度: {result.customer.value_recognition.value}")
        print(f"   态度评分: {result.customer.attitude_score:.2f}")
        
        # 保存结果
        with open("demo_result.json", 'w', encoding='utf-8') as f:
            json.dump(result.dict(), f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 详细结果已保存到: demo_result.json")
        
        return result
        
    except Exception as e:
        logger.error(f"演示分析失败: {e}")
        print(f"❌ 分析失败: {e}")
        raise


async def demo_batch_analysis():
    """演示批量分析"""
    
    print("\n📊 演示批量分析")
    print("=" * 50)
    
    # 创建批量测试数据
    batch_calls = [
        CallInput(
            call_id=f"batch_demo_{i:03d}",
            transcript=f"销售：您好，我是益盟专员。客户：你好。销售：我们提供股票分析服务。客户：{'好的，了解一下' if i % 2 == 0 else '不需要，谢谢'}。",
            customer_id=f"customer_{i:03d}",
            sales_id=f"sales_{i:03d}"
        )
        for i in range(5)
    ]
    
    try:
        # 检查API Key配置
        from src.config.settings import settings
        has_valid_api_key = (
            settings.model.openai_api_key and 
            settings.model.openai_api_key != "" and 
            settings.model.openai_api_key != "test_key_for_demo" and
            not settings.model.openai_api_key.startswith("你的")
        )
        
        # 创建配置
        config = AnalysisConfig(
            enable_vector_search=True,
            enable_llm_validation=has_valid_api_key,
            confidence_threshold=0.7
        )
        
        # 初始化引擎
        print("初始化分析引擎...")
        vector_engine = await get_vector_engine()
        rule_engine = RuleEngine()
        llm_engine = get_llm_engine()
        
        # 创建工作流（使用简化版本）
        workflow = SimpleCallAnalysisWorkflow(
            vector_engine=vector_engine,
            rule_engine=rule_engine,
            llm_engine=llm_engine
        )
        
        # 执行批量分析
        print(f"\n🔄 开始批量分析 {len(batch_calls)} 个通话...")
        import time
        start_time = time.time()
        
        results = await workflow.execute_batch(
            batch_calls, 
            config,
            max_concurrency=3
        )
        
        end_time = time.time()
        
        # 统计结果
        success_count = sum(1 for r in results if r.confidence_score > 0.5)
        avg_confidence = sum(r.confidence_score for r in results) / len(results)
        
        print(f"\n✅ 批量分析完成！")
        print(f"   耗时: {end_time - start_time:.2f}秒")
        print(f"   成功率: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")
        print(f"   平均置信度: {avg_confidence:.2f}")
        
        # 保存批量结果
        batch_results = [result.dict() for result in results]
        with open("batch_demo_results.json", 'w', encoding='utf-8') as f:
            json.dump(batch_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 批量结果已保存到: batch_demo_results.json")
        
        return results
        
    except Exception as e:
        logger.error(f"批量分析演示失败: {e}")
        print(f"❌ 批量分析失败: {e}")
        raise


async def demo_performance_test():
    """演示性能测试"""
    
    print("\n⚡ 演示性能测试")
    print("=" * 50)
    
    try:
        # 初始化引擎
        vector_engine = await get_vector_engine()
        rule_engine = RuleEngine()
        llm_engine = get_llm_engine()
        
        # 创建工作流（使用简化版本）
        workflow = SimpleCallAnalysisWorkflow(
            vector_engine=vector_engine,
            rule_engine=rule_engine,
            llm_engine=llm_engine
        )
        
        # 获取引擎统计信息
        print("📈 系统统计信息:")
        vector_stats = vector_engine.get_statistics()
        rule_stats = rule_engine.get_statistics() 
        llm_stats = llm_engine.get_statistics()
        
        print(f"   向量引擎: {vector_stats.get('document_count', 0)} 文档")
        print(f"   规则引擎: {rule_stats.get('total_rules', 0)} 规则")
        print(f"   LLM引擎: {llm_stats.get('request_count', 0)} 请求")
        
        # 性能基准测试
        test_transcript = "销售：您好，我是益盟操盘手专员。客户：你好。销售：我们提供专业的股票分析服务，包括买卖点提示功能。客户：听起来不错。"
        
        # 单次分析性能
        import time
        start_time = time.time()
        
        call_input = CallInput(
            call_id="perf_test",
            transcript=test_transcript
        )
        
        # 创建测试配置
        from src.config.settings import settings
        has_valid_api_key = (
            settings.model.openai_api_key and 
            settings.model.openai_api_key != "" and 
            settings.model.openai_api_key != "test_key_for_demo" and
            not settings.model.openai_api_key.startswith("你的")
        )
        config = AnalysisConfig(enable_llm_validation=has_valid_api_key)
        
        result = await workflow.execute(call_input, config)
        end_time = time.time()
        
        single_time = end_time - start_time
        print(f"\n⏱️  单次分析耗时: {single_time:.2f}秒")
        
        # 并发分析性能
        start_time = time.time()
        
        concurrent_inputs = [
            CallInput(call_id=f"concurrent_{i}", transcript=test_transcript)
            for i in range(3)
        ]
        
        concurrent_results = await workflow.execute_batch(
            concurrent_inputs,
            config,
            max_concurrency=3
        )
        
        end_time = time.time()
        concurrent_time = end_time - start_time
        
        print(f"⚡ 3个并发分析耗时: {concurrent_time:.2f}秒")
        print(f"🚀 并发效率提升: {(single_time * 3 / concurrent_time):.1f}x")
        
        return {
            "single_time": single_time,
            "concurrent_time": concurrent_time,
            "efficiency_gain": single_time * 3 / concurrent_time
        }
        
    except Exception as e:
        logger.error(f"性能测试失败: {e}")
        print(f"❌ 性能测试失败: {e}")
        raise


def print_usage_examples():
    """打印使用示例"""
    
    print("\n📖 使用示例")
    print("=" * 50)
    
    examples = [
        {
            "title": "1. 命令行单次分析",
            "command": 'python main.py analyze --text "销售：您好，我是益盟操盘手专员..."'
        },
        {
            "title": "2. 启动API服务器",
            "command": "python run_server.py"
        },
        {
            "title": "3. 启动可视化Dashboard", 
            "command": "python run_dashboard.py"
        },
        {
            "title": "4. 生成示例数据",
            "command": "python main.py sample --output sample_calls.json"
        },
        {
            "title": "5. 批量分析",
            "command": "python main.py batch --file sample_calls.json --output results.json"
        },
        {
            "title": "6. 运行测试",
            "command": "pytest tests/ -v"
        }
    ]
    
    for example in examples:
        print(f"\n{example['title']}:")
        print(f"   {example['command']}")
    
    print("\n🌐 API接口:")
    print("   POST http://localhost:8000/analyze - 单次分析")
    print("   POST http://localhost:8000/analyze/batch - 批量分析")
    print("   GET  http://localhost:8000/docs - API文档")
    
    print("\n🎨 Dashboard:")
    print("   http://localhost:8501 - 可视化界面")


async def main():
    """主演示函数"""
    
    print("🎯 销售通话质检系统 - 功能演示")
    print("=" * 60)
    
    try:
        # 检查环境
        from src.config.settings import settings
        
        # 检测API Key配置
        has_valid_api_key = (
            settings.model.openai_api_key and 
            settings.model.openai_api_key != "" and 
            settings.model.openai_api_key != "test_key_for_demo" and
            not settings.model.openai_api_key.startswith("你的")
        )
        
        if not has_valid_api_key:
            print("⚠️  警告: 未配置有效的OPENAI_API_KEY，将以无LLM模式运行")
            print("   如需启用完整功能，请在.env文件中配置真实的API密钥")
            print("   当前将仅使用规则引擎和向量检索功能")
        
        print(f"✅ 系统配置正常")
        print(f"   模型: {settings.model.llm_model}")
        print(f"   向量模型: {settings.model.embedding_model}")
        
        # 运行演示
        print("\n🚀 开始功能演示...")
        
        # 单次分析演示
        await demo_single_analysis()
        
        # 批量分析演示
        await demo_batch_analysis()
        
        # 性能测试演示
        await demo_performance_test()
        
        # 使用示例
        print_usage_examples()
        
        print("\n🎉 演示完成！")
        print("\n💡 下一步:")
        print("   1. 启动API服务器: python run_server.py")
        print("   2. 启动Dashboard: python run_dashboard.py")
        print("   3. 使用API进行实际分析")
        
    except Exception as e:
        logger.error(f"演示失败: {e}")
        print(f"❌ 演示失败: {e}")
        
        print("\n🔧 故障排除:")
        print("   1. 检查.env配置文件")
        print("   2. 确保网络连接正常")
        print("   3. 检查Python依赖是否完整安装")
        print("   4. 查看logs/app.log了解详细错误信息")


if __name__ == "__main__":
    # 设置事件循环策略（Windows兼容性）
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())