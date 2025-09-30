"""系统配置管理"""

import os
from typing import Dict, Any, List
from pydantic_settings import BaseSettings
from pydantic import Field


class DatabaseSettings(BaseSettings):
    """数据库配置"""
    chroma_persist_directory: str = Field(default="./data/chroma")
    collection_name: str = Field(default="call_analysis")
    USE_NEBULA: bool = Field(default=False)


class ModelSettings(BaseSettings):
    """模型配置"""
    openai_api_key: str = Field(default="")
    openai_base_url: str = Field(default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    embedding_model: str = Field(default="./models/paraphrase-multilingual-MiniLM-L12-v2")
    llm_model: str = Field(default="deepseek-v3.1")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, ge=100, le=4000)


class ProcessingSettings(BaseSettings):
    """处理配置"""
    max_workers: int = Field(default=4, ge=1, le=16)
    batch_size: int = Field(default=32, ge=1, le=128)
    cache_size: int = Field(default=1000, ge=100, le=10000)
    timeout_seconds: int = Field(default=300, ge=30, le=3600)


class ServerSettings(BaseSettings):
    """服务器配置"""
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1000, le=65535)
    debug: bool = Field(default=False)
    reload: bool = Field(default=False)


# 新增痛点量化相关配置
PAIN_POINT_DETECTION_RULES = {
    "loss": {
        "keywords": [
            "亏损", "亏了", "损失", "套牢", "被套", "赔钱", "亏本",
            "缩水", "蒸发", "血亏", "巨亏", "深套", "腰斩"
        ],
        "quantification_patterns": [
            r"亏(了|损)?(\d+\.?\d*)([万千])?",
            r"损失(\d+\.?\d*)([万千])?",
            r"套(了|牢)?(\d+\.?\d*)([万千])?",
            r"跌(了|去)?(\d+\.?\d*)([万千个]点|%)",
        ],
        "severity_keywords": {
            "轻微": ["小亏", "小损失", "轻微亏损"],
            "中等": ["亏损", "套牢", "被套"],
            "严重": ["巨亏", "血亏", "深套", "腰斩", "爆仓"]
        }
    },
    "miss_opportunity": {
        "keywords": [
            "踏空", "错过", "没买到", "没上车", "看着涨", "眼睁睁",
            "后悔", "早知道", "没抓住", "失去机会"
        ],
        "quantification_patterns": [
            r"错过(\d+\.?\d*)([万千])?收益",
            r"没赚到(\d+\.?\d*)([万千])?",
            r"涨了(\d+\.?\d*)([万千个]点|%)",
        ]
    },
    "chase_high": {
        "keywords": [
            "追高", "高位", "山顶", "接盘", "站岗", "买在高点",
            "追涨", "冲动买入", "FOMO"
        ],
        "quantification_patterns": [
            r"(\d+\.?\d*)([万千])?买在高点",
            r"高位买入(\d+\.?\d*)([万千])?",
        ]
    },
    "panic_sell": {
        "keywords": [
            "割肉", "恐慌", "止损", "忍痛卖出", "低位卖出",
            "抛售", "清仓", "斩仓", "认栽"
        ],
        "quantification_patterns": [
            r"(\d+\.?\d*)([万千])?割肉",
            r"止损(\d+\.?\d*)([万千])?",
        ]
    }
}

# 量化提取正则表达式
QUANTIFICATION_EXTRACTORS = {
    "amount": [
        r"(\d+\.?\d*)万",
        r"(\d+\.?\d*)千", 
        r"(\d+\.?\d*)块",
        r"(\d+\.?\d*)元"
    ],
    "frequency": [
        r"(\d+)次",
        r"(\d+)回",
        r"(\d+)遍"
    ],
    "ratio": [
        r"(\d+\.?\d*)%",
        r"(\d+\.?\d*)个点",
        r"跌了(\d+\.?\d*)成"
    ]
}

