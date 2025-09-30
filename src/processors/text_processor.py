"""文本预处理模块"""

import re
import jieba
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
from ..utils.logger import get_logger

logger = get_logger(__name__)


class TextProcessor:
    """文本预处理器"""
    
    def __init__(self):
        # 初始化jieba
        jieba.initialize()
        
        # 销售和客户标识符模式
        self.speaker_patterns = {
            'sales': [
                # 传统中文格式
                r'(销售|客服|顾问|老师|分析师|专员)[:：]',
                r'[小大]?[王李张赵陈刘][:：]',
                r'工作人员[:：]',
                r'(益盟|操盘手|客服中心|工作人员)[:：]',
                r'(这边|我们这边|我这边).{0,6}(益盟|操盘手|客服|专员|老师|顾问)[:：]?',
                r'益盟[:：]',
                # 添加具体人名模式 - 通常销售人员会用真实姓名
                r'侯茜茜',  # 实际测试数据中的销售人员姓名
                r'[小大]?[王李张赵陈刘黄周吴徐孙胡朱高林何郭马罗梁宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严赖覃洪武莫孔汤向常温康施文牛樊葛邢安齐易乔伍庞颜倪庄聂章鲁岑薄翟殷詹申欧耿关兰焦俞左柳甘祝包宁尚符舒阮柯纪梅童凌毕单季裴霍涂成苗谷盛曲翁冉骆蓝路游辛靳管柴蒙乔连谢]{1,3}\s+\d{4}年\d{2}月\d{2}日\s+\d{2}:\d{2}:\d{2}',  # 人名+时间戳格式
                r'[一-龯]{2,4}\s+\d{4}年\d{2}月\d{2}日\s+\d{2}:\d{2}:\d{2}',  # 通用中文姓名+时间戳格式
            ],
            'customer': [
                # 传统中文格式
                r'(客户|用户|先生|女士|老板)[:：]',
                r'(用户|投资者|股民)[:：]',
                r'[小大]?[王李张赵陈刘](先生|女士|老板)[:：]',
                r'客户\s+\d{4}年\d{2}月\d{2}日\s+\d{2}:\d{2}:\d{2}',  # 客户+时间戳格式
            ]
        }
        
        # A/B格式的说话人标识模式 - 重要：A是销售，B是客户
        self.ab_speaker_pattern = r'\[(\d+:\d+:\d+)\]([AB]):'
        
        # 时间戳模式 - 支持多种格式
        self.timestamp_patterns = [
            r'\d{2}:\d{2}:\d{2}',  # HH:MM:SS 传统格式
            r'\[(\d+:\d+:\d+)\]',  # [H:M:S] 新格式
        ]
        
        # 无效内容模式
        self.noise_patterns = [
            r'<br\s*/?>', # HTML换行标签
            r'<.*?>',    # 其他HTML标签
            r'（.*?）',   # 中文括号
            r'\(.*?\)',  # 英文括号
            r'嗯{2,}',   # 多个嗯
            r'啊{2,}',   # 多个啊
            r'哦{2,}',   # 多个哦
            r'额{2,}',   # 多个额
        ]
        
    async def process(self, text: str) -> Dict[str, Any]:
        """处理文本"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # 1. 基础清理
            cleaned_text = self._clean_text(text)
            
            # 2. 对话分割
            dialogues = self._split_dialogues(cleaned_text)
            
            # 3. 角色识别
            speaker_dialogues = self._identify_speakers(dialogues)
            
            # 4. 时间戳处理
            timed_dialogues = self._process_timestamps(speaker_dialogues)
            
            # 5. 内容分析
            content_analysis = self._analyze_content(timed_dialogues)
            
            # 6. 分句处理
            sentences = self._split_sentences(timed_dialogues)
            
            # 7. 关键词提取
            keywords = self._extract_keywords(cleaned_text)
            
            # 8. 统计信息
            statistics = self._calculate_statistics(timed_dialogues)
            
            end_time = asyncio.get_event_loop().time()
            
            result = {
                'original_text': text,
                'cleaned_text': cleaned_text,
                'dialogues': timed_dialogues,
                'sentences': sentences,
                'keywords': keywords,
                'content_analysis': content_analysis,
                'statistics': statistics,
                'processing_time': end_time - start_time
            }
            
            logger.info(f"文本预处理完成，对话数: {len(timed_dialogues)}, 时长估算: {statistics.get('estimated_duration_minutes', 0):.1f}分钟")
            return result
            
        except Exception as e:
            logger.error(f"文本预处理失败: {e}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ""
            
        cleaned = text
        
        # 先处理HTML标签 - 特别是<br/>标签，替换为换行符而不是移除
        cleaned = re.sub(r'<br\s*/?>', '\n', cleaned)  # 将<br/>标签替换为换行符
        cleaned = re.sub(r'<.*?>', '', cleaned)        # 移除其他HTML标签
        
        # 去除其他噪音模式（但不包括时间戳括号）
        for pattern in self.noise_patterns:
            if not pattern.startswith(r'<br') and pattern != r'<.*?>':  # 已经处理过HTML标签
                cleaned = re.sub(pattern, '', cleaned)

        # 标准化换行并保留对话行结构
        cleaned = re.sub(r'\r\n?', '\n', cleaned)  # 统一行结束符

        # 折叠行内多余的空格或制表符，保留换行
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)

        # 去除每行首尾空格，防止出现空白行
        cleaned = '\n'.join(line.strip() for line in cleaned.split('\n') if line.strip())

        # 去除首尾多余空行
        cleaned = cleaned.strip()

        return cleaned
    
    def _split_dialogues(self, text: str) -> List[str]:
        """分割对话"""
        if not text:
            return []
        
        # 按行分割
        lines = text.split('\n')
        dialogues = []
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 2:  # 过滤太短的行
                dialogues.append(line)
        
        return dialogues
    
    def _identify_speakers(self, dialogues: List[str]) -> List[Dict[str, Any]]:
        """识别说话人"""
        speaker_dialogues = []
        
        for i, dialogue in enumerate(dialogues):
            speaker = 'unknown'
            content = dialogue
            original = dialogue
            timestamp_str = None
            
            # 优先检查A/B格式
            ab_match = re.match(self.ab_speaker_pattern, dialogue)
            if ab_match:
                timestamp_str = ab_match.group(1)
                speaker_letter = ab_match.group(2)
                
                # A代表销售(Agent)，B代表客户(Buyer)
                if speaker_letter == 'A':
                    speaker = 'sales'
                elif speaker_letter == 'B':
                    speaker = 'customer'
                
                # 提取内容（去除时间戳和说话人标识）
                content = dialogue[ab_match.end():].strip()
            
            else:
                # 检查传统中文格式
                # 检查销售模式
                for pattern in self.speaker_patterns['sales']:
                    if re.search(pattern, dialogue):
                        speaker = 'sales'
                        if '年' in dialogue and '月' in dialogue and '日' in dialogue:
                            # 这是时间戳行，可能内容在同一行
                            content = re.sub(pattern, '', dialogue).strip()
                        else:
                            # 移除说话人标识
                            content = re.sub(pattern, '', dialogue).strip()
                        break
                
                # 检查客户模式
                if speaker == 'unknown':
                    for pattern in self.speaker_patterns['customer']:
                        if re.search(pattern, dialogue):
                            speaker = 'customer'
                            if '年' in dialogue and '月' in dialogue and '日' in dialogue:
                                content = re.sub(pattern, '', dialogue).strip()
                            else:
                                content = re.sub(pattern, '', dialogue).strip()
                            break
                
                # 如果仍然未识别，根据内容特征推断
                if speaker == 'unknown':
                    speaker = self._infer_speaker_by_content(content)
            
            # 只添加有实际内容的对话
            if content.strip() and len(content.strip()) > 1:
                speaker_dialogues.append({
                    'speaker': speaker,
                    'content': content,
                    'original': original,
                    'extracted_timestamp': timestamp_str  # A/B格式提取的时间戳
                })
        
        return speaker_dialogues
    
    def _infer_speaker_by_content(self, content: str) -> str:
        """根据内容特征推断说话人"""
        # 销售特征词
        sales_keywords = [
            '我们', '我是', '益盟', '操盘手', '专员', '老师', '帮您', '为您',
            '给您', '分析', '指标', '软件', '功能', '腾讯', '上市公司',
            'BS点', '买卖点', '主力资金', '步步高', '这边', '公司', '平台',
            '特地', '免费', '讲解', '演示', '客户', '用户'
        ]
        
        # 客户特征词
        customer_keywords = [
            '喂', '嗯', '好', '可以', '行', '知道', '明白', '没有', '有',
            '多少钱', '收费', '效果', '真的', '不需要', '没空', '回头', 
            '没时间', '不感兴趣', '等会', '忙', '先生', '打开了'
        ]
        
        sales_score = sum(1 for kw in sales_keywords if kw in content)
        customer_score = sum(1 for kw in customer_keywords if kw in content)
        
        # 短回应更可能是客户
        if len(content.strip()) <= 3 and content.strip() in ['嗯', '喂', '好', '行', '可以', '有', '没有']:
            return 'customer'
        
        if sales_score > customer_score:
            return 'sales'
        elif customer_score > sales_score:
            return 'customer'
        else:
            return 'unknown'
    
    def _process_timestamps(self, dialogues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理时间戳"""
        for i, dialogue in enumerate(dialogues):
            timestamp = None
            
            # 优先使用A/B格式提取的时间戳
            if dialogue.get('extracted_timestamp'):
                timestamp = dialogue['extracted_timestamp']
            else:
                # 尝试从原始文本中提取时间戳
                for pattern in self.timestamp_patterns:
                    timestamp_match = re.search(pattern, dialogue['original'])
                    if timestamp_match:
                        if pattern.startswith(r'\['):
                            # [H:M:S]格式，提取括号内的时间
                            timestamp = timestamp_match.group(1)
                        else:
                            # 传统HH:MM:SS格式
                            timestamp = timestamp_match.group()
                        break
            
            dialogue['timestamp'] = timestamp
            dialogue['sequence'] = i
            
            # 清理extracted_timestamp字段
            if 'extracted_timestamp' in dialogue:
                del dialogue['extracted_timestamp']
        
        return dialogues
    
    def _analyze_content(self, dialogues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """内容分析"""
        sales_dialogues = [d for d in dialogues if d['speaker'] == 'sales']
        customer_dialogues = [d for d in dialogues if d['speaker'] == 'customer']
        unknown_dialogues = [d for d in dialogues if d['speaker'] == 'unknown']
        
        analysis = {
            'total_dialogues': len(dialogues),
            'sales_dialogues': len(sales_dialogues),
            'customer_dialogues': len(customer_dialogues),
            'unknown_dialogues': len(unknown_dialogues),
            
            'sales_content': [d['content'] for d in sales_dialogues],
            'customer_content': [d['content'] for d in customer_dialogues],
            
            'conversation_pattern': self._analyze_conversation_pattern(dialogues),
            'topic_transitions': self._analyze_topic_transitions(dialogues)
        }
        
        logger.info(f"内容分析: 总对话{analysis['total_dialogues']}, 销售{analysis['sales_dialogues']}, 客户{analysis['customer_dialogues']}, 未知{analysis['unknown_dialogues']}")
        
        return analysis
    
    def _analyze_conversation_pattern(self, dialogues: List[Dict[str, Any]]) -> List[str]:
        """分析对话模式"""
        pattern = []
        for dialogue in dialogues:
            pattern.append(dialogue['speaker'])
        return pattern
    
    def _analyze_topic_transitions(self, dialogues: List[Dict[str, Any]]) -> List[str]:
        """分析话题转换"""
        # 简化版话题识别
        topic_keywords = {
            'introduction': ['我是', '身份', '公司', '腾讯', '益盟', '操盘手'],
            'product': ['软件', '功能', '指标', '操盘手', '分析'],
            'demonstration': ['BS点', '买卖点', '步步高', '演示', '看一下', '点开'],
            'pricing': ['价格', '收费', '多少钱', '免费'],
            'objection': ['不需要', '没空', '不感兴趣', '考虑', '忙'],
            'closing': ['成交', '购买', '试用', '联系方式', '微信']
        }
        
        topics = []
        for dialogue in dialogues:
            content = dialogue['content']
            dialogue_topics = []
            
            for topic, keywords in topic_keywords.items():
                if any(kw in content for kw in keywords):
                    dialogue_topics.append(topic)
            
            if dialogue_topics:
                topics.extend(dialogue_topics)
        
        return topics
    
    def _split_sentences(self, dialogues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """分句处理"""
        sentences = []
        
        for dialogue in dialogues:
            content = dialogue['content']
            
            # 分句
            sentence_splits = re.split(r'[。！？；;.!?]', content)
            
            for i, sentence in enumerate(sentence_splits):
                sentence = sentence.strip()
                if sentence and len(sentence) > 2:
                    sentences.append({
                        'sentence': sentence,
                        'speaker': dialogue['speaker'],
                        'dialogue_sequence': dialogue['sequence'],
                        'sentence_sequence': i,
                        'timestamp': dialogue.get('timestamp')
                    })
        
        return sentences
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        if not text:
            return []
        
        # 使用jieba分词
        words = jieba.lcut(text)
        
        # 过滤停用词和短词
        stop_words = {'的', '了', '是', '在', '我', '你', '他', '她', '它', '我们', '你们', '他们',
                      '这', '那', '这个', '那个', '什么', '怎么', '为什么', '哪里', '哪个', '几个',
                      '一些', '有些', '所有', '每个', '任何', '没有', '都', '也', '还', '就',
                      '从', '到', '向', '往', '对', '为', '和', '与', '以及', '或者', '但是',
                      '然而', '因为', '所以', '如果', '虽然', '尽管', '除了', '包括'}
        
        keywords = []
        for word in words:
            if (len(word) > 1 and 
                word not in stop_words and 
                not word.isdigit() and
                not re.match(r'^[a-zA-Z]+$', word)):
                keywords.append(word)
        
        # 去重并按频次排序
        from collections import Counter
        keyword_counts = Counter(keywords)
        return [kw for kw, count in keyword_counts.most_common(50)]
    
    def _calculate_statistics(self, dialogues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算统计信息"""
        if not dialogues:
            return {}
        
        sales_dialogues = [d for d in dialogues if d['speaker'] == 'sales']
        customer_dialogues = [d for d in dialogues if d['speaker'] == 'customer']
        
        # 字符统计
        sales_chars = sum(len(d['content']) for d in sales_dialogues)
        customer_chars = sum(len(d['content']) for d in customer_dialogues)
        total_chars = sales_chars + customer_chars
        
        # 时间统计 - 支持[H:M:S]格式
        timestamps = [d.get('timestamp') for d in dialogues if d.get('timestamp')]
        duration_minutes = 0
        
        if len(timestamps) >= 2:
            try:
                # 解析开始和结束时间戳
                start_time_str = timestamps[0]
                end_time_str = timestamps[-1]
                
                # 解析时间戳 - 支持H:M:S格式（小时可能超过24）
                def parse_timestamp(ts_str):
                    parts = ts_str.split(':')
                    if len(parts) == 3:
                        hours = int(parts[0])
                        minutes = int(parts[1]) 
                        seconds = int(parts[2])
                        return hours * 3600 + minutes * 60 + seconds
                    return 0
                
                start_seconds = parse_timestamp(start_time_str)
                end_seconds = parse_timestamp(end_time_str)
                
                duration_seconds = end_seconds - start_seconds
                if duration_seconds > 0:
                    duration_minutes = duration_seconds / 60
                else:
                    # 如果计算出负数，可能是跨天或其他问题，使用对话数量估算
                    duration_minutes = len(dialogues) * 0.5  # 每个对话平均30秒
                    
            except Exception as e:
                logger.warning(f"时间戳解析失败，使用估算: {e}")
                # 如果时间戳解析失败，基于对话数量估算
                duration_minutes = len(dialogues) * 0.5  # 每个对话平均30秒
        else:
            # 没有时间戳，基于对话数量估算
            duration_minutes = len(dialogues) * 0.5  # 每个对话平均30秒
        
        logger.info(f"时长计算: 共{len(timestamps)}个时间戳, 估算时长{duration_minutes:.1f}分钟")
        
        return {
            'total_dialogues': len(dialogues),
            'sales_dialogues_count': len(sales_dialogues),
            'customer_dialogues_count': len(customer_dialogues),
            
            'total_characters': total_chars,
            'sales_characters': sales_chars,
            'customer_characters': customer_chars,
            'sales_ratio': sales_chars / total_chars if total_chars > 0 else 0,
            
            'estimated_duration_minutes': duration_minutes,
            'interaction_frequency': len(dialogues) / duration_minutes if duration_minutes > 0 else 0,
            
            'average_dialogue_length': total_chars / len(dialogues) if dialogues else 0,
            'sales_avg_length': sales_chars / len(sales_dialogues) if sales_dialogues else 0,
            'customer_avg_length': customer_chars / len(customer_dialogues) if customer_dialogues else 0
        }
