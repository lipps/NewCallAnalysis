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

        定义：销售明确提及付费、购买、下单等涉及金钱的要求或建议购买。
        每命中一次（句子或话轮中出现一次相关表达）计 1 次。
        """
        try:
            sales_utts = processed_text.get('content_analysis', {}).get('sales_content', []) or []

            # 金额/数字：如 288元/￥199/99块/一年/一季度等
            price_num = r"(￥|¥|RMB|人民币)?\s*\d+(\.\d+)?\s*(元|块|块钱|人民币|rmb)?"
            cn_num = r"(十|百|千|万|一|二|三|四|五|六|七|八|九|两)+\s*(元|块)"

            # 付费动作/购买/充值/开通/办理等
            pay_verbs = r"(下单|购买|买|付费|付款|支付|转账|打款|充值|开通|办理|订购|升级|续费|会员|套餐|开卡|激活|成交|签单|扫(码|二维码))"

            # 建议/推动购买的措辞
            push_phrase = r"(可以|建议|不如|要不要|先|考虑|试试).{0,6}(下单|购买|开通|办理|升级|充值)"

            combined = re.compile(
                rf"({price_num}|{cn_num}|{pay_verbs}|{push_phrase})",
                re.IGNORECASE
            )

            quotes: List[str] = []
            count = 0
            for utt in sales_utts:
                if not utt:
                    continue
                matches = list(combined.finditer(utt))
                if matches:
                    count += 1
                    # 证据：尽量返回整句或短片段
                    snippet = utt
                    if len(snippet) > 120:
                        snippet = snippet[:120] + "..."
                    quotes.append(snippet)
            return {"count": count, "quotes": quotes[:20]}
        except Exception:
            return {"count": 0, "quotes": []}