# 痛点量化配置
class PainPointSettings(BaseSettings):
    """痛点量化配置"""
    detection_rules: Dict[str, Any] = Field(default_factory=lambda: PAIN_POINT_DETECTION_RULES)
    quantification_extractors: Dict[str, List[str]] = Field(default_factory=lambda: QUANTIFICATION_EXTRACTORS)
    
    # 痛点量化阈值配置
    confidence_threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="痛点检测置信度阈值")
    severity_thresholds: Dict[str, Dict[str, float]] = Field(
        default_factory=lambda: {
            "loss": {
                "low": 0.1,     # 轻微损失
                "medium": 0.3,   # 中等损失
                "high": 0.6      # 严重损失
            },
            "miss_opportunity": {
                "low": 0.1,      # 小机会
                "medium": 0.3,   # 中等机会
                "high": 0.6      # 重大机会
            }
        },
        description="不同痛点类型的严重程度阈值"
    )
    
    # 量化权重配置
    quantification_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "amount": 0.4,       # 金额权重
            "frequency": 0.2,     # 频次权重
            "ratio": 0.3,         # 比例权重
            "severity": 0.1       # 严重程度权重
        },
        description="不同量化维度的权重配置"
    )


class UISettings(BaseSettings):
    """UI适配器配置"""
    ui_evidence_max_length: int = Field(default=200, ge=50, le=1000, description="UI证据片段最大长度")
    ui_cache_enabled: bool = Field(default=True, description="启用UI适配器缓存")
    ui_cache_size: int = Field(default=100, ge=10, le=1000, description="UI适配器缓存大小")
    ui_enable_evidence_enhancement: bool = Field(default=True, description="启用证据增强功能")
    ui_evidence_match_threshold: float = Field(default=0.3, ge=0.1, le=0.9, description="证据匹配阈值")
    ui_fallback_enabled: bool = Field(default=True, description="启用降级处理")


class LoggingSettings(BaseSettings):
    """日志配置"""
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="./logs/app.log")
    log_format: str = Field(default="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} | {message}")

