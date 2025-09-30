# UI适配器快速开始指南

## 🚀 5分钟快速上手

### 1. 启动系统

```bash
# 启动API服务器
python main.py server --host 0.0.0.0 --port 8000

# 或使用uvicorn直接启动
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### 2. 测试UI接口

```bash
# 使用curl测试
curl -X POST "http://localhost:8000/ui/analyze" \
     -H "Content-Type: application/json" \
     -d '{
       "call_id": "quick_test",
       "transcript": "销售：您好，我是益盟操盘手的专员小李，很高兴为您服务。客户：你好。销售：我们是腾讯投资的上市公司，有BS买卖点功能。客户：听起来不错，有什么效果？销售：根据历史数据，客户平均提升18%收益率。",
       "customer_id": "test_customer",
       "sales_id": "test_sales"
     }'
```

### 3. 查看返回结果

UI接口将返回完整的结构化数据，包括：
- 客户问题和态度分析
- 开场白各要素命中情况
- 功能演绎深度分析
- 通话指标统计
- 结构化证据片段

---

## 📋 实际使用示例

### Python客户端示例

```python
import requests
import json
from pprint import pprint

def analyze_call_for_ui(call_data):
    """使用UI接口分析通话"""

    url = "http://localhost:8000/ui/analyze"
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=call_data, headers=headers)
        response.raise_for_status()

        ui_result = response.json()

        print("=== UI分析结果 ===")
        print(f"通话ID: {ui_result['output']['meta']['call_id']}")
        print(f"分析时间: {ui_result['_adapter_metadata']['conversion_timestamp']}")

        # 客户侧分析
        customer = ui_result['output']['customer_side']
        print(f"\n📊 客户分析:")
        print(f"  客户问题数: {len(customer['questions'])}")
        print(f"  价值认知: {customer['value_recognition']}")
        print(f"  客户问题: {customer['questions']}")

        # 开场白分析
        opening = ui_result['output']['opening']
        print(f"\n🎯 开场白分析:")
        for key, data in opening.items():
            status = "✅" if data['hit'] else "❌"
            evidence_count = len(data['evidence'])
            print(f"  {key}: {status} (证据数:{evidence_count})")

        # 功能演绎深度分析
        demo_more = ui_result['output']['demo_more']
        print(f"\n🔍 功能演绎深度:")
        for key, data in demo_more.items():
            if data['coverage']['hit']:
                depth = data['depth_effectiveness']['depth']
                score = data['depth_effectiveness']['effectiveness_score']
                print(f"  {key}: {depth} (得分:{score:.2f})")

        # 通话指标
        metrics = ui_result['output']['metrics']
        print(f"\n📈 通话指标:")
        print(f"  通话时长: {metrics['talk_time_min']:.1f}分钟")
        print(f"  互动频率: {metrics['interactions_per_min']:.1f}次/分钟")
        print(f"  成交意向: {'是' if metrics['deal_or_visit'] else '否'}")

        return ui_result

    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        return None

# 使用示例
call_data = {
    "call_id": "demo_call_001",
    "transcript": """销售：您好，我是益盟操盘手的专员小李，很高兴为您服务。
客户：你好。
销售：是这样的，我们是腾讯投资的上市公司，专门为股民提供专业的分析服务。耽误您两分钟时间，我免费给您讲解一下我们的核心功能。
客户：好的，你说吧。
销售：我们的主要功能是买卖点提示，B点代表最佳买入时机，S点代表卖出信号。另外还有主力控盘资金指标。
客户：听起来不错，有实际效果吗？
销售：根据历史回测数据，使用我们信号的客户平均提升了18%的收益率。咱们看看您现在持有什么股票？
客户：我持有招商银行和中国平安。
销售：好的，我们来看看这两只股票的买卖点情况。我们还有步步高VIP专属功能。
客户：这个功能收费吗？
销售：我们有不同的服务套餐，您可以先试用一下看效果。
客户：可以，我想了解一下。""",
    "customer_id": "customer_demo_001",
    "sales_id": "sales_demo_001"
}

