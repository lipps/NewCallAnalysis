# UI适配器API文档

## 📋 概述

UI适配器系统为现有的销售通话质检系统提供UI界面友好的数据格式。该系统采用适配器模式，完全零侵入现有架构，仅通过数据格式转换为前端UI提供结构化的分析结果。

### 核心特性
- **零侵入设计**: 不影响现有API和分析流程
- **结构化证据**: 将简单文本证据转换为包含索引、时间戳的结构化格式
- **深度分析**: 提供演绎内容的深度有效性分析
- **高性能缓存**: 多级缓存优化响应速度
- **完整降级**: 多层错误处理确保系统稳定

---

## 🚀 API端点

### 1. UI专用分析接口

#### `POST /ui/analyze`

执行通话分析并返回UI友好的格式化结果。

**请求格式**:
```json
{
    "call_id": "string",
    "transcript": "string",
    "customer_id": "string (可选)",
    "sales_id": "string (可选)",
    "call_time": "string (可选)"
}
```

**响应格式**:
```json
{
    "output": {
        "customer_side": {
            "questions": ["string", "..."],
            "summary": "string",
            "value_recognition": "YES|NO|UNCLEAR"
        },
        "standard_actions": {
            "money_ask": {
                "count": "integer",
                "quotes": ["string", "..."],
                "total_attempts": "integer"
            },
            "action_summary": {
                "total_executed": "integer",
                "execution_rate": "float",
                "key_actions": ["string", "..."]
            }
        },
        "opening": {
            "professional_identity": {
                "hit": "boolean",
                "evidence": [
                    {
                        "idx": "integer",
                        "ts": "string",
                        "quote": "string",
                        "match_type": "exact|keyword|fuzzy|fallback",
                        "confidence": "float"
                    }
                ],
                "confidence": "float",
                "evidence_source": "string"
            },
            "value_help": { "同上结构" },
            "time_notice": { "同上结构" },
            "tencent_invest": { "同上结构" },
            "free_teach": { "同上结构" }
        },
        "meta": {
            "call_id": "string",
            "customer_id": "string",
            "sales_id": "string",
            "call_time": "string",
            "analysis_timestamp": "string"
        },
        "metrics": {
            "talk_time_min": "float",
            "interactions_per_min": "float",
            "deal_or_visit": "boolean",
            "word_stats": {
                "total_words": "integer",
                "sales_words": "integer",
                "customer_words": "integer",
                "sales_ratio": "float"
            }
        },
        "rejects": {
            "handle_objection_count": "integer",
            "handling_strategies": [
                {
                    "strategy": "string",
                    "quote": "string"
                }
            ],
            "rejection_reasons": [
                {
                    "type": "string",
                    "quote": "string"
                }
            ],
            "next_appointment": "boolean",
            "rejection_kpi": "object",
            "handling_kpi": "object"
        },
        "demo": {
            "bs_explained": { "同opening结构" },
            "period_resonance_explained": { "同opening结构" },
            "control_funds_explained": { "同opening结构" },
            "bubugao_explained": { "同opening结构" },
            "value_quantify_explained": { "同opening结构" },
            "customer_stock_explained": { "同opening结构" }
        },
        "demo_more": {
            "bs_explained": {
                "coverage": { "同opening结构" },
                "depth_effectiveness": {
                    "depth": "无|浅显|适中|深入",
                    "effectiveness_score": "float",
                    "analysis": "string"
                }
            },
            "period_resonance_explained": { "同上结构" },
            "control_funds_explained": { "同上结构" },
            "bubugao_explained": { "同上结构" },
            "value_quantify_explained": { "同上结构" }
        }
    },
    "_adapter_metadata": {
        "conversion_timestamp": "string",
        "adapter_version": "string",
        "source_call_id": "string",
        "has_processed_text": "boolean"
    }
}
```

**请求示例**:
```bash
curl -X POST "http://localhost:8000/ui/analyze" \
     -H "Content-Type: application/json" \
     -d '{
       "call_id": "demo_001",
       "transcript": "销售：您好，我是益盟操盘手的专员小李。客户：你好。销售：我们是腾讯投资的上市公司，有BS买卖点功能。客户：听起来不错。",
       "customer_id": "customer_001",
       "sales_id": "sales_001"
     }'
```

**状态码**:
- `200`: 分析成功
- `400`: 请求参数错误
- `500`: 系统内部错误或UI适配器不可用

---

### 2. UI分析统计接口

#### `GET /ui/analyze/stats`

获取UI分析系统的运行统计信息。

