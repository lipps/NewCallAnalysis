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
                r'(销售|客服|顾问|老师|分析师|专员)[:：]',
                r'[小大]?[王李张赵陈刘][:：]',
                r'工作人员[:：]',
                r'益盟[:：]'
            ],
            'customer': [
                r'(客户|用户|先生|女士|老板)[:：]',
                r'[小大]?[王李张赵陈刘](先生|女士|老板)[:：]'
            ]
        }
        
        # 时间戳模式
        self.timestamp_pattern = r'\d{2}:\d{2}:\d{2}'
        
        # 无效内容模式
        self.noise_patterns = [
            r'\[.*?\]',  # 括号内容
            r'<.*?>',    # 尖括号内容
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
            
            logger.info(f"文本预处理完成，耗时: {result['processing_time']:.2f}秒")
            return result
            
        except Exception as e:
            logger.error(f"文本预处理失败: {e}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ""
            
        # 去除噪音模式
        cleaned = text
        for pattern in self.noise_patterns:
            cleaned = re.sub(pattern, '', cleaned)
        
        # 标准化空白字符
        cleaned = re.sub(r'\s+', ' ', cleaned)
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
        
        for dialogue in dialogues:
            speaker = 'unknown'
            content = dialogue
            
            # 检查销售模式
            for pattern in self.speaker_patterns['sales']:
                if re.search(pattern, dialogue):
                    speaker = 'sales'
                    # 移除说话人标识
                    content = re.sub(pattern, '', dialogue).strip()
                    break
            
            # 检查客户模式
            if speaker == 'unknown':
                for pattern in self.speaker_patterns['customer']:
                    if re.search(pattern, dialogue):
                        speaker = 'customer'
                        content = re.sub(pattern, '', dialogue).strip()
                        break
            
            # 如果仍然未识别，根据内容特征推断
            if speaker == 'unknown':
                speaker = self._infer_speaker_by_content(content)
            
            speaker_dialogues.append({
                'speaker': speaker,
                'content': content,
                'original': dialogue
            })
        
        return speaker_dialogues
    
    def _infer_speaker_by_content(self, content: str) -> str:
        """根据内容特征推断说话人"""
        # 销售特征词
        sales_keywords = [
            '我们', '我是', '益盟', '操盘手', '专员', '老师', '帮您', '为您',
            '给您', '分析', '指标', '软件', '功能', '腾讯', '上市公司',
            'BS点', '买卖点', '主力资金', '步步高'
        ]
        
        # 客户特征词
        customer_keywords = [
            '我', '你', '这个', '怎么', '多少钱', '收费', '效果', '真的',
            '可以', '不需要', '没空', '没时间', '不感兴趣'
        ]
        
        sales_score = sum(1 for kw in sales_keywords if kw in content)
        customer_score = sum(1 for kw in customer_keywords if kw in content)
        
        if sales_score > customer_score:
            return 'sales'
        elif customer_score > sales_score:
            return 'customer'
        else:
            return 'unknown'
    
    def _process_timestamps(self, dialogues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理时间戳"""
        for i, dialogue in enumerate(dialogues):
            # 提取时间戳
            timestamp_match = re.search(self.timestamp_pattern, dialogue['original'])
            if timestamp_match:
                dialogue['timestamp'] = timestamp_match.group()
                # 移除时间戳
                dialogue['content'] = re.sub(self.timestamp_pattern, '', dialogue['content']).strip()
            else:
                dialogue['timestamp'] = None
            
            # 设置序号
            dialogue['sequence'] = i
        
        return dialogues
    
    def _analyze_content(self, dialogues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """内容分析"""
        sales_dialogues = [d for d in dialogues if d['speaker'] == 'sales']
        customer_dialogues = [d for d in dialogues if d['speaker'] == 'customer']
        
        analysis = {
            'total_dialogues': len(dialogues),
            'sales_dialogues': len(sales_dialogues),
            'customer_dialogues': len(customer_dialogues),
            'unknown_dialogues': len(dialogues) - len(sales_dialogues) - len(customer_dialogues),
            
            'sales_content': [d['content'] for d in sales_dialogues],
            'customer_content': [d['content'] for d in customer_dialogues],
            
            'conversation_pattern': self._analyze_conversation_pattern(dialogues),
            'topic_transitions': self._analyze_topic_transitions(dialogues)
        }
        
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
            'introduction': ['我是', '身份', '公司', '腾讯'],
            'product': ['软件', '功能', '指标', '操盘手'],
            'demonstration': ['BS点', '买卖点', '步步高', '演示'],
            'pricing': ['价格', '收费', '多少钱', '免费'],
            'objection': ['不需要', '没空', '不感兴趣', '考虑'],
            'closing': ['成交', '购买', '试用', '联系方式']
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
        
        # 时间统计
        timestamps = [d.get('timestamp') for d in dialogues if d.get('timestamp')]
        duration_minutes = 0
        if len(timestamps) >= 2:
            try:
                start_time = datetime.strptime(timestamps[0], '%H:%M:%S')
                end_time = datetime.strptime(timestamps[-1], '%H:%M:%S')
                duration = end_time - start_time
                if duration.total_seconds() < 0:  # 跨天处理
                    duration += timedelta(days=1)
                duration_minutes = duration.total_seconds() / 60
            except:
                duration_minutes = 0
        
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