result = analyze_call_for_ui(call_data)
```

### JavaScript客户端示例

```javascript
async function analyzeCallForUI(callData) {
    const url = 'http://localhost:8000/ui/analyze';

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(callData)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const uiResult = await response.json();

        console.log('=== UI分析结果 ===');
        console.log(`通话ID: ${uiResult.output.meta.call_id}`);

        // 处理客户侧数据
        const customer = uiResult.output.customer_side;
        console.log(`客户问题数: ${customer.questions.length}`);
        console.log(`价值认知: ${customer.value_recognition}`);

        // 处理开场白数据
        const opening = uiResult.output.opening;
        Object.entries(opening).forEach(([key, data]) => {
            const status = data.hit ? '✅' : '❌';
            console.log(`${key}: ${status} (证据数:${data.evidence.length})`);
        });

        return uiResult;

    } catch (error) {
        console.error('❌ 分析失败:', error);
        return null;
    }
}

// 使用示例
const callData = {
    call_id: "js_demo_001",
    transcript: "销售：您好，我是益盟操盘手专员...",
    customer_id: "customer_js_001",
    sales_id: "sales_js_001"
};

analyzeCallForUI(callData);
```

---

## 🎯 UI数据使用指南

### 1. 客户侧数据处理

```python
def process_customer_data(customer_side):
    """处理客户侧数据"""

    # 客户问题分析
    questions = customer_side['questions']
    if questions:
        print(f"客户提出了 {len(questions)} 个问题:")
        for i, question in enumerate(questions, 1):
            print(f"  {i}. {question}")

    # 价值认知状态
    recognition = customer_side['value_recognition']
    recognition_map = {
        'YES': '✅ 认同产品价值',
        'NO': '❌ 不认同产品价值',
        'UNCLEAR': '❓ 态度不明确'
    }
    print(f"价值认知: {recognition_map.get(recognition, recognition)}")

    # 客户总结
    summary = customer_side['summary']
    if summary:
        print(f"客户总结: {summary}")
```

### 2. 证据数据可视化

```python
def visualize_evidence(evidence_list):
    """可视化证据数据"""

    for evidence in evidence_list:
        confidence_bar = "█" * int(evidence['confidence'] * 10)
        match_type_emoji = {
            'exact': '🎯',
            'keyword': '🔍',
            'fuzzy': '🌟',
            'fallback': '🛡️'
        }

        emoji = match_type_emoji.get(evidence['match_type'], '❓')

        print(f"{emoji} [{evidence['ts']}] 置信度: {confidence_bar} ({evidence['confidence']:.2f})")
        print(f"   引用: {evidence['quote'][:100]}...")
        print(f"   匹配类型: {evidence['match_type']}")
        print()
```

### 3. 深度分析数据展示

```python
def display_depth_analysis(demo_more):
    """展示深度分析数据"""

    depth_colors = {
        '无': '⚫',
        '浅显': '🟡',
        '适中': '🟠',
        '深入': '🔴'
    }

    print("🔍 功能演绎深度分析:")

    for feature, data in demo_more.items():
        if data['coverage']['hit']:
            depth = data['depth_effectiveness']['depth']
            score = data['depth_effectiveness']['effectiveness_score']

            color = depth_colors.get(depth, '❓')
            bar = "▰" * int(score * 10) + "▱" * (10 - int(score * 10))

            print(f"{color} {feature}:")
            print(f"   深度: {depth}")
            print(f"   效果: {bar} ({score:.2f})")
            print(f"   分析: {data['depth_effectiveness']['analysis']}")
            print()
