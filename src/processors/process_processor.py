"""过程指标统计处理器"""

from typing import Dict, List, Any, Optional
import re
from datetime import datetime, timedelta
from ..models.schemas import ProcessModel, AnalysisConfig
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ProcessProcessor:
    """过程指标统计处理器"""
    
    def __init__(self):
        pass
        
    async def analyze(self, 
                     processed_text: Dict[str, Any],
                     config: AnalysisConfig) -> ProcessModel:
        """分析过程指标"""
        
        try:
            logger.info("开始过程指标统计")
            
            # 获取基本统计信息
            statistics = processed_text.get('statistics', {})
            dialogues = processed_text.get('dialogues', [])
            content_analysis = processed_text.get('content_analysis', {})
            
            # 计算讲解时长
            explain_duration = self._calculate_explain_duration(dialogues, statistics)
            
            # 计算互动频率
            interaction_frequency = self._calculate_interaction_frequency(dialogues, explain_duration)
            
            # 检测成交或约访
            deal_or_visit = self._detect_deal_or_visit(processed_text)
            
            # 计算词数统计
            word_stats = self._calculate_word_statistics(content_analysis)

            # 识别“要钱行为”
            money_ask = self._detect_money_ask(processed_text)
            
            # 构建结果
            result = ProcessModel(
                explain_duration_min=explain_duration,
                interaction_rounds_per_min=interaction_frequency,
                deal_or_visit=deal_or_visit,
                total_words=word_stats['total_words'],
                sales_words=word_stats['sales_words'],
                customer_words=word_stats['customer_words'],
                money_ask_count=money_ask['count'],
                money_ask_quotes=money_ask['quotes']
            )
            
            logger.info(f"过程指标统计完成，讲解时长: {explain_duration:.1f}分钟")
            
            return result
            
        except Exception as e:
            logger.error(f"过程指标统计失败: {e}")
            raise
    
    def _calculate_explain_duration(self, 
                                   dialogues: List[Dict[str, Any]],
                                   statistics: Dict[str, Any]) -> float:
        """计算讲解时长"""
        
        try:
            # 优先使用统计信息中的估算时长
            if 'estimated_duration_minutes' in statistics:
                duration = statistics['estimated_duration_minutes']
                if duration > 0:
                    return duration
            
            # 如果有时间戳，使用时间戳计算
            timestamps = [d.get('timestamp') for d in dialogues if d.get('timestamp')]
            if len(timestamps) >= 2:
                try:
                    start_time = datetime.strptime(timestamps[0], '%H:%M:%S')
                    end_time = datetime.strptime(timestamps[-1], '%H:%M:%S')
                    duration = end_time - start_time
                    if duration.total_seconds() < 0:  # 跨天处理
                        duration += timedelta(days=1)
                    return duration.total_seconds() / 60
                except:
                    pass
            
            # 根据对话数量估算（假设平均每轮对话30秒）
            if dialogues:
                return len(dialogues) * 0.5  # 30秒 = 0.5分钟
            
            return 0.0
            
        except Exception as e:
            logger.error(f"计算讲解时长失败: {e}")
            return 0.0
    
    def _calculate_interaction_frequency(self, 
                                       dialogues: List[Dict[str, Any]],
                                       duration_minutes: float) -> float:
        """计算互动频率"""
        
        try:
            if duration_minutes <= 0 or not dialogues:
                return 0.0
            
            # 计算互动回合数（连续同一说话人不算互动）
            interaction_rounds = 0
            previous_speaker = None
            
            for dialogue in dialogues:
                current_speaker = dialogue.get('speaker', 'unknown')
                if previous_speaker and current_speaker != previous_speaker and current_speaker != 'unknown':
                    interaction_rounds += 1
                previous_speaker = current_speaker
            
            # 计算每分钟互动次数
            return interaction_rounds / duration_minutes
            
        except Exception as e:
            logger.error(f"计算互动频率失败: {e}")
            return 0.0
    
    def _detect_deal_or_visit(self, processed_text: Dict[str, Any]) -> bool:
        """检测成交或约访"""
        
        try:
            # 获取全部对话内容
            all_content = processed_text.get('cleaned_text', '')
            customer_content = processed_text.get('content_analysis', {}).get('customer_content', [])
            customer_text = ' '.join(customer_content)
            
            # 成交关键词
            deal_patterns = [
                r'(成交|购买|买了|要了|订购)',
                r'(多少钱|价格|怒么付款)',
                r'(同意|决定|考虑好了)',
                r'(试用|先试试)'
            ]
            
            # 约访关键词  
            visit_patterns = [
                r'(面谈|面访|上门|到公司)',
                r'(约个时间|预约|安排时间)',
                r'(明天|后天|下周).{0,10}(来|过去|访问)',
                r'(地址|地点|位置).{0,20}(在哪|在哪里)'
            ]
            
            # 检测成交信号
            for pattern in deal_patterns:
                if re.search(pattern, all_content):
                    return True
            
            # 检测约访信号
            for pattern in visit_patterns:
                if re.search(pattern, all_content):
                    return True
            
            # 检测客户积极响应
            positive_responses = [
                r'(可以|好的|行|没问题)',
                r'(我想|我要|给我)',
                r'(联系方式|电话号码)'
            ]
            
            for pattern in positive_responses:
                if re.search(pattern, customer_text):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"检测成交或约访失败: {e}")
            return False
    
    def _calculate_word_statistics(self, content_analysis: Dict[str, Any]) -> Dict[str, int]:
        """计算词数统计"""
        
        try:
            sales_content = content_analysis.get('sales_content', [])
            customer_content = content_analysis.get('customer_content', [])
            
            # 计算字数（中文环境下字数更有意义）
            sales_words = sum(len(content.replace(' ', '')) for content in sales_content)
            customer_words = sum(len(content.replace(' ', '')) for content in customer_content)
            total_words = sales_words + customer_words
            
            return {
                'total_words': total_words,
                'sales_words': sales_words,
                'customer_words': customer_words
            }
            
        except Exception as e:
            logger.error(f"计算词数统计失败: {e}")
            return {
                'total_words': 0,
                'sales_words': 0,
                'customer_words': 0
            }

    def _detect_money_ask(self, processed_text: Dict[str, Any]) -> Dict[str, Any]:
        """识别销售的要钱/付费/下单类行为并统计次数与证据。

        定义：销售明确要求客户付费、购买、下单等涉及金钱的要求。
        使用简化的检测逻辑，避免过度复杂化。
        """
        try:
            sales_utts = processed_text.get('content_analysis', {}).get('sales_content', []) or []

            quotes: List[str] = []
            count = 0
            
            for utt in sales_utts:
                if not utt or len(utt.strip()) < 8:  # 过滤太短的话语
                    continue
                
                # 使用简化的检测逻辑
                if self._contains_money_ask_behavior(utt):
                    count += 1
                    # 提取关键证据片段
                    snippet = self._extract_key_evidence(utt)
                    quotes.append(snippet)
            
            return {"count": count, "quotes": quotes[:10]}
            
        except Exception as e:
            logger.error(f"要钱行为检测失败: {e}")
            return {"count": 0, "quotes": []}

    def _contains_money_ask_behavior(self, text: str) -> bool:
        """检查是否包含要钱行为 - 简化版本"""
        
        # 首先排除明显的非要钱场景
        exclude_patterns = [
            r'您.{0,15}(买|购买|成本价|持有|持仓).{0,20}(股票|多少|什么时候)',  # 询问客户持仓
            r'客户.{0,15}(买|购买|持有)',  # 描述客户行为
            r'(下载|注册|安装|打开|返回).{0,15}(软件|APP|应用)',  # 软件操作指导（但不包括付费相关的）
            r'股价.{0,30}(区域|位置|点位|涨|跌)',  # 技术分析
            r'(这|那).{0,10}股票.{0,20}可以.{0,10}(买入|买进)',  # 股票交易建议
        ]
        
        # 检查排除模式
        for pattern in exclude_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        
        # 检查要钱行为模式
        money_ask_patterns = [
            # 1. 明确的价格表述
            r'(￥|¥)\s*\d+',  # 金额符号
            r'\d+\s*(元|块)\s*(一年|年费|月费|季度)',  # 具体费用
            r'\d+您确定',  # 价格确认
            r'原价.*\d+.*一年',  # 原价对比
            r'二百八.*八十八',  # 具体数字
            r'几毛钱',  # 低价暗示
            
            # 2. 收费相关表述
            r'(收费|付费|费用)',  # 直接提及收费
            r'(全是|都是).{0,10}收费',  # 收费说明
            r'(花|去花)\d+.*开通',  # 花钱开通
            r'花.*钱',  # 花钱
            
            # 3. 开通和办理行为
            r'开通.*年',  # 开通服务
            r'开通.*之后',  # 开通后续
            r'点进去.*办理',  # 办理操作
            r'操作办理',  # 操作办理
            r'您.*办理',  # 建议办理
            
            # 4. 活动和优惠
            r'抢到.*活动',  # 活动优惠
            r'现实秒杀',  # 秒杀活动
            r'恭喜.*抢到',  # 恭喜获得优惠
            
            # 5. 会员和套餐推销
            r'(VIP|会员|套餐)',  # VIP相关
            r'升级.*可以',  # 升级功能
            r'送.*月.*使用期',  # 赠送使用期
            
            # 6. 试用和体验推广
            r'(先|可以).{0,10}(试用|体验)',  # 试用推广
            r'免费.*后',  # 免费试用后
            
            # 7. 购买压力和紧迫感
            r'耽误.*几分钟.*时间.*可以',  # 时间压力
            r'点进去.*操作',  # 操作引导
            r'工号.*填',  # 填写工号
            
            # 8. 价值包装
            r'连续费率.*占到.*%',  # 续费率
            r'排名.*第一',  # 排名优势
            r'23年.*时间',  # 历史悠久
            
            # 9. 免费限制暗示
            r'只能用.*股票',  # 免费限制
            r'免费.*版本.*每天.*只能',  # 免费限制
        ]
        
        # 检查是否匹配任何要钱模式
        for pattern in money_ask_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False

    def _extract_key_evidence(self, text: str) -> str:
        """提取关键证据片段"""
        
        # 如果文本较短，直接返回
        if len(text) <= 100:
            return text
        
        # 查找包含关键词的句子
        key_phrases = [
            '收费', '付费', '费用', 'VIP', '会员', '套餐', '试用', '体验',
            '开通', '升级', '购买', '元', '块', '免费'
        ]
        
        sentences = re.split(r'[。！？；;.!?]', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:
                for phrase in key_phrases:
                    if phrase in sentence:
                        # 返回包含关键词的句子，限制长度
                        if len(sentence) > 80:
                            return sentence[:80] + "..."
                        return sentence
        
        # 如果没找到合适的句子，返回截断的文本
        return text[:100] + "..."
