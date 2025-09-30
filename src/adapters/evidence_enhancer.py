"""证据增强器 - 将简单证据文本转换为UI所需的结构化格式

该模块负责将现有系统中的简单证据字符串转换为UI界面所需的
包含索引、时间戳和引用片段的结构化格式。

主要功能：
1. 解析现有的证据字符串格式
2. 匹配对话片段并提取结构化信息
3. 提供降级处理机制以确保系统稳定性
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class EvidenceEnhancer:
    """证据增强器

    将现有的简单证据文本转换为UI所需的结构化格式：
    {
        "idx": int,       # 对话索引
        "ts": str,        # 时间戳
        "quote": str      # 引用片段
    }
    """

    def __init__(self, max_quote_length: int = 200, cache_size: int = 1000):
        """初始化证据增强器

        Args:
            max_quote_length: 引用片段的最大长度
            cache_size: 缓存大小
        """
        self.max_quote_length = max_quote_length
        self.cache_size = cache_size
        self._cache: Dict[str, List[Dict]] = {}
        self._cache_stats = {"hits": 0, "misses": 0}

        # 常见的证据格式正则模式
        self._evidence_patterns = [
            # 格式1: "姓名 日期 内容"
            r'^(.+?)\s+(\d{4}年\d{1,2}月\d{1,2}日|\d{4}-\d{1,2}-\d{1,2})\s+(.+)$',
            # 格式2: "时间戳: 内容"
            r'^(\d{1,2}:\d{1,2}:\d{1,2}|\d{1,2}:\d{1,2})\s*[:：]\s*(.+)$',
            # 格式3: 纯内容（无时间信息）
            r'^(.+)$'
        ]

    def enhance_evidence(self,
                        evidence_text: str,
                        processed_text: Optional[Dict] = None,
                        context_hint: Optional[str] = None) -> List[Dict[str, Any]]:
        """增强证据文本为结构化格式

        Args:
            evidence_text: 原始证据文本
            processed_text: 处理后的文本数据，包含dialogues等信息
            context_hint: 上下文提示，用于改善匹配准确性

        Returns:
            List[Dict]: 结构化的证据列表
        """
        if not evidence_text or not evidence_text.strip():
            return []

        # 检查缓存
        cache_key = self._generate_cache_key(evidence_text, processed_text, context_hint)
        if cache_key in self._cache:
            self._cache_stats["hits"] += 1
            logger.debug(f"Cache hit for evidence: {evidence_text[:50]}...")
            return self._cache[cache_key]

        self._cache_stats["misses"] += 1

        try:
            # 解析证据文本
            parsed_evidence = self._parse_evidence_text(evidence_text)

            # 如果没有处理文本，返回简化格式
            if not processed_text:
                result = self._create_fallback_evidence(parsed_evidence, evidence_text)
            else:
                # 尝试匹配对话片段
                result = self._match_dialogues(parsed_evidence, processed_text, context_hint)

                # 如果匹配失败，使用降级策略
                if not result:
                    result = self._create_fallback_evidence(parsed_evidence, evidence_text)

            # 缓存结果
            self._update_cache(cache_key, result)

            logger.debug(f"Enhanced evidence: {len(result)} items found")
            return result

        except Exception as e:
            logger.warning(f"Evidence enhancement failed: {e}, using fallback")
            fallback_result = self._create_simple_fallback(evidence_text)
            self._update_cache(cache_key, fallback_result)
            return fallback_result

    def _parse_evidence_text(self, evidence_text: str) -> Dict[str, Any]:
        """解析证据文本，提取结构化信息

        Args:
            evidence_text: 原始证据文本

        Returns:
            Dict: 解析后的结构化信息
        """
        evidence_info = {
            "original_text": evidence_text,
            "speaker": None,
            "timestamp": None,
            "content": evidence_text.strip(),
            "keywords": []
        }

        # 尝试各种格式模式
        for pattern in self._evidence_patterns:
            match = re.match(pattern, evidence_text.strip(), re.DOTALL)
            if match:
                groups = match.groups()

                if len(groups) == 3:  # 格式1: 姓名 日期 内容
                    evidence_info["speaker"] = groups[0].strip()
                    evidence_info["timestamp"] = self._parse_timestamp(groups[1])
                    evidence_info["content"] = groups[2].strip()
                elif len(groups) == 2:  # 格式2: 时间: 内容
                    evidence_info["timestamp"] = groups[0].strip()
                    evidence_info["content"] = groups[1].strip()

                break

        # 提取关键词用于匹配
        evidence_info["keywords"] = self._extract_keywords(evidence_info["content"])

        return evidence_info

    def _match_dialogues(self,
                        parsed_evidence: Dict[str, Any],
                        processed_text: Dict,
                        context_hint: Optional[str] = None) -> List[Dict[str, Any]]:
        """匹配对话片段

        Args:
            parsed_evidence: 解析后的证据信息
            processed_text: 处理后的文本数据
            context_hint: 上下文提示

        Returns:
            List[Dict]: 匹配到的对话片段
        """
        dialogues = processed_text.get('dialogues', [])
        if not dialogues:
            return []

        matches = []
        content = parsed_evidence["content"]
        keywords = parsed_evidence["keywords"]

        # 策略1: 精确文本匹配
        for i, dialogue in enumerate(dialogues):
            dialogue_content = dialogue.get('content', '')
            if content in dialogue_content or dialogue_content in content:
                matches.append({
                    "idx": i,
                    "ts": dialogue.get('timestamp', ''),
                    "quote": self._truncate_quote(dialogue_content),
                    "match_type": "exact",
                    "confidence": 1.0
                })

        # 策略2: 关键词匹配（如果精确匹配失败）
        if not matches and keywords:
            for i, dialogue in enumerate(dialogues):
                dialogue_content = dialogue.get('content', '')
                match_score = self._calculate_keyword_match_score(keywords, dialogue_content)

                if match_score > 0.3:  # 阈值可配置
                    matches.append({
                        "idx": i,
                        "ts": dialogue.get('timestamp', ''),
                        "quote": self._truncate_quote(dialogue_content),
                        "match_type": "keyword",
                        "confidence": match_score
                    })

        # 策略3: 模糊匹配（基于相似度）
        if not matches:
            matches = self._fuzzy_match_dialogues(content, dialogues)

        # 排序并返回最佳匹配
        matches.sort(key=lambda x: x["confidence"], reverse=True)
        return matches[:3]  # 最多返回3个匹配结果

    def _fuzzy_match_dialogues(self, content: str, dialogues: List[Dict]) -> List[Dict[str, Any]]:
        """模糊匹配对话片段

        Args:
            content: 证据内容
            dialogues: 对话列表

        Returns:
            List[Dict]: 模糊匹配结果
        """
        matches = []
        content_words = set(content.replace('，', '').replace('。', '').replace('？', '').split())

        for i, dialogue in enumerate(dialogues):
            dialogue_content = dialogue.get('content', '')
            dialogue_words = set(dialogue_content.replace('，', '').replace('。', '').replace('？', '').split())

            # 计算词汇重叠度
            if content_words and dialogue_words:
                overlap = len(content_words & dialogue_words)
                union = len(content_words | dialogue_words)
                similarity = overlap / union if union > 0 else 0

                if similarity > 0.2:  # 相似度阈值
                    matches.append({
                        "idx": i,
                        "ts": dialogue.get('timestamp', ''),
                        "quote": self._truncate_quote(dialogue_content),
                        "match_type": "fuzzy",
                        "confidence": similarity
                    })

        return matches

    def _create_fallback_evidence(self, parsed_evidence: Dict[str, Any], original_text: str) -> List[Dict[str, Any]]:
        """创建降级证据格式

        当无法匹配到具体对话时，创建一个基于原始证据的简化格式

        Args:
            parsed_evidence: 解析后的证据信息
            original_text: 原始证据文本

        Returns:
            List[Dict]: 降级格式的证据列表
        """
        return [{
            "idx": 0,
            "ts": parsed_evidence.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "quote": self._truncate_quote(parsed_evidence["content"]),
            "match_type": "fallback",
            "confidence": 0.5,
            "original_evidence": original_text
        }]

    def _create_simple_fallback(self, evidence_text: str) -> List[Dict[str, Any]]:
        """创建最简单的降级格式

        Args:
            evidence_text: 原始证据文本

        Returns:
            List[Dict]: 最简单的降级格式
        """
        return [{
            "idx": 0,
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "quote": self._truncate_quote(evidence_text),
            "match_type": "simple_fallback",
            "confidence": 0.1
        }]

    def _parse_timestamp(self, timestamp_str: str) -> str:
        """解析时间戳字符串

        Args:
            timestamp_str: 时间戳字符串

        Returns:
            str: 标准化的时间戳
        """
        try:
            # 尝试解析中文日期格式
            if '年' in timestamp_str and '月' in timestamp_str and '日' in timestamp_str:
                # 转换为标准格式
                timestamp_str = timestamp_str.replace('年', '-').replace('月', '-').replace('日', '')
                datetime.strptime(timestamp_str, '%Y-%m-%d')
                return timestamp_str

            # 尝试解析ISO格式
            if '-' in timestamp_str:
                datetime.strptime(timestamp_str, '%Y-%m-%d')
                return timestamp_str

            # 时间格式
            if ':' in timestamp_str:
                return timestamp_str

        except ValueError:
            pass

        # 如果解析失败，返回当前时间
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _extract_keywords(self, content: str) -> List[str]:
        """从内容中提取关键词

        Args:
            content: 文本内容

        Returns:
            List[str]: 关键词列表
        """
        # 移除标点符号，分割为词汇
        import re
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', content)

        # 过滤短词和停用词
        stop_words = {'的', '了', '在', '是', '我', '你', '他', '她', '它', '我们', '你们', '他们'}
        keywords = [word for word in words if len(word) > 1 and word not in stop_words]

        return keywords[:10]  # 最多返回10个关键词

    def _calculate_keyword_match_score(self, keywords: List[str], content: str) -> float:
        """计算关键词匹配分数

        Args:
            keywords: 关键词列表
            content: 待匹配的内容

        Returns:
            float: 匹配分数 (0-1)
        """
        if not keywords:
            return 0.0

        matched_count = sum(1 for keyword in keywords if keyword in content)
        return matched_count / len(keywords)

    def _truncate_quote(self, quote: str) -> str:
        """截断引用片段到合适长度

        Args:
            quote: 原始引用

        Returns:
            str: 截断后的引用
        """
        if len(quote) <= self.max_quote_length:
            return quote

        # 尽量在句子边界截断
        truncated = quote[:self.max_quote_length]
        sentence_end = max(truncated.rfind('。'), truncated.rfind('！'), truncated.rfind('？'))

        if sentence_end > self.max_quote_length * 0.5:  # 如果句子结束位置合理
            return quote[:sentence_end + 1]
        else:
            return truncated + "..."

    def _generate_cache_key(self, evidence_text: str, processed_text: Optional[Dict], context_hint: Optional[str]) -> str:
        """生成缓存键

        Args:
            evidence_text: 证据文本
            processed_text: 处理文本
            context_hint: 上下文提示

        Returns:
            str: 缓存键
        """
        key_data = f"{evidence_text}|{str(processed_text)}|{context_hint or ''}"
        return hashlib.md5(key_data.encode('utf-8')).hexdigest()[:16]

    def _update_cache(self, key: str, value: List[Dict[str, Any]]) -> None:
        """更新缓存

        Args:
            key: 缓存键
            value: 缓存值
        """
        # 如果缓存超限，删除一些旧条目（简单LRU）
        if len(self._cache) >= self.cache_size:
            # 删除前10%的条目
            keys_to_remove = list(self._cache.keys())[:self.cache_size // 10]
            for k in keys_to_remove:
                del self._cache[k]

        self._cache[key] = value

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息

        Returns:
            Dict: 缓存统计
        """
        total_requests = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_rate = self._cache_stats["hits"] / total_requests if total_requests > 0 else 0

        return {
            "cache_size": len(self._cache),
            "max_size": self.cache_size,
            "hits": self._cache_stats["hits"],
            "misses": self._cache_stats["misses"],
            "hit_rate": hit_rate,
            "total_requests": total_requests
        }

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._cache_stats = {"hits": 0, "misses": 0}
        logger.info("Evidence enhancer cache cleared")