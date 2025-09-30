# 销售功能讲解深度与有效性检测需求文档

## 📋 项目概述

### 功能名称
销售功能讲解深度与有效性检测（Advanced Function Explanation Analysis）

### 功能背景
在现有销售通话质检系统基础上，增加针对四个核心销售功能（BS点、周期共振、控盘资金、步步高）的深度讲解质量分析，采用"功能覆盖 + 深度与有效性"的两层检测机制，提供更精准的销售表现评估。

### 业务价值
- 提升销售功能讲解的质量和有效性
- 量化评估销售人员的专业能力
- 优化客户沟通效果，提高成交转化率
- 为销售培训提供精准的改进方向

## 🎯 核心检测对象

### 1. BS点功能
**关键词识别**：
- 基础词汇：BS点、B点、S点、买卖点、买点、卖点、操盘线
- 扩展词汇：趋势信号、买入信号、卖出信号、趋势指标、交易信号、提示

**深度信号（BS点特有）**：
- `mention_trends`：是否提及趋势概念
- `explain_B`：是否解释B点含义
- `explain_S`：是否解释S点含义

### 2. 周期共振功能
**关键词识别**：
- 基础词汇：周期共振、看大做小、看长做短
- 扩展词汇：周期、共振、周线、月线、以大带小、短期、中期、长期、多周期、B点共振、上涨波段

### 3. 控盘资金功能
**关键词识别**：
- 基础词汇：控盘资金、控盘资金VIP、筹码分布、资金流向
- 扩展词汇：大资金、机构资金、庄家、净流入、净流出、主力、有控盘能力、红色面积代表主力资金净流入

**深度信号（控盘资金特有）**：
- `mention_13d_param`：是否提及13日参数设置
- `mention_inflow_outflow`：是否说明净流入/净流出
- `mention_main_force`：是否提及主力资金概念

### 4. 步步高功能
**关键词识别**：
- 基础词汇：步步高、步步高VIP、活跃线、活跃指数
- 扩展词汇：海面线、能量柱、紫柱、黄柱、橙色、量在价前、量能、步步高波段战法、红线含义

**深度信号（步步高特有）**：
- `mention_volume`：是否提及量能概念
- `mention_redline`：是否解释红线含义
- `mention_wave_strategy`：是否提及波段战法

## 🔍 两层检测机制

### 第一层：功能覆盖检测

**判定逻辑**：
- 仅出现关键词但没有明确讲解 → **不命中**
- 仅由客户提问或引出 → **不命中**
- 必须是agent明确讲解/解释/演绎该功能 → **命中**

**输出结构**：
```json
"coverage": {
  "hit": true/false,
  "evidence": [
    {"idx": 序号, "ts": [开始时间, 结束时间] | null, "quote": "agent原文"}
  ]
}
```

### 第二层：深度与有效性检测（仅对覆盖=有的功能）

#### 深度评估维度

**1. 好处/价值讲解**
- `explained_benefit`: 是否讲清楚功能的好处和价值

**2. 深度信号检测**
- `usage_scenario`: 使用场景（如何用/何时用/针对谁）
- `customer_value`: 客户价值（收益、痛点缓解、风险降低、效率提升）
- `comparison_or_relevance`: 对比/相关性（与其他方案/指标的对比或联动）

**3. 功能特定信号**
- 根据不同功能设置特定的深度信号检测项

#### 客户反应分析

**反应类型**：
- `已确认`：正面回应/同意
- `提问`：澄清问题/延展问题  
- `误解`：表述与功能不符，需要纠正
- `忽略`：无明显回应或转移话题
- `无`：未检测到明显反应

**反应证据**：
```json
"customer_reaction": {
  "type": "已确认|提问|误解|忽略|无",
  "evidence": [
    {"idx": 序号, "ts": [开始时间, 结束时间] | null, "quote": "customer原文"}
  ]
}
```

#### 深度分级

**分级标准**：
- `N/A`：功能覆盖=无
- `浅显`：仅点名功能，未深入讲解
- `适中`：包含基本讲解和部分深度信号
- `充分`：全面讲解，包含多个深度信号

#### 有效性评分

**评分规则 (0-2分)**：
- `0分`：未提及或客户忽略
- `1分`：覆盖=有且讲解浅显 或 客户无反应
- `2分`：覆盖=有且讲解充分 且 存在客户反应

## 📊 标准输出格式

### JSON Schema

```json
{
  "bs_explained": {
    "coverage": {
      "hit": boolean,
      "evidence": [
        {"idx": number, "ts": [number, number] | null, "quote": string}
      ]
    },
    "depth_effectiveness": {
      "depth": "浅显|适中|充分|N/A",
      "explained_benefit": boolean,
      "signals": {
        "usage_scenario": boolean,
        "customer_value": boolean,
        "comparison_or_relevance": boolean,
        "bs_facets": {
          "mention_trends": boolean,
          "explain_B": boolean,
          "explain_S": boolean
        }
      },
      "customer_reaction": {
        "type": "已确认|提问|误解|忽略|无",
        "evidence": [
          {"idx": number, "ts": [number, number] | null, "quote": string}
        ]
      },
      "effectiveness_score": number
    }
  },
  "period_resonance_explained": {
    "coverage": {...},
    "depth_effectiveness": {...}
  },
  "control_funds_explained": {
    "coverage": {...},
    "depth_effectiveness": {
      "depth": "浅显|适中|充分|N/A",
      "explained_benefit": boolean,
      "signals": {
        "usage_scenario": boolean,
        "customer_value": boolean,
        "comparison_or_relevance": boolean,
        "control_funds_facets": {
          "mention_13d_param": boolean,
          "mention_inflow_outflow": boolean,
          "mention_main_force": boolean
        }
      },
      "customer_reaction": {...},
      "effectiveness_score": number
    }
  },
  "bubugao_explained": {
    "coverage": {...},
    "depth_effectiveness": {
      "depth": "浅显|适中|充分|N/A", 
      "explained_benefit": boolean,
      "signals": {
        "usage_scenario": boolean,
        "customer_value": boolean,
        "comparison_or_relevance": boolean,
        "bubugao_facets": {
          "mention_volume": boolean,
          "mention_redline": boolean,
          "mention_wave_strategy": boolean
        }
      },
      "customer_reaction": {...},
      "effectiveness_score": number
    }
  }
}
```