```

### 4. 统计数据仪表板

```python
def create_dashboard(ui_result):
    """创建统计仪表板"""

    output = ui_result['output']

    print("=" * 50)
    print("📊 通话分析仪表板")
    print("=" * 50)

    # 基本信息
    meta = output['meta']
    print(f"🆔 通话ID: {meta['call_id']}")
    print(f"👤 客户ID: {meta['customer_id']}")
    print(f"🎯 销售ID: {meta['sales_id']}")
    print()

    # 关键指标
    metrics = output['metrics']
    customer = output['customer_side']

    print("📈 关键指标:")
    print(f"  ⏱️  通话时长: {metrics['talk_time_min']:.1f} 分钟")
    print(f"  💬 互动频率: {metrics['interactions_per_min']:.1f} 次/分钟")
    print(f"  🎯 成交意向: {'是' if metrics['deal_or_visit'] else '否'}")
    print(f"  ❓ 客户问题: {len(customer['questions'])} 个")
    print(f"  💰 要钱次数: {output['standard_actions']['money_ask']['count']} 次")
    print()

    # 开场白完成度
    opening = output['opening']
    opening_hits = sum(1 for data in opening.values() if data['hit'])
    opening_rate = opening_hits / len(opening) * 100

    print(f"🎬 开场白完成度: {opening_hits}/{len(opening)} ({opening_rate:.1f}%)")

    # 功能演绎完成度
    demo = output['demo']
    demo_hits = sum(1 for data in demo.values() if data['hit'])
    demo_rate = demo_hits / len(demo) * 100

    print(f"🎯 功能演绎完成度: {demo_hits}/{len(demo)} ({demo_rate:.1f}%)")

    # 拒绝处理
    rejects = output['rejects']
    print(f"🛡️  拒绝处理次数: {rejects['handle_objection_count']} 次")

    print("=" * 50)
```

---

## 🔧 高级配置示例

### 自定义适配器配置

```python
from src.adapters import UIAdapter, EvidenceEnhancer
from src.config.settings import settings

# 高性能配置
def create_high_performance_adapter():
    """创建高性能适配器"""

    evidence_enhancer = EvidenceEnhancer(
        max_quote_length=150,      # 较短引用提高速度
        cache_size=1000           # 大缓存提高命中率
    )

    ui_adapter = UIAdapter(
        evidence_enhancer=evidence_enhancer,
        enable_cache=True,
        cache_size=500            # 大UI缓存
    )

    return ui_adapter

# 低内存配置
def create_low_memory_adapter():
    """创建低内存适配器"""

    evidence_enhancer = EvidenceEnhancer(
        max_quote_length=100,      # 更短引用
        cache_size=50             # 小缓存
    )

    ui_adapter = UIAdapter(
        evidence_enhancer=evidence_enhancer,
        enable_cache=True,
        cache_size=50             # 小UI缓存
    )

    return ui_adapter

# 调试配置
def create_debug_adapter():
    """创建调试适配器"""

    evidence_enhancer = EvidenceEnhancer(
        max_quote_length=300,      # 长引用便于调试
        cache_size=10             # 小缓存便于测试
    )

    ui_adapter = UIAdapter(
        evidence_enhancer=evidence_enhancer,
        enable_cache=False,       # 禁用缓存便于调试
        cache_size=10
    )

    return ui_adapter
```

### 批量处理示例

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def batch_analyze_for_ui(call_list, max_workers=3):
    """批量UI分析"""

    ui_adapter = create_high_performance_adapter()

    async def analyze_single(call_data):
        """分析单个通话"""
        try:
            # 这里应该调用实际的工作流
            # result = await workflow.execute(call_input, config)
            # processed_text = workflow.get_last_processed_text()
            # return ui_adapter.convert_to_ui_format(result, processed_text)

            # 模拟API调用
            import requests
            response = requests.post('http://localhost:8000/ui/analyze', json=call_data)
            return response.json()

        except Exception as e:
            print(f"❌ 分析失败 {call_data['call_id']}: {e}")
            return None

    # 控制并发数量
    semaphore = asyncio.Semaphore(max_workers)

    async def analyze_with_semaphore(call_data):
        async with semaphore:
            return await analyze_single(call_data)

    # 批量执行
    tasks = [analyze_with_semaphore(call_data) for call_data in call_list]
    results = await asyncio.gather(*tasks)

    # 过滤成功结果
    successful_results = [r for r in results if r is not None]

    print(f"✅ 批量分析完成: {len(successful_results)}/{len(call_list)}")

    return successful_results

# 使用示例
call_list = [
    {"call_id": f"batch_{i}", "transcript": f"测试通话 {i}..."}
    for i in range(5)
]

# asyncio.run(batch_analyze_for_ui(call_list))
```

---

## 🚨 故障排查快速指南