**响应格式**:
```json
{
    "status": "ok",
    "stats": {
        "adapter_cache": {
            "cache_enabled": "boolean",
            "cache_size": "integer",
            "max_size": "integer",
            "hits": "integer",
            "misses": "integer",
            "hit_rate": "float",
            "total_requests": "integer"
        },
        "evidence_enhancer_cache": {
            "cache_size": "integer",
            "max_size": "integer",
            "hits": "integer",
            "misses": "integer",
            "hit_rate": "float",
            "total_requests": "integer"
        },
        "adapter_version": "string"
    },
    "timestamp": "string"
}
```

**请求示例**:
```bash
curl -X GET "http://localhost:8000/ui/analyze/stats"
```

---

## 📊 数据格式说明

### 证据结构 (Evidence)

UI适配器将简单的证据字符串转换为结构化格式：

```json
{
    "idx": 0,           // 对话索引
    "ts": "10:30:01",   // 时间戳
    "quote": "您好，我是益盟操盘手专员", // 引用片段
    "match_type": "exact",  // 匹配类型
    "confidence": 0.9   // 置信度
}
```

**匹配类型说明**:
- `exact`: 精确文本匹配
- `keyword`: 关键词匹配
- `fuzzy`: 模糊相似度匹配
- `fallback`: 降级处理结果
- `simple_fallback`: 最简单降级处理

### 深度有效性分析 (Depth Effectiveness)

对演绎内容提供深度分析：

```json
{
    "depth": "适中",           // 深度级别: 无|浅显|适中|深入
    "effectiveness_score": 0.8, // 有效性评分 (0-1)
    "analysis": "BS点讲解深度适中，有效性评分0.8" // 分析描述
}
```

---

## ⚙️ 配置参数

系统通过环境变量或配置文件进行配置：

### UI相关配置

```bash
# 证据片段最大长度
UI__UI_EVIDENCE_MAX_LENGTH=200

# 启用适配器缓存
UI__UI_CACHE_ENABLED=True

# 适配器缓存大小
UI__UI_CACHE_SIZE=100

# 启用证据增强功能
UI__UI_ENABLE_EVIDENCE_ENHANCEMENT=True

# 证据匹配阈值
UI__UI_EVIDENCE_MATCH_THRESHOLD=0.3

# 启用降级处理
UI__UI_FALLBACK_ENABLED=True
```

### 性能调优参数

```python
# 代码配置示例
from src.adapters import UIAdapter, EvidenceEnhancer

# 自定义配置
evidence_enhancer = EvidenceEnhancer(
    max_quote_length=150,    # 引用片段最大长度
    cache_size=200           # 缓存大小
)

ui_adapter = UIAdapter(
    evidence_enhancer=evidence_enhancer,
    enable_cache=True,       # 启用缓存
    cache_size=150           # UI适配器缓存大小
)
```

---

## 🔄 使用流程

### 1. 标准使用流程

```python
# 1. 发送分析请求
response = requests.post('/ui/analyze', json={
    'call_id': 'call_001',
    'transcript': '通话内容...'
})

# 2. 获取UI格式结果
ui_result = response.json()

# 3. 使用各模块数据
customer_questions = ui_result['output']['customer_side']['questions']
opening_data = ui_result['output']['opening']
demo_analysis = ui_result['output']['demo_more']
```

### 2. 错误处理

```python
try:
    response = requests.post('/ui/analyze', json=call_data)
    response.raise_for_status()

    ui_result = response.json()

    # 检查是否使用了降级处理
    if ui_result.get('_adapter_metadata', {}).get('conversion_status') == 'fallback':
        print("警告：使用了降级处理")

except requests.exceptions.RequestException as e:
    print(f"API请求失败: {e}")
except KeyError as e:
    print(f"数据格式错误: {e}")
```

---

## 📈 性能特征

### 响应时间

| 场景 | 期望响应时间 |
|------|------------|
| 标准通话 (5分钟) | < 500ms |
| 长通话 (15分钟) | < 800ms |
| 批量处理 (10通话) | < 5s |

### 缓存效果

- **适配器缓存命中率**: 通常 >60%
- **证据增强缓存命中率**: 通常 >40%
- **内存占用增加**: < 10%

### 并发能力

- **支持并发数**: 与原系统相同
- **缓存线程安全**: 完全支持
- **性能影响**: 增加 <20% 响应时间

---

## 🛠️ 开发集成

### FastAPI集成

```python
from fastapi import FastAPI, Depends
from src.adapters import UIAdapter, EvidenceEnhancer
from src.workflows.simplified_workflow import SimpleCallAnalysisWorkflow

app = FastAPI()

@app.post("/ui/analyze")
async def analyze_for_ui(
    call_input: CallInput,
    workflow: SimpleCallAnalysisWorkflow = Depends(get_workflow)
):
    # 执行分析
    result = await workflow.execute(call_input, config)

    # 获取处理文本
    processed_text = workflow.get_last_processed_text()

    # UI格式转换
    evidence_enhancer = EvidenceEnhancer()
    ui_adapter = UIAdapter(evidence_enhancer=evidence_enhancer)
    ui_result = ui_adapter.convert_to_ui_format(result, processed_text)

    return ui_result
```