## 📋 输入处理规则

### 输入格式支持
- **纯文本对话**：自动按行解析，推断说话人
- **结构化转写**：支持包含idx、ts、speaker等字段的JSON格式

### 自动处理规则
- **话语序号(idx)**：若未提供，按出现顺序从0开始编号
- **时间戳(ts)**：若未提供，置为null
- **说话人识别**：以"agent/销售"、"customer/客户"标识；无法识别时根据上下文推断

### 等价表达处理
系统需要识别以下等价表达（示例，非穷举）：
- "没买到行情" ≈ "踏空"
- "红色代表资金进来" ≈ "红色面积主力净流入"
- "看大做小" ≈ "周期共振/看长做短"
- "主力资金在流入/流出" ≈ "净流入/净流出"
- "量在价前/量能柱子/红线含义" ≈ "步步高"

## 🎯 实现要点

### 技术架构建议

**1. 数据模型扩展**
- 扩展现有的`DeductionModel`，增加深度与有效性字段
- 新增`FunctionExplanationModel`用于该功能的输出

**2. 处理器设计**
- 创建`FunctionExplanationProcessor`
- 继承现有的`BaseProcessor`架构
- 集成规则引擎、向量引擎、LLM引擎

**3. 工作流集成**
- 在现有`CallAnalysisWorkflow`中添加新节点
- 支持并行处理以提升性能

### 核心算法流程

```
1. 输入预处理 → 话语解析、说话人识别
2. 功能覆盖检测 → 关键词匹配 + 语义分析 + LLM验证
3. 深度信号检测 → 多维度信号提取
4. 客户反应分析 → 反应类型分类 + 证据提取
5. 综合评分 → 深度分级 + 有效性评分
6. JSON格式输出 → 严格格式验证
```

### 质量保证

**1. 证据溯源**
- 所有判定必须有可追溯的原文证据
- 证据需包含准确的idx和ts信息

**2. 一致性检验**
- coverage.hit=false时，depth必须为"N/A"
- effectiveness_score与depth/customer_reaction的一致性

**3. 输出验证**
- 严格JSON Schema验证
- 必填字段完整性检查

## 🧪 测试场景设计

### 场景1：基础功能覆盖
**输入**：agent简单提及"这个B点代表买入信号"
**预期**：coverage.hit=true, depth="浅显", effectiveness_score=1

### 场景2：深度讲解+客户反应
**输入**：agent详细讲解BS点原理+使用场景，customer提问"这个准确率怎么样？"
**预期**：coverage.hit=true, depth="充分", customer_reaction.type="提问", effectiveness_score=2

### 场景3：客户引出但agent未讲解
**输入**：customer问"什么是BS点？"，agent回答"一会儿再说"
**预期**：coverage.hit=false, depth="N/A", effectiveness_score=0

### 场景4：多功能混合讲解
**输入**：agent同时讲解BS点和周期共振
**预期**：两个功能都应该被检测到并独立评分

### 场景5：等价表达识别
**输入**：agent说"看大做小，长周期判断趋势"
**预期**：period_resonance_explained.coverage.hit=true

## 📈 性能指标

### 准确性指标
- 功能覆盖检测准确率 ≥ 95%
- 深度分级一致性 ≥ 90%
- 客户反应识别准确率 ≥ 85%

### 性能指标  
- 单通话处理时间 ≤ 3秒
- 批量处理并发能力 ≥ 10个/并发
- 内存占用 ≤ 500MB

### 鲁棒性指标
- 输入格式容错能力
- 异常情况处理完整性
- JSON输出格式严格性 100%

## 🔧 配置管理

### 规则配置
```python
FUNCTION_EXPLANATION_RULES = {
    "bs_explained": {
        "keywords": ["BS点", "B点", "S点", "买卖点", ...],
        "patterns": [r"[BS]点.{0,20}(信号|提示)", ...],
        "depth_signals": {
            "trends": ["趋势", "上涨", "下跌"],
            "explain_b": ["B点", "买入", "买进"],
            "explain_s": ["S点", "卖出", "卖掉"]
        }
    },
    # ... 其他功能配置
}
```

### 评分权重配置
```python
SCORING_WEIGHTS = {
    "depth_weight": 0.6,        # 深度权重
    "reaction_weight": 0.4,     # 客户反应权重
    "benefit_threshold": 0.5,   # 好处讲解阈值
    "signal_threshold": 2       # 深度信号最低数量
}
```

## 📝 交付物清单

### 代码交付
- [ ] `FunctionExplanationProcessor`处理器
- [ ] `FunctionExplanationModel`数据模型
- [ ] 工作流集成代码
- [ ] 配置文件更新

### 文档交付
- [ ] API接口文档
- [ ] 配置说明文档
- [ ] 测试用例文档
- [ ] 部署指南

### 测试交付
- [ ] 单元测试用例
- [ ] 集成测试用例
- [ ] 性能测试报告
- [ ] 用户验收测试

---

**版本**: v1.0  
**创建日期**: 2025-09-26  
**文档状态**: 需求分析完成，待开发实现
