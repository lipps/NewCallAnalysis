#!/usr/bin/env python3
"""调试要钱行为检测完整流程"""

import asyncio
import sys
import os
import json
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.models.schemas import CallInput, AnalysisConfig
from src.workflows.simplified_workflow import SimpleCallAnalysisWorkflow
from src.processors.text_processor import TextProcessor
from src.processors.process_processor import ProcessProcessor

async def debug_full_flow():
    """调试完整的要钱行为检测流程"""
    
    print("🔧 调试要钱行为检测完整流程")
    print("=" * 60)
    
    # 使用真实的销售对话数据
    test_transcript = """侯茜茜 2025年09月07日 17:29:48
全是收费嗯288。

侯茜茜 2025年09月07日 17:29:54
288您确定，啊因为像咱们这个软件的话，原价是1680一年的，相当于相当于想抢噢

侯茜茜 2025年09月07日 17:30:13
噢那相当于你抢到了咱们现实秒杀的一个活动，呀恭喜你啊哥，你想二百八二百八十八一年的时间，相当于一天平均算下来不到几毛钱，啊您现在的

客户 2025年09月07日 17:31:45
行，我再考虑一下吧好吧？

侯茜茜 2025年09月07日 17:33:59
这个话就耽误您几分钟的时间就可以了，您点进去操作办理一下。"""
    
    try:
        # 1. 创建输入
        call_input = CallInput(
            call_id="debug_money_ask_001",
            transcript=test_transcript,
            customer_id="debug_customer",
            sales_id="debug_sales",
            call_time=datetime.now().isoformat()
        )
        
        print(f"📋 输入通话文本长度: {len(test_transcript)} 字符")
        
        # 2. 文本预处理
        print("\n🔍 步骤1: 文本预处理")
        text_processor = TextProcessor()
        processed_text = await text_processor.process(test_transcript)
        
        print(f"处理后对话数量: {len(processed_text.get('dialogues', []))}")
        print(f"销售内容数量: {len(processed_text.get('content_analysis', {}).get('sales_content', []))}")
        
        # 显示销售内容
        sales_content = processed_text.get('content_analysis', {}).get('sales_content', [])
        print("\n销售话语内容:")
        for i, content in enumerate(sales_content[:5], 1):  # 只显示前5条
            print(f"  {i}. {content[:80]}{'...' if len(content) > 80 else ''}")
        
        # 3. 直接测试ProcessProcessor
        print("\n🔍 步骤2: 直接测试ProcessProcessor")
        process_processor = ProcessProcessor()
        config = AnalysisConfig()
        
        # 测试money_ask检测
        money_ask_result = process_processor._detect_money_ask(processed_text)
        print(f"直接调用_detect_money_ask结果: {money_ask_result}")
        
        # 测试完整analyze方法
        process_result = await process_processor.analyze(processed_text, config)
        print(f"ProcessProcessor完整分析结果:")
        print(f"  - money_ask_count: {process_result.money_ask_count}")
        print(f"  - money_ask_quotes长度: {len(process_result.money_ask_quotes)}")
        
        if process_result.money_ask_quotes:
            print("  - 证据片段:")
            for i, quote in enumerate(process_result.money_ask_quotes[:3], 1):
                print(f"    {i}. {quote[:100]}{'...' if len(quote) > 100 else ''}")
        
        # 4. 使用完整工作流测试
        print("\n🔍 步骤3: 完整工作流测试")
        
        # 创建配置（禁用LLM验证避免API调用）
        config = AnalysisConfig(
            enable_vector_search=False,
            enable_llm_validation=False,
            use_cache=True
        )
        
        # 使用简化工作流
        workflow = SimpleCallAnalysisWorkflow()
        await workflow.initialize()
        
        full_result = await workflow.execute(call_input, config)
        
        print(f"完整工作流结果:")
        print(f"  - call_id: {full_result.call_id}")
        print(f"  - process.money_ask_count: {full_result.process.money_ask_count}")
        print(f"  - process.money_ask_quotes长度: {len(full_result.process.money_ask_quotes)}")
        
        if full_result.process.money_ask_quotes:
            print("  - 完整工作流证据片段:")
            for i, quote in enumerate(full_result.process.money_ask_quotes[:3], 1):
                print(f"    {i}. {quote[:100]}{'...' if len(quote) > 100 else ''}")
        
        # 5. 保存结果用于对比
        result_dict = full_result.dict()
        with open('debug_money_ask_result.json', 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 调试完成，结果已保存到 debug_money_ask_result.json")
        
        # 检查是否有异常
        if full_result.process.money_ask_count == 0:
            print("\n❌ 问题确认：完整工作流中要钱行为次数为0")
            print("需要进一步调试工作流各个步骤")
        else:
            print(f"\n✅ 成功：检测到 {full_result.process.money_ask_count} 次要钱行为")
            
    except Exception as e:
        print(f"\n❌ 调试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_full_flow()) 