# 规则配置
DETECTION_RULES = {
    "icebreak": {
        "professional_identity": {
            "keywords": [
                "我是益盟操盘手", "专员", "老师", "顾问", "分析师", "业务员", "益盟客服",
                "投资顾问", "股票老师", "操盘手", "客服", "工作人员", "专业分析师"
            ],
            "patterns": [
                r"我是.{0,10}(益盟|操盘手|专员|老师|顾问|分析师)",
                r"(这边|我们这边|我这边).{0,6}(益盟|操盘手|客服|专员|老师|顾问)",
                r"(专业|资深).{0,5}(投资|股票|分析)",
                r"(来自|打电话).{0,10}(益盟|操盘手|客服中心)",
            ]
        },
        "value_help": {
            "keywords": [
                "帮您", "帮助您", "为您", "给您", "解决问题", "带来收益",
                "提升收益", "把握机会", "规避风险", "获利", "赚钱", "教你",
                "讲解功能", "指导使用", "带您使用", "使用说明", "教学"
            ],
            "patterns": [
                r"(帮您|帮助您|为您|给您).{0,20}(解决|提升|把握|获得|赚)",
                r"(讲解|指导|教学|带您|教你).{0,12}(功能|使用|操作)",
                r"让您.{0,15}(收益|获利|赚钱|盈利)"
            ]
        },
        "time_notice": {
            "keywords": [
                "耽误您", "占用您", "打扰您", "几分钟", "两分钟", "三分钟",
                "一会儿", "不会太久", "不耽误您时间", "简单说两句", "占用您一点时间", "一分钟/片刻/稍微", "很快"
            ],
            "patterns": [
                r"(耽误|占用|打扰).{0,5}您.{0,10}(分钟|时间)",
                r"(先|我)简单(说|介绍|讲)几句",
                r"(不?耽误|占用).{0,6}(您)?.{0,6}(一点|片刻|一会|一下|稍微)",
                r"(几|两|三|五).{0,2}分钟"
            ]
        },
        "company_background": {
            "keywords": [
                "腾讯投资", "大公司", "知名企业", "行业领先",
                "专业机构", "权威平台", "互联网大厂", "背景背书", "正规机构","品牌"
            ],
            "patterns": [
                r"腾讯.{0,5}投资.{0,5}(的|上市|公司)",
                r"(腾讯|互联网|大型|知名).{0,6}(投资|背景|背书|平台)",
                r"(知名|大型).{0,5}公司"
            ]
        },
        "free_teach": {
            "keywords": [
                "免费", "不收费", "不要钱", "义务", "公益", "免费讲解", "免费体验",
                "免费分析", "免费指导", "免费使用权", "永久免费", "免费服务"
            ],
            "patterns": [
                r"免费.{0,10}(讲解|分析|指导|服务|教学)",
                r"免费.{0,8}(使用|体验|权限|试用)",
                r"(不收费|不要钱|义务).{0,5}(讲|教|指导)"
            ]
        }
    },
    "deduction": {
        "bs_explained": {
            "keywords": [
                "B点", "S点", "买卖点", "操盘线", "趋势信号", "买入信号",
                "卖出信号", "买点", "卖点", "BS点", "趋势指标", "交易信号"
            ],
            "patterns": [
                r"[BS]点.{0,20}(信号|提示|买|卖)",
                r"(买卖点|操盘线|趋势信号|交易信号)"
            ]
        },
        "period_resonance_explained": {
            "keywords": [
                "周期", "共振", "看大做小", "周期共振", "周线", "月线", "以大带小",
                "短期", "中期", "长期", "多周期", "B点共振", "上涨波段", "看长做短"
            ],
            "patterns": [
                r"(周期|共振).{0,15}(分析|研判|配合)",
                r"(日|周|月)线.{0,10}(配合|共振|分析)",
                r"(多|跨|不同)周期.{0,6}(共振|配合|同向|对齐)",
                r"(短|中|长)期.{0,10}(趋势|周期)"
            ]
        },
        "control_funds_explained": {
            "keywords": [
                "控盘资金(VIP)", "控盘资金", "筹码分布", "资金流向", "大资金",
                "机构资金", "庄家", "净流入", "净流出", "控盘资金VIP"
            ],
            "patterns": [
                r"(控盘|机构).{0,5}资金",
                r"筹码.{0,10}(分布|集中|分散)",
                r"资金.{0,10}(流向|进出|动向)"
            ]
        },
        "bubugao_explained": {
            "keywords": [
                "步步高", "步步高VIP", "活跃线", "活跃指数", "海面线",
                "能量柱", "紫柱", "黄柱", "橙色"
            ],
            "patterns": [
                r"步步高.{0,20}(功能|指标|信号)",
                r"步步高VIP.{0,10}(专属|功能|指标)"
            ]
        },
        "value_quantify_explained": {
            "keywords": [
                "量化价值", "实盘", "真实案例", "历史回测", "收益率",
                "提升收益", "赚钱", "跑赢", "提高胜率", "真实效果",
                "成功率", "胜率", "盈亏比", "实际效果", "收益不错"
            ],
            "patterns": [
                r"(实盘|真实).{0,10}(案例|效果|收益)",
                r"(成功率|胜率|收益率).{0,5}\d+%",
                r"(实际|真实|客户).{0,8}(效果|反馈|表现|收益)",
                r"(提升|提高).{0,6}(收益|胜率|命中|成功率)",
                r"(验证|对比|回看|跑赢).{0,10}(大盘|指数|市场)",
                r"(历史|过往).{0,10}(数据|表现|收益)"
            ]
        },
        "customer_stock_explained": {
            "keywords": [
                "您的股票", "您持有的", "咱们看看", "分析一下", "您的持仓",
                "这只股票", "您买的", "您关注的"
            ],
            "patterns": [
                r"(您的|您持有的|您买的).{0,10}股票",
                r"(咱们|我们).{0,5}(看|分析).{0,5}(您的|这只)",
                r"您.{0,5}(持仓|关注的).{0,10}股票"
            ]
        }
    }
}

