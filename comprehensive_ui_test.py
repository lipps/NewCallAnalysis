#!/usr/bin/env python3
"""全面测试UI接口的Python脚本"""

import requests
import json
from pprint import pprint

def test_comprehensive_ui_analysis():
    """测试包含多种销售要素的完整通话"""

    url = "http://localhost:8000/ui/analyze"
    headers = {"Content-Type": "application/json"}

    # 更全面的测试数据，包含多种销售要素
    call_data = {
        "call_id": "comprehensive_test_001",
        "transcript": """销售：您好，我是益盟操盘手的专员小李，很高兴为您服务。我们是腾讯投资的上市公司。
客户：你好，腾讯投资的公司？
销售：是的，我们为客户免费提供专业的股票分析服务。现在给您介绍一下我们的BS买卖点功能。
客户：这个BS点是什么意思？
销售：BS点是我们的核心技术，B代表买入信号，S代表卖出信号。根据历史数据，使用我们系统的客户平均提升18%的收益率。
客户：听起来不错，但我资金不多，只有几万块。
销售：没关系，几万块也可以很好地进行资金控制。我们还有步步高功能，可以帮您把握每一次上涨机会。
客户：需要付费吗？
销售：现在是免费体验期，您可以先试用看效果。
客户：好的，那我考虑一下。
销售：您现在主要关注哪些股票呢？我可以帮您分析一下。""",
        "customer_id": "customer_comprehensive_001",
        "sales_id": "sales_lijie_001",
        "call_time": "2024-01-15 14:30:00"
    }

    try:
        print("🚀 正在进行全面UI接口测试...")
        print(f"URL: {url}")
        print("-" * 80)

        response = requests.post(url, json=call_data, headers=headers, timeout=60)

        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ 全面测试成功!")

            # 详细验证各个模块
            output = result['output']

            print(f"\n📊 通话基本信息:")
            meta = output.get('meta', {})
            print(f"  - 通话ID: {meta.get('call_id')}")
            print(f"  - 客户ID: {meta.get('customer_id')}")
            print(f"  - 销售ID: {meta.get('sales_id')}")
            print(f"  - 通话时间: {meta.get('call_time')}")

            print(f"\n👤 客户侧分析:")
            customer = output.get('customer_side', {})
            print(f"  - 客户问题数: {len(customer.get('questions', []))}")
            print(f"  - 价值认知: {customer.get('value_recognition')}")
            if customer.get('questions'):
                print(f"  - 客户问题: {customer.get('questions')}")

            print(f"\n🎯 开场白分析:")
            opening = output.get('opening', {})
            for key, data in opening.items():
                status = "✅" if data.get('hit') else "❌"
                evidence_count = len(data.get('evidence', []))
                confidence = data.get('confidence', 0)
                print(f"  - {key}: {status} (证据数:{evidence_count}, 置信度:{confidence:.2f})")

                # 显示证据详情（前2条）
                if evidence_count > 0:
                    for i, evidence in enumerate(data.get('evidence', [])[:2]):
                        print(f"    └─ 证据{i+1}: idx={evidence.get('idx')}, quote='{evidence.get('quote', '')[:30]}...'")

            print(f"\n🔍 功能演绎分析:")
            demo = output.get('demo', {})
            for key, data in demo.items():
                status = "✅" if data.get('hit') else "❌"
                confidence = data.get('confidence', 0)
                print(f"  - {key}: {status} (置信度:{confidence:.2f})")

            print(f"\n📈 深度分析 (demo_more):")
            demo_more = output.get('demo_more', {})
            for key, data in demo_more.items():
                coverage_hit = data.get('coverage', {}).get('hit', False)
                depth_info = data.get('depth_effectiveness', {})
                depth = depth_info.get('depth', '无')
                effectiveness = depth_info.get('effectiveness_score', 0)

                status = "✅" if coverage_hit else "❌"
                print(f"  - {key}: {status} (深度:{depth}, 有效性:{effectiveness:.2f})")

            print(f"\n📊 通话指标:")
            metrics = output.get('metrics', {})
            print(f"  - 通话时长: {metrics.get('talk_time_min', 0):.1f}分钟")
            print(f"  - 每分钟交互: {metrics.get('interactions_per_min', 0):.1f}次")
            print(f"  - 成交或约访: {metrics.get('deal_or_visit', False)}")

            word_stats = metrics.get('word_stats', {})
            print(f"  - 总词数: {word_stats.get('total_words', 0)}")
            print(f"  - 销售话语占比: {word_stats.get('sales_ratio', 0):.1%}")

            print(f"\n🔧 适配器元信息:")
            adapter_meta = result.get('_adapter_metadata', {})
            print(f"  - 适配器版本: {adapter_meta.get('adapter_version')}")
            print(f"  - 转换时间: {adapter_meta.get('conversion_timestamp')}")
            print(f"  - 包含处理文本: {adapter_meta.get('has_processed_text')}")

            # 验证数据结构完整性
            print(f"\n🔍 数据结构验证:")
            required_sections = ['customer_side', 'opening', 'demo', 'demo_more', 'metrics', 'meta']
            for section in required_sections:
                has_section = section in output
                print(f"  - {section}: {'✅' if has_section else '❌'}")

            return result
        else:
            print(f"❌ 测试失败: {response.status_code}")
            print(f"错误详情: {response.text}")
            return None

    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return None

def test_ui_stats():
    """测试UI统计接口"""
    print(f"\n" + "="*50)
    print("🔧 测试UI统计接口...")

    try:
        response = requests.get("http://localhost:8000/ui/analyze/stats")
        if response.status_code == 200:
            stats = response.json()
            print("✅ 统计接口正常")

            adapter_cache = stats['stats']['adapter_cache']
            enhancer_cache = stats['stats']['evidence_enhancer_cache']

            print(f"  - 适配器缓存: {adapter_cache['cache_size']}/{adapter_cache['max_size']} (命中率: {adapter_cache['hit_rate']:.1%})")
            print(f"  - 证据增强缓存: {enhancer_cache['cache_size']}/{enhancer_cache['max_size']} (命中率: {enhancer_cache['hit_rate']:.1%})")
            print(f"  - 适配器版本: {stats['stats']['adapter_version']}")
        else:
            print(f"❌ 统计接口失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 统计接口异常: {e}")

if __name__ == "__main__":
    # 全面测试
    result = test_comprehensive_ui_analysis()

    # 统计接口测试
    test_ui_stats()

    if result:
        print(f"\n" + "="*50)
        print("🎉 全面测试完成! UI适配器系统工作正常")