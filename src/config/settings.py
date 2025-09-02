"""系统配置管理"""

import os
from typing import Dict, Any, List
from pydantic_settings import BaseSettings
from pydantic import Field


class DatabaseSettings(BaseSettings):
    """数据库配置"""
    chroma_persist_directory: str = Field(default="./data/chroma")
    collection_name: str = Field(default="call_analysis")
    
    
class ModelSettings(BaseSettings):
    """模型配置"""
    openai_api_key: str = Field(default="")
    openai_base_url: str = Field(default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    embedding_model: str = Field(default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    llm_model: str = Field(default="deepseek-r1")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, ge=100, le=4000)


class ProcessingSettings(BaseSettings):
    """处理配置"""
    max_workers: int = Field(default=4, ge=1, le=16)
    batch_size: int = Field(default=32, ge=1, le=128)
    cache_size: int = Field(default=1000, ge=100, le=10000)
    timeout_seconds: int = Field(default=300, ge=30, le=3600)


class LoggingSettings(BaseSettings):
    """日志配置"""
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="./logs/app.log")
    log_format: str = Field(default="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} | {message}")


class ServerSettings(BaseSettings):
    """服务器配置"""
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1000, le=65535)
    debug: bool = Field(default=False)
    reload: bool = Field(default=False)


class AppSettings(BaseSettings):
    """应用配置"""
    app_name: str = Field(default="销售通话质检系统")
    version: str = Field(default="1.0.0")
    description: str = Field(default="基于AI的销售通话质检与分析系统")
    
    # 子配置
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    model: ModelSettings = Field(default_factory=ModelSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    
    # 统一的模型配置 - 合并 Config 类的设置
    model_config = {
        "extra": "allow",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_nested_delimiter": "__"
    }


# 规则配置
DETECTION_RULES = {
    "icebreak": {
        "professional_identity": {
            "keywords": [
                "我是益盟操盘手", "专员", "老师", "顾问", "分析师", 
                "投资顾问", "股票老师", "操盘手", "专业分析师"
            ],
            "patterns": [
                r"我是.{0,10}(益盟|操盘手|专员|老师|顾问|分析师)",
                r"(专业|资深).{0,5}(投资|股票|分析)",
            ]
        },
        "value_help": {
            "keywords": [
                "帮您", "帮助您", "为您", "给您", "解决问题", "带来收益",
                "提升收益", "把握机会", "规避风险", "获利", "赚钱"
            ],
            "patterns": [
                r"(帮您|帮助您|为您|给您).{0,20}(解决|提升|把握|获得|赚)",
                r"让您.{0,15}(收益|获利|赚钱|盈利)"
            ]
        },
        "time_notice": {
            "keywords": [
                "耽误您", "占用您", "打扰您", "几分钟", "两分钟", "三分钟", 
                "一会儿", "不会太久", "很快"
            ],
            "patterns": [
                r"(耽误|占用|打扰).{0,5}您.{0,10}(分钟|时间)",
                r"(几|两|三|五).{0,2}分钟"
            ]
        },
        "company_background": {
            "keywords": [
                "腾讯投资", "上市公司", "大公司", "知名企业", "行业领先",
                "专业机构", "权威平台", "品牌"
            ],
            "patterns": [
                r"腾讯.{0,5}投资.{0,5}(的|上市|公司)",
                r"(上市|知名|大型).{0,5}公司"
            ]
        },
        "free_teach": {
            "keywords": [
                "免费", "不收费", "不要钱", "义务", "公益", "免费讲解",
                "免费分析", "免费指导", "免费服务"
            ],
            "patterns": [
                r"免费.{0,10}(讲解|分析|指导|服务|教学)",
                r"(不收费|不要钱|义务).{0,5}(讲|教|指导)"
            ]
        }
    },
    "deduction": {
        "bs_explained": {
            "keywords": [
                "B点", "S点", "买卖点", "操盘线", "趋势信号", "买入信号", 
                "卖出信号", "买点", "卖点", "交易信号"
            ],
            "patterns": [
                r"[BS]点.{0,20}(信号|提示|买|卖)",
                r"(买卖点|操盘线|趋势信号|交易信号)"
            ]
        },
        "period_resonance_explained": {
            "keywords": [
                "周期", "共振", "时间级别", "日线", "周线", "月线", 
                "短期", "中期", "长期", "多周期", "时段"
            ],
            "patterns": [
                r"(周期|共振).{0,15}(分析|研判|配合)",
                r"(日|周|月)线.{0,10}(配合|共振|分析)",
                r"(短|中|长)期.{0,10}(趋势|周期)"
            ]
        },
        "control_funds_explained": {
            "keywords": [
                "主力资金", "控盘资金", "筹码分布", "资金流向", "大资金",
                "机构资金", "庄家", "主力", "热钱"
            ],
            "patterns": [
                r"(主力|控盘|机构).{0,5}资金",
                r"筹码.{0,10}(分布|集中|分散)",
                r"资金.{0,10}(流向|进出|动向)"
            ]
        },
        "bubugao_explained": {
            "keywords": [
                "步步高", "VIP", "专属指标", "高级功能", "付费功能",
                "会员功能", "特色指标"
            ],
            "patterns": [
                r"步步高.{0,20}(功能|指标|信号)",
                r"VIP.{0,10}(专属|功能|指标)",
                r"(会员|付费).{0,10}(功能|指标)"
            ]
        },
        "value_quantify_explained": {
            "keywords": [
                "量化价值", "实盘", "真实案例", "历史回测", "收益率",
                "成功率", "胜率", "盈亏比", "实际效果", "数据证明"
            ],
            "patterns": [
                r"(实盘|真实).{0,10}(案例|效果|收益)",
                r"(成功率|胜率|收益率).{0,5}\d+%",
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

# 全局设置实例
settings = AppSettings()