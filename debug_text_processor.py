#!/usr/bin/env python3
"""专门调试文本处理器的脚本"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.processors.text_processor import TextProcessor

async def debug_text_processor():
    """调试文本处理器的说话人识别"""
    
    print("🔧 调试文本处理器")
    print("=" * 50)
    
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

    processor = TextProcessor()
    
    print("📋 原始文本:")
    print(test_transcript)
    print()
    
    # 1. 测试文本清理
    print("🔍 步骤1: 文本清理")
    cleaned = processor._clean_text(test_transcript)
    print("清理后文本:")
    print(cleaned)
    print()
    
    # 2. 测试对话分割
    print("🔍 步骤2: 对话分割")
    dialogues = processor._split_dialogues(cleaned)
    print(f"分割出 {len(dialogues)} 个对话片段:")
    for i, dialogue in enumerate(dialogues, 1):
        print(f"  {i}. {dialogue}")
    print()
    
    # 3. 测试说话人识别
    print("🔍 步骤3: 说话人识别")
    speaker_dialogues = processor._identify_speakers(dialogues)
    print(f"识别出 {len(speaker_dialogues)} 个说话者对话:")
    for i, dlg in enumerate(speaker_dialogues, 1):
        print(f"  {i}. 说话人: {dlg['speaker']}")
        print(f"     原始: {dlg['original']}")
        print(f"     内容: {dlg['content']}")
        print()
    
    # 4. 测试内容分析
    print("🔍 步骤4: 内容分析")
    timed_dialogues = processor._process_timestamps(speaker_dialogues)
    content_analysis = processor._analyze_content(timed_dialogues)
    
    print(f"销售内容数量: {len(content_analysis.get('sales_content', []))}")
    print(f"客户内容数量: {len(content_analysis.get('customer_content', []))}")
    
    print("\n销售内容:")
    for i, content in enumerate(content_analysis.get('sales_content', []), 1):
        print(f"  {i}. {content}")
    
    print("\n客户内容:")
    for i, content in enumerate(content_analysis.get('customer_content', []), 1):
        print(f"  {i}. {content}")
    
    # 5. 手动测试正则表达式
    print("\n🔍 步骤5: 手动测试正则表达式")
    import re
    
    test_lines = [
        "侯茜茜 2025年09月07日 17:29:48",
        "全是收费嗯288。",
        "客户 2025年09月07日 17:31:45",
        "行，我再考虑一下吧好吧？"
    ]
    
    for line in test_lines:
        print(f"测试行: {line}")
        
        # 测试销售模式
        for i, pattern in enumerate(processor.speaker_patterns['sales']):
            if re.search(pattern, line):
                print(f"  ✅ 匹配销售模式 {i+1}: {pattern}")
            else:
                print(f"  ❌ 不匹配销售模式 {i+1}: {pattern}")
        
        # 测试客户模式
        for i, pattern in enumerate(processor.speaker_patterns['customer']):
            if re.search(pattern, line):
                print(f"  ✅ 匹配客户模式 {i+1}: {pattern}")
            else:
                print(f"  ❌ 不匹配客户模式 {i+1}: {pattern}")
        print()

if __name__ == "__main__":
    asyncio.run(debug_text_processor()) 