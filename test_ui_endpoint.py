#!/usr/bin/env python3
"""测试UI接口的Python脚本"""

import requests
import json
from pprint import pprint

def test_ui_analyze():
    """测试UI分析接口"""

    url = "http://localhost:8000/ui/analyze"
    headers = {"Content-Type": "application/json"}

    # 测试数据
    call_data = {
        "call_id": "quick_test",
        "transcript": "销售：您好，我是益盟操盘手的专员小李，很高兴为您服务。客户：你好。销售：我们是腾讯投资的上市公司，有BS买卖点功能。客户：听起来不错，有什么效果？销售：根据历史数据，客户平均提升18%收益率。",
        "customer_id": "test_customer",
        "sales_id": "test_sales"
    }

    try:
        print("🚀 正在测试UI分析接口...")
        print(f"URL: {url}")
        print(f"数据: {json.dumps(call_data, ensure_ascii=False, indent=2)}")
        print("-" * 50)

        response = requests.post(url, json=call_data, headers=headers, timeout=60)

        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")

        if response.status_code == 200:
            result = response.json()
            print("✅ 请求成功!")
            print(f"响应数据结构:")

            # 显示主要结构
            if 'output' in result:
                output = result['output']
                print(f"  - meta: call_id={output.get('meta', {}).get('call_id')}")
                print(f"  - customer_side: questions_count={len(output.get('customer_side', {}).get('questions', []))}")
                print(f"  - opening: {list(output.get('opening', {}).keys())}")
                print(f"  - demo_more: {list(output.get('demo_more', {}).keys())}")

            if '_adapter_metadata' in result:
                metadata = result['_adapter_metadata']
                print(f"  - adapter_metadata: version={metadata.get('adapter_version')}")

            return result
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"错误详情: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求异常: {e}")
        return None
    except Exception as e:
        print(f"❌ 其他异常: {e}")
        return None

if __name__ == "__main__":
    result = test_ui_analyze()
    if result:
        print("\n" + "="*50)
        print("完整响应 (前200字符):")
        print(json.dumps(result, ensure_ascii=False, indent=2)[:200] + "...")