### 直接使用适配器

```python
from src.adapters import UIAdapter, EvidenceEnhancer

# 创建适配器
evidence_enhancer = EvidenceEnhancer()
ui_adapter = UIAdapter(evidence_enhancer=evidence_enhancer)

# 转换分析结果
ui_result = ui_adapter.convert_to_ui_format(
    analysis_result,    # CallAnalysisResult对象
    processed_text      # 处理后的文本数据
)

# 获取统计信息
stats = ui_adapter.get_conversion_stats()
print(f"缓存命中率: {stats['adapter_cache']['hit_rate']:.2%}")
```

---

## 🚨 错误处理

### 常见错误类型

#### 1. 适配器不可用 (HTTP 503)
```json
{
    "detail": "UI适配器不可用"
}
```

**解决方案**: 检查适配器模块是否正确安装

#### 2. 转换失败 (HTTP 500)
```json
{
    "detail": "UI分析失败: [错误详情]"
}
```

**解决方案**: 系统会自动使用降级处理，检查日志获取详细信息

#### 3. 参数验证失败 (HTTP 400)
```json
{
    "detail": "通话转写文本不能为空"
}
```

**解决方案**: 检查请求参数格式和必填字段

### 降级处理机制

系统具有多层降级处理：

1. **证据增强失败**: 返回简化证据格式
2. **部分模块失败**: 返回可用模块数据 + 空默认值
3. **完全转换失败**: 返回基础结构 + fallback标记

---

## 📝 最佳实践

### 1. 性能优化

```python
# 推荐配置
evidence_enhancer = EvidenceEnhancer(
    max_quote_length=200,     # 适中的引用长度
    cache_size=500           # 较大缓存提高命中率
)

ui_adapter = UIAdapter(
    evidence_enhancer=evidence_enhancer,
    enable_cache=True,       # 启用缓存
    cache_size=200          # 适配器缓存
)
```

### 2. 错误监控

```python
# 监控转换状态
def check_conversion_quality(ui_result):
    metadata = ui_result.get('_adapter_metadata', {})

    if metadata.get('conversion_status') == 'fallback':
        logger.warning(f"UI转换使用降级处理: {metadata.get('source_call_id')}")

    # 检查缓存效果
    if hasattr(ui_adapter, 'get_cache_stats'):
        stats = ui_adapter.get_cache_stats()
        if stats['hit_rate'] < 0.3:
            logger.info(f"缓存命中率较低: {stats['hit_rate']:.2%}")
```

### 3. 资源管理

```python
# 定期清理缓存
def cleanup_caches():
    ui_adapter.clear_cache()
    evidence_enhancer.clear_cache()

# 获取系统统计
def get_system_health():
    stats = ui_adapter.get_conversion_stats()
    return {
        'cache_efficiency': stats['adapter_cache']['hit_rate'],
        'total_conversions': stats['adapter_cache']['total_requests'],
        'system_status': 'healthy' if stats['adapter_cache']['hit_rate'] > 0.2 else 'degraded'
    }
```

---

## 🔧 故障排查

### 常见问题及解决方案

#### Q: UI接口返回500错误
**A**:
1. 检查适配器模块是否正确导入
2. 查看系统日志中的详细错误信息
3. 验证原有分析系统是否正常工作

#### Q: 证据增强效果不理想
**A**:
1. 调整 `ui_evidence_match_threshold` 参数
2. 检查 `processed_text` 是否包含完整的对话数据
3. 启用详细日志查看匹配过程

#### Q: 响应时间过长
**A**:
1. 检查缓存配置和命中率
2. 调整 `max_quote_length` 减少处理时间
3. 考虑增加并发处理能力

#### Q: 缓存命中率低
**A**:
1. 增加 `cache_size` 配置
2. 检查输入数据的重复性
3. 分析缓存键生成策略是否合理

---

## 📋 版本信息

- **当前版本**: 1.0.0
- **兼容性**: 与现有系统完全兼容
- **最低要求**: Python 3.8+, FastAPI 0.104.0+
- **推荐配置**: 4GB+ RAM, 2+ CPU cores

---

## 📞 技术支持

如需技术支持，请提供：
1. 错误日志和堆栈跟踪
2. 请求数据示例
3. 系统配置信息
4. 预期结果与实际结果对比

通过完整的API文档，开发团队可以快速集成和使用UI适配器系统，同时确保生产环境的稳定运行。