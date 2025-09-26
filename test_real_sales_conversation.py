#!/usr/bin/env python3
"""测试实际销售对话中的要钱行为检测"""

import asyncio
import sys
import os
import re

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.processors.process_processor import ProcessProcessor
from src.processors.text_processor import TextProcessor

async def test_real_sales_conversation():
    """测试实际销售对话中的要钱行为检测"""
    
    print("🧪 测试实际销售对话 - 要钱行为检测")
    print("=" * 60)
    
    # 实际的销售对话数据
    real_sales_text = """侯茜茜 2025年09月07日 16:48:21
您好您好，请问是尾号是744的机主本人吗？

客户 2025年09月07日 16:48:25
你说。

侯茜茜 2025年09月07日 16:48:26
这边看您在8月7号有下载注册了咱们益盟操盘手股票分析软件，很多同期下载的用户反馈软件功能不太会用，。

侯茜茜 2025年09月07日 16:48:37
所以公司特地安排我给你来电，专门免费教您使用的，如果您用下来觉得好，后期长期免费去用就可以了，您这边用的是手机版还是电脑版呢。

侯茜茜 2025年09月07日 16:49:15
唉然后返回到手机桌面打开软件，来益盟操盘手股票分析软件，打开之后呢点击左上角的那个小人头像，然后再看一下头像下方是您的尾号47是是的尾号登录的吗？

侯茜茜 2025年09月07日 16:51:01
只能用三个股票是吧？

侯茜茜 2025年09月07日 17:06:16
啊这个功能我跟你讲它是咱们益盟23年的核心经典功能，这个功能呢在外面其他任何一家公司的股票分析软件里面都找不到跟咱们类似一样的功能，呀我这边详细教您一下，您认真看一下这个功能呢这上面有一个。

侯茜茜 2025年09月07日 17:29:48
全是收费嗯288。

侯茜茜 2025年09月07日 17:29:54
288您确定，啊因为像咱们这个软件的话，原价是1680一年的，相当于相当于想抢噢

侯茜茜 2025年09月07日 17:30:13
噢那相当于你抢到了咱们现实秒杀的一个活动，呀恭喜你啊哥，你想二百八二百八十八一年的时间，相当于一天平均算下来不到几毛钱，啊您现在的

侯茜茜 2025年09月07日 17:30:34
啊就是说啊这个工号啊你一定要填，为什么？呢您看我今天也花了这么长的时间去教你，啊像咱们这是版软件里面还有其他好用那些功能，呀后续咱们开通之后呢都是板。

侯茜茜 2025年09月07日 17:31:48
唉大哥您放心好了，咱们这个软件呢它就是包括我们车略预选时以及咱们5000多家的个股买卖点都是包含在内的。

侯茜茜 2025年09月07日 17:31:58
而且你今天开通半年之后，咱们也是相当于有缘分，嘛我再给给您送一套咱们益盟就是操盘手第一课，这个课程呢就是专门你在外面去听的话也是要花几千块钱的。

侯茜茜 2025年09月07日 17:32:21
讲咱们一些选股啊以及买卖的一些好的方法，其实您办理之后，呢我这边特彻底去给您申请下来，直播回放的话都是有的，您点进去操作办理一下。

侯茜茜 2025年09月07日 17:32:36
而且的话到时候我还会再再给您咱们送三个月的一个使用期，嘛

侯茜茜 2025年09月07日 17:32:54
咱们公司的话已经有23年的一个时间了，在国内股票收费排名的话也是第一的，咱们用户连续费率呢也是占到80%。

侯茜茜 2025年09月07日 17:33:30
那同样呢咱们今年真正的去花288去开通一年，咱们真正的去用一点，如果说咱们在用的过程当中，你觉得咱们软件对你来说帮助帮助不断的话，你想一下，您第一点用的不好，第，第二年还会花钱去用吗，那肯定也不可能再用的对不对？

侯茜茜 2025年09月07日 17:33:59
这个话就耽误您几分钟的时间就可以了，您点进去操作办理一下。"""

    # 提取销售话语
    sales_utterances = extract_sales_utterances(real_sales_text)
    
    print(f"📋 提取了 {len(sales_utterances)} 条销售话语")
    print("-" * 40)
    
    processor = ProcessProcessor()
    text_processor = TextProcessor()
    
    # 分析每条销售话语的详细检测过程
    print("🔍 详细检测过程分析：")
    print("-" * 50)
    
    total_money_asks = 0
    all_quotes = []
    
    for i, utterance in enumerate(sales_utterances, 1):
        print(f"\n{i}. 话语: {utterance}")
        
        # 测试单条话语
        single_test = {
            'content_analysis': {
                'sales_content': [utterance]
            }
        }
        
        single_result = processor._detect_money_ask(single_test)
        is_money_ask = single_result['count'] > 0
        
        # 详细分析这条话语
        print(f"   检测结果: {'✅ 要钱行为' if is_money_ask else '❌ 非要钱行为'}")
        
        # 手动检查是否包含关键词
        money_keywords = ['288', '1680', '收费', '开通', '办理', '花', '钱', '元', '免费', '付费', '会员', 'VIP']
        found_keywords = [kw for kw in money_keywords if kw in utterance]
        if found_keywords:
            print(f"   包含关键词: {found_keywords}")
        
        # 测试我们的检测函数
        contains_behavior = processor._contains_money_ask_behavior(utterance)
        print(f"   _contains_money_ask_behavior: {contains_behavior}")
        
        if is_money_ask:
            total_money_asks += 1
            if single_result['quotes']:
                all_quotes.extend(single_result['quotes'])
                print(f"   证据: {single_result['quotes'][0]}")
    
    # 总体检测结果
    print(f"\n📊 总体检测结果:")
    print(f"检测到要钱行为: {total_money_asks} 次")
    
    if all_quotes:
        print("\n📋 所有证据片段:")
        for i, quote in enumerate(all_quotes, 1):
            print(f"{i}. {quote}")
    
    # 手动标注的真实要钱行为
    print(f"\n🎯 预期要钱行为 (应该检测到的):")
    expected_money_asks = [
        "全是收费嗯288",
        "288您确定，啊因为像咱们这个软件的话，原价是1680一年的",
        "噢那相当于你抢到了咱们现实秒杀的一个活动，呀恭喜你啊哥，你想二百八二百八十八一年的时间",
        "后续咱们开通之后呢都是板",
        "而且你今天开通半年之后",
        "您点进去操作办理一下",
        "那同样呢咱们今年真正的去花288去开通一年",
        "这个话就耽误您几分钟的时间就可以了，您点进去操作办理一下"
    ]
    
    for expected in expected_money_asks:
        print(f"- {expected[:80]}{'...' if len(expected) > 80 else ''}")
    
    # 性能分析
    expected_count = len(expected_money_asks)
    print(f"\n📈 检测效果分析：")
    print(f"实际检测到: {total_money_asks} 次")
    print(f"预期应检测: {expected_count} 次")
    
    if total_money_asks > 0:
        # 估算准确率（这里简化处理）
        precision_estimate = min(total_money_asks, expected_count) / total_money_asks
        recall_estimate = min(total_money_asks, expected_count) / expected_count
        print(f"估计精确率: {precision_estimate:.1%}")
        print(f"估计召回率: {recall_estimate:.1%}")
    else:
        print("❌ 召回率: 0% (未检测到任何要钱行为)")
        print("🔧 需要调整检测逻辑")