### 1. 常见问题检查清单

```bash
# 1. 检查服务是否启动
curl -X GET "http://localhost:8000/docs"

# 2. 检查原有API是否正常
curl -X GET "http://localhost:8000/health" || echo "健康检查端点可能不存在"

# 3. 测试UI统计接口
curl -X GET "http://localhost:8000/ui/analyze/stats"

# 4. 测试简单UI分析
curl -X POST "http://localhost:8000/ui/analyze" \
     -H "Content-Type: application/json" \
     -d '{"call_id":"test","transcript":"销售：您好。客户：你好。"}'
```

### 2. Python诊断脚本

```python
import requests
import json

def diagnose_ui_system():
    """诊断UI系统状态"""

    base_url = "http://localhost:8000"

    print("🔍 UI适配器系统诊断")
    print("=" * 40)

    # 1. 检查服务可达性
    try:
        response = requests.get(f"{base_url}/docs", timeout=5)
        print("✅ 服务可达")
    except:
        print("❌ 服务不可达，请检查服务是否启动")
        return

    # 2. 检查UI统计接口
    try:
        response = requests.get(f"{base_url}/ui/analyze/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            print("✅ UI统计接口正常")
            print(f"   适配器版本: {stats['stats']['adapter_version']}")
            print(f"   缓存状态: {stats['stats']['adapter_cache']['cache_enabled']}")
        else:
            print(f"❌ UI统计接口异常: {response.status_code}")
    except Exception as e:
        print(f"❌ UI统计接口错误: {e}")

    # 3. 测试简单分析
    test_data = {
        "call_id": "diagnostic_test",
        "transcript": "销售：您好，我是专员。客户：你好。"
    }

    try:
        response = requests.post(f"{base_url}/ui/analyze", json=test_data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            print("✅ UI分析接口正常")

            # 检查关键字段
            output = result.get('output', {})
            if 'customer_side' in output and 'opening' in output and 'demo' in output:
                print("✅ 输出格式正确")
            else:
                print("⚠️  输出格式不完整")

        else:
            print(f"❌ UI分析接口异常: {response.status_code}")
            print(f"   错误信息: {response.text[:200]}...")

    except Exception as e:
        print(f"❌ UI分析接口错误: {e}")

    print("\n诊断完成！")

if __name__ == "__main__":
    diagnose_ui_system()
```

---

## 📈 性能监控

### 监控脚本示例

```python
import time
import requests
from datetime import datetime

def monitor_ui_performance(duration_minutes=5, interval_seconds=30):
    """监控UI性能"""

    print(f"🔍 开始监控UI性能 ({duration_minutes}分钟)")
    print("=" * 50)

    end_time = time.time() + (duration_minutes * 60)
    test_data = {
        "call_id": f"monitor_{int(time.time())}",
        "transcript": "销售：您好，我是益盟操盘手专员小李。客户：你好。销售：我们是腾讯投资的公司。"
    }

    while time.time() < end_time:
        start_time = time.time()

        try:
            # 测试UI接口
            response = requests.post(
                "http://localhost:8000/ui/analyze",
                json=test_data,
                timeout=10
            )

            response_time = (time.time() - start_time) * 1000  # ms

            if response.status_code == 200:
                print(f"✅ {datetime.now().strftime('%H:%M:%S')} - 响应时间: {response_time:.0f}ms")

                # 获取统计信息
                stats_response = requests.get("http://localhost:8000/ui/analyze/stats")
                if stats_response.status_code == 200:
                    stats = stats_response.json()['stats']
                    hit_rate = stats['adapter_cache']['hit_rate']
                    print(f"   缓存命中率: {hit_rate:.2%}")
            else:
                print(f"❌ {datetime.now().strftime('%H:%M:%S')} - 错误: {response.status_code}")

        except Exception as e:
            print(f"❌ {datetime.now().strftime('%H:%M:%S')} - 异常: {e}")

        time.sleep(interval_seconds)

    print("监控结束")

if __name__ == "__main__":
    monitor_ui_performance()
```

通过这个快速开始指南，您可以在几分钟内开始使用UI适配器系统，并掌握各种高级用法和最佳实践。