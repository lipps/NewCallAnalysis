"""数据模型和JSON Schema定义"""

from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field
from enum import Enum


class ValueRecognition(str, Enum):
    """客户价值认同度"""
    YES = "是"
    NO = "否"
    UNCLEAR = "不明"


class EvidenceHit(BaseModel):
    """证据命中模型"""
    hit: bool = Field(description="是否命中")
    evidence: str = Field(default="", description="证据片段")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="置信度")


class IcebreakModel(BaseModel):
    """破冰要点检测模型"""
    professional_identity: EvidenceHit = Field(description="专业身份")
    value_help: EvidenceHit = Field(description="帮助价值")
    time_notice: EvidenceHit = Field(description="占用时间说明")
    company_background: EvidenceHit = Field(description="腾讯投资/公司背景")
    free_teach: EvidenceHit = Field(description="免费讲解说明")
    refuse_reason: str = Field(default="", description="拒绝沟通原因")
    refuse_recover_count: int = Field(default=0, ge=0, description="应对拒绝动作次数")
    next_appointment: bool = Field(default=False, description="是否预约下次沟通")


class DeductionModel(BaseModel):
    """功能演绎要点检测模型"""
    bs_explained: EvidenceHit = Field(description="BS点讲解")
    period_resonance_explained: EvidenceHit = Field(description="周期/时段讲解")
    control_funds_explained: EvidenceHit = Field(description="控盘资金讲解")
    bubugao_explained: EvidenceHit = Field(description="步步高讲解")
    value_quantify_explained: EvidenceHit = Field(description="价值量化/实盘化演绎")
    customer_stock_explained: EvidenceHit = Field(description="客户自有股票讲解")


class ProcessModel(BaseModel):
    """过程指标统计模型"""
    explain_duration_min: float = Field(default=0.0, ge=0.0, description="讲解时长(分钟)")
    interaction_rounds_per_min: float = Field(default=0.0, ge=0.0, description="每分钟互动次数")
    deal_or_visit: bool = Field(default=False, description="是否成交/约访")
    total_words: int = Field(default=0, ge=0, description="总字数")
    sales_words: int = Field(default=0, ge=0, description="销售话语字数")
    customer_words: int = Field(default=0, ge=0, description="客户话语字数")


class CustomerModel(BaseModel):
    """客户侧结构化输出模型"""
    summary: str = Field(default="", description="客户总结")
    questions: List[str] = Field(default_factory=list, description="客户问题列表")
    value_recognition: ValueRecognition = Field(default=ValueRecognition.UNCLEAR, description="对软件价值的认同度")
    attitude_score: float = Field(default=0.0, ge=-1.0, le=1.0, description="客户态度评分(-1到1)")


class ActionExecution(BaseModel):
    """动作执行情况"""
    executed: bool = Field(description="是否执行")
    count: int = Field(default=0, ge=0, description="执行次数")
    evidence_list: List[str] = Field(default_factory=list, description="所有证据片段")


class ActionsModel(BaseModel):
    """标准动作执行情况模型"""
    # 破冰动作
    professional_identity: ActionExecution = Field(description="专业身份表明")
    value_help: ActionExecution = Field(description="帮助价值说明")
    time_notice: ActionExecution = Field(description="占用时间说明")
    company_background: ActionExecution = Field(description="公司背景介绍")
    free_teach: ActionExecution = Field(description="免费讲解说明")
    
    # 功能演绎动作
    bs_explained: ActionExecution = Field(description="BS点讲解")
    period_resonance_explained: ActionExecution = Field(description="周期/时段讲解")
    control_funds_explained: ActionExecution = Field(description="控盘资金讲解")
    bubugao_explained: ActionExecution = Field(description="步步高讲解")
    value_quantify_explained: ActionExecution = Field(description="价值量化演绎")
    customer_stock_explained: ActionExecution = Field(description="客户股票讲解")


class CallAnalysisResult(BaseModel):
    """通话分析结果完整模型"""
    call_id: str = Field(description="通话ID")
    customer_id: Optional[str] = Field(default=None, description="客户ID")
    sales_id: Optional[str] = Field(default=None, description="销售员ID")
    call_time: Optional[str] = Field(default=None, description="通话时间")
    
    # 四大分析模块
    icebreak: IcebreakModel = Field(description="破冰要点检测")
    演绎: DeductionModel = Field(description="功能演绎要点检测")
    process: ProcessModel = Field(description="过程指标统计")
    customer: CustomerModel = Field(description="客户侧结构化输出")
    actions: ActionsModel = Field(description="标准动作执行情况")
    
    # 元数据
    analysis_timestamp: str = Field(description="分析时间戳")
    model_version: str = Field(default="1.0", description="模型版本")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="整体置信度")


class CallInput(BaseModel):
    """通话输入模型"""
    call_id: str = Field(description="通话ID")
    transcript: str = Field(description="通话转写文本")
    customer_id: Optional[str] = Field(default=None, description="客户ID")
    sales_id: Optional[str] = Field(default=None, description="销售员ID")
    call_time: Optional[str] = Field(default=None, description="通话时间")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="附加元数据")


class BatchAnalysisInput(BaseModel):
    """批量分析输入模型"""
    calls: List[CallInput] = Field(description="通话列表")
    batch_id: str = Field(description="批次ID")
    priority: int = Field(default=1, ge=1, le=10, description="优先级")


class AnalysisConfig(BaseModel):
    """分析配置模型"""
    enable_vector_search: bool = Field(default=True, description="启用向量检索")
    enable_llm_validation: bool = Field(default=True, description="启用LLM验证")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="置信度阈值")
    max_evidence_length: int = Field(default=200, ge=50, le=1000, description="最大证据片段长度")
    language: str = Field(default="zh-CN", description="语言")


class QualityMetrics(BaseModel):
    """质量指标模型"""
    overall_score: float = Field(ge=0.0, le=100.0, description="综合评分")
    icebreak_score: float = Field(ge=0.0, le=100.0, description="破冰得分")
    deduction_score: float = Field(ge=0.0, le=100.0, description="演绎得分")
    interaction_score: float = Field(ge=0.0, le=100.0, description="互动得分")
    completion_rate: float = Field(ge=0.0, le=1.0, description="完成度")
    
    
# JSON Schema导出
CALL_ANALYSIS_SCHEMA = CallAnalysisResult.model_json_schema()