def extract_sales_utterances(conversation_text):
    """从对话文本中提取销售人员的话语"""
    
    sales_utterances = []
    lines = conversation_text.split('\n')
    
    print(f"🔍 解析对话文本，共 {len(lines)} 行")
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
            
        print(f"第{i+1}行: {line[:50]}...")
        
        # 检查是否是销售人员说话（侯茜茜）
        if line.startswith('侯茜茜'):
            print(f"  -> 发现销售话语标识")
            
            # 下一行应该是实际内容
            if i + 1 < len(lines):
                content = lines[i + 1].strip()
                if content and len(content) > 8:
                    sales_utterances.append(content)
                    print(f"  -> 添加话语: {content[:50]}...")
                else:
                    print(f"  -> 下一行内容为空或太短: '{content}'")
            else:
                print(f"  -> 没有下一行内容")
            
            i += 2  # 跳过时间戳行和内容行
        elif line.startswith('客户'):
            print(f"  -> 客户话语，跳过")
            i += 2  # 跳过客户的时间戳和内容
        else:
            print(f"  -> 其他内容，跳过")
            i += 1
    
    print(f"📋 最终提取到 {len(sales_utterances)} 条销售话语")
    return sales_utterances

if __name__ == "__main__":
    asyncio.run(test_real_sales_conversation()) 