# 客户拒绝/抗拒识别 - 正则配置（可业务侧按需扩展/调整）
REJECTION_PATTERNS = {
    "无需求/已解决": r"(不需要|不用|用不到|已经(有|解决)|自己(会|弄)|不考虑)",
    "忙没空/时间冲突": r"(忙|没空|不方便|稍后|改天|等(一会|下次)|开会|在路上|驾车|吃饭|上班|上课|带孩子)",
    "不信任/警惕": r"(骗子|诈骗|骗人|不相信|别打了|骚扰|打扰|拉黑|举报)",
    "情绪负向/抱怨/要投诉": r"(投诉|打扰|骚扰|烦|受不了|生气|别再.*打)",
    "已卸载/不再使用产品": r"(卸载|删(掉|了)|不用了|取消(了)?|不再使用|停用)",
    "要求改为其他渠道（加微信/发资料/邮件）": r"(加(微信|vx|qq)|发(资料|短信|邮件|邮箱)|公众号|二维码)",
    "价格/费用顾虑": r"(太贵|多少钱|价格|费用|收费|贵|没钱|买不起)"
}

# 销售应对策略识别 - 正则配置
HANDLING_PATTERNS = {
    "共情/确认": r"(理解|明白|能理解|抱歉|不好意思|感谢|体谅)",
    "需求确认/提问": r"(方便(说|问)|能简单(说|聊)|您现在.*情况|具体.*情况|为什么|原因|想了解哪)",
    "价值重申": r"(我们(的)?(功能|价值|优势|收益|帮|提升|省时)|可以帮您|对您有帮助|效果|案例|数据|对比|验证过)",
    "备选时间": r"(什么时候方便|明天|后天|下午|晚上|周[一二三四五六日天]|再联系|约个时间|稍后|一会|改天)",
    "社会证明": r"(腾讯投资|上市公司|很多用户|客户|案例|成功率|口碑|业内|平台|背书|大厂)",
    "改约渠道": r"(加(微信|vx)|发(资料|短信|邮件)|二维码|公众号)",
    "继续推进/成交请求": r"(试用|体验|现在给您开通|先开通|先注册|办理|下单|购买|成交)"
}

# 批量处理相关配置
class BatchProcessingSettings(BaseSettings):
    """批量处理设置"""
    batch_max_files: int = Field(default=20, ge=1, le=50, description="每批次最大文件数")
    batch_max_calls: int = Field(default=2000, ge=1, le=10000, description="每批次最大通话数")
    batch_max_file_size_mb: int = Field(default=200, ge=1, le=1000, description="单文件最大大小(MB)")
    batch_max_concurrency: int = Field(default=3, ge=1, le=10, description="最大并发处理文件数")
    batch_result_storage_path: str = Field(default="./batch_results", description="批量结果存储路径")
    batch_result_retention_hours: int = Field(default=24, ge=1, le=168, description="结果保留时长(小时)")
    batch_enable_progress_tracking: bool = Field(default=True, description="启用进度跟踪")
    batch_enable_auto_cleanup: bool = Field(default=True, description="启用自动清理过期结果")


# 更新应用设置，包含批量处理配置
class AppSettings(BaseSettings):
    """应用配置"""
    app_name: str = Field(default="销售通话质检系统")
    version: str = Field(default="1.1.0")  # 升级版本号
    description: str = Field(default="基于AI的销售通话质检与分析系统 - 支持批量文件处理")

    # 子配置
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    model: ModelSettings = Field(default_factory=ModelSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    pain_point: PainPointSettings = Field(default_factory=PainPointSettings)
    batch_processing: BatchProcessingSettings = Field(default_factory=BatchProcessingSettings)
    ui: UISettings = Field(default_factory=UISettings)

    # 统一的模型配置 - 合并 Config 类的设置
    model_config = {
        "extra": "allow",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_nested_delimiter": "__"
    }

    CUSTOMER_PROBING_PROMPT: str = """
    你是一个通话分析专家。请分析以下通话记录，判断坐席是否考察了客户的个人情况。
    考察客户情况包括但不限于询问或提及：
    1. 仓位、资金量、持股情况。
    2. 投资风格、经验、风险偏好。
    3. 投资周期（长线/短线）。
    4. 验证客户是否理解或掌握公司教授的投资方法（如战法、BS买卖点、步步高、周期共振等）。

    如果判断为是，请回答'YES'并提供关键证据。如果不是，请回答'NO'。
    通话记录：
    ---
    {transcript}
    ---
    """


# 全局设置实例
settings = AppSettings()
