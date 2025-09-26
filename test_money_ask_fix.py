#!/usr/bin/env python3
"""测试要钱行为检测修复效果"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.processors.process_processor import ProcessProcessor

async def test_money_ask_detection():
    """测试要钱行为检测"""
    
    print("🧪 测试要钱行为检测修复效果")
    print("=" * 60)
    
    processor = ProcessProcessor()
    
    # 应该被识别为要钱行为的案例
    positive_cases = [
        "我们有不同的服务套餐，您可以先试用一下看效果",
        "VIP会员每年288元，功能更强大",
        "这个功能是收费的，不过效果很好",
        "建议您升级到专业版，功能更全面",
        "您可以先体验一下免费版本，然后考虑升级",
        "我们的付费服务包含更多功能",
        "现在开通VIP可以享受优惠价格",
        "免费会员每天只能看3只股票，升级后没有限制"
    ]
    
    # 不应该被识别为要钱行为的案例（之前的误报）
    negative_cases = [
        "您这个股票成本价买成多少呀",
        "下载注册了咱们益盟操盘手股票分析软件",
        "返回到手机桌面打开软件",
        "股价在一个大的下跌的蓝色区域",
        "那长期操作一只个股",
        "这个功能我跟您介绍一下",
        "您买的这只股票情况怎么样",
        "客户购买的股票成本较高"
    ]
    
    print("🟢 应该检测到的要钱行为：")
    print("-" * 40)
    
    for i, case in enumerate(positive_cases, 1):
        # 模拟销售内容
        processed_text = {
            'content_analysis': {
                'sales_content': [case]
            }
        }
        
        result = processor._detect_money_ask(processed_text)
        status = "✅ 检测到" if result['count'] > 0 else "❌ 未检测到"
        print(f"{i}. {status}: {case}")
        if result['quotes']:
            print(f"   证据: {result['quotes'][0]}")
        print()
    
    print("🔴 不应该检测到的要钱行为：")
    print("-" * 40)
    
    for i, case in enumerate(negative_cases, 1):
        # 模拟销售内容
        processed_text = {
            'content_analysis': {
                'sales_content': [case]
            }
        }
        
        result = processor._detect_money_ask(processed_text)
        status = "✅ 正确排除" if result['count'] == 0 else "❌ 误报"
        print(f"{i}. {status}: {case}")
        if result['quotes']:
            print(f"   误报证据: {result['quotes'][0]}")
        print()
    
    # 统计结果
    positive_detected = 0
    for case in positive_cases:
        processed_text = {'content_analysis': {'sales_content': [case]}}
        result = processor._detect_money_ask(processed_text)
        if result['count'] > 0:
            positive_detected += 1
    
    negative_excluded = 0
    for case in negative_cases:
        processed_text = {'content_analysis': {'sales_content': [case]}}
        result = processor._detect_money_ask(processed_text)
        if result['count'] == 0:
            negative_excluded += 1
    
    print("📊 检测结果统计：")
    print("=" * 40)
    print(f"真实要钱行为检测率: {positive_detected}/{len(positive_cases)} ({positive_detected/len(positive_cases)*100:.1f}%)")
    print(f"误报排除率: {negative_excluded}/{len(negative_cases)} ({negative_excluded/len(negative_cases)*100:.1f}%)")
    
    overall_accuracy = (positive_detected + negative_excluded) / (len(positive_cases) + len(negative_cases))
    print(f"整体准确率: {overall_accuracy*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(test_money_ask_detection())
