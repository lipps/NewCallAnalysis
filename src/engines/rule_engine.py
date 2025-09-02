"""规则引擎 - 基于关键词和正则表达式的快速检测"""

import re
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from ..config.settings import DETECTION_RULES
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RuleResult:
    """规则检测结果"""
    hit: bool
    confidence: float
    evidence: str
    rule_type: str
    matched_patterns: List[str]


class RuleEngine:
    """规则引擎"""
    
    def __init__(self):
        self.rules = DETECTION_RULES
        self.compiled_patterns = {}
        self.rule_cache = {}
        
        # 编译所有正则表达式模式
        self._compile_patterns()
    
    def _compile_patterns(self):
        """编译所有正则表达式模式"""
        try:
            for category, category_rules in self.rules.items():
                self.compiled_patterns[category] = {}
                
                for point, rule_config in category_rules.items():
                    self.compiled_patterns[category][point] = {
                        'keywords': rule_config.get('keywords', []),
                        'patterns': []
                    }
                    
                    # 编译正则表达式
                    for pattern in rule_config.get('patterns', []):
                        try:
                            compiled_pattern = re.compile(pattern, re.IGNORECASE)
                            self.compiled_patterns[category][point]['patterns'].append(
                                (compiled_pattern, pattern)
                            )
                        except re.error as e:
                            logger.warning(f"编译正则表达式失败: {pattern}, 错误: {e}")
            
            logger.info(f"规则引擎初始化完成，共编译了 {self._count_rules()} 条规则")
            
        except Exception as e:
            logger.error(f"编译规则模式失败: {e}")
            raise
    
    def _count_rules(self) -> int:
        """统计规则数量"""
        count = 0
        for category in self.compiled_patterns.values():
            for point in category.values():
                count += len(point['keywords']) + len(point['patterns'])
        return count
    
    async def detect(self, 
                    category: str,
                    point: str,
                    text: str,
                    min_confidence: float = 0.3) -> Dict[str, Any]:
        """检测文本是否命中规则"""
        
        try:
            # 检查缓存
            cache_key = f"{category}_{point}_{hash(text)}"
            if cache_key in self.rule_cache:
                return self.rule_cache[cache_key]
            
            # 执行检测
            result = await self._execute_detection(category, point, text)
            
            # 转换为字典格式
            result_dict = {
                'hit': result.hit,
                'confidence': result.confidence,
                'evidence': result.evidence,
                'rule_type': result.rule_type,
                'matched_patterns': result.matched_patterns
            }
            
            # 只缓存高置信度结果
            if result.confidence >= min_confidence:
                # 限制缓存大小
                if len(self.rule_cache) >= 1000:
                    # 删除最旧的一半缓存
                    keys_to_remove = list(self.rule_cache.keys())[:500]
                    for key in keys_to_remove:
                        del self.rule_cache[key]
                
                self.rule_cache[cache_key] = result_dict
            
            return result_dict
            
        except Exception as e:
            logger.error(f"规则检测失败: {e}")
            return {
                'hit': False,
                'confidence': 0.0,
                'evidence': '',
                'rule_type': 'error',
                'matched_patterns': []
            }
    
    async def _execute_detection(self, 
                               category: str,
                               point: str,
                               text: str) -> RuleResult:
        """执行检测逻辑"""
        
        # 获取对应的规则配置
        if category not in self.compiled_patterns or point not in self.compiled_patterns[category]:
            return RuleResult(
                hit=False,
                confidence=0.0,
                evidence="",
                rule_type="no_rule",
                matched_patterns=[]
            )
        
        rule_config = self.compiled_patterns[category][point]
        keywords = rule_config['keywords']
        patterns = rule_config['patterns']
        
        # 并行执行关键词检测和模式匹配
        keyword_task = self._detect_keywords(text, keywords)
        pattern_task = self._detect_patterns(text, patterns)
        
        keyword_result, pattern_result = await asyncio.gather(keyword_task, pattern_task)
        
        # 合并结果
        return self._merge_results(keyword_result, pattern_result)
    
    async def _detect_keywords(self, 
                             text: str, 
                             keywords: List[str]) -> RuleResult:
        """关键词检测"""
        
        if not keywords:
            return RuleResult(False, 0.0, "", "keyword", [])
        
        matched_keywords = []
        evidences = []
        
        text_lower = text.lower()
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in text_lower:
                matched_keywords.append(keyword)
                
                # 提取证据片段（关键词前后各20个字符）
                start_idx = text_lower.find(keyword_lower)
                evidence_start = max(0, start_idx - 20)
                evidence_end = min(len(text), start_idx + len(keyword) + 20)
                evidence = text[evidence_start:evidence_end].strip()
                evidences.append(evidence)
        
        if matched_keywords:
            # 计算置信度（匹配关键词数量比例）
            confidence = min(1.0, len(matched_keywords) / len(keywords) * 1.5)
            
            # 选择最长的证据片段
            best_evidence = max(evidences, key=len) if evidences else ""
            
            return RuleResult(
                hit=True,
                confidence=confidence,
                evidence=best_evidence,
                rule_type="keyword",
                matched_patterns=matched_keywords
            )
        
        return RuleResult(False, 0.0, "", "keyword", [])
    
    async def _detect_patterns(self, 
                             text: str,
                             patterns: List[Tuple[re.Pattern, str]]) -> RuleResult:
        """正则模式检测"""
        
        if not patterns:
            return RuleResult(False, 0.0, "", "pattern", [])
        
        matched_patterns = []
        evidences = []
        
        for compiled_pattern, original_pattern in patterns:
            matches = compiled_pattern.finditer(text)
            
            for match in matches:
                matched_patterns.append(original_pattern)
                
                # 提取匹配的证据片段
                match_start = match.start()
                match_end = match.end()
                
                # 扩展上下文
                evidence_start = max(0, match_start - 30)
                evidence_end = min(len(text), match_end + 30)
                evidence = text[evidence_start:evidence_end].strip()
                evidences.append(evidence)
        
        if matched_patterns:
            # 模式匹配的置信度通常比关键词高
            confidence = min(1.0, len(matched_patterns) / len(patterns) * 2.0)
            
            # 选择最长的证据片段
            best_evidence = max(evidences, key=len) if evidences else ""
            
            return RuleResult(
                hit=True,
                confidence=confidence,
                evidence=best_evidence,
                rule_type="pattern",
                matched_patterns=matched_patterns
            )
        
        return RuleResult(False, 0.0, "", "pattern", [])
    
    def _merge_results(self, 
                      keyword_result: RuleResult,
                      pattern_result: RuleResult) -> RuleResult:
        """合并关键词和模式匹配结果"""
        
        # 如果都没有命中
        if not keyword_result.hit and not pattern_result.hit:
            return RuleResult(False, 0.0, "", "none", [])
        
        # 选择置信度更高的结果
        if keyword_result.confidence >= pattern_result.confidence:
            primary_result = keyword_result
            secondary_result = pattern_result
        else:
            primary_result = pattern_result
            secondary_result = keyword_result
        
        # 合并置信度（加权平均，主要结果权重更高）
        if secondary_result.hit:
            merged_confidence = primary_result.confidence * 0.7 + secondary_result.confidence * 0.3
        else:
            merged_confidence = primary_result.confidence
        
        # 合并证据（选择更长的）
        if len(secondary_result.evidence) > len(primary_result.evidence):
            merged_evidence = secondary_result.evidence
        else:
            merged_evidence = primary_result.evidence
        
        # 合并匹配模式
        merged_patterns = primary_result.matched_patterns + secondary_result.matched_patterns
        
        return RuleResult(
            hit=True,
            confidence=min(1.0, merged_confidence),
            evidence=merged_evidence[:200],  # 限制证据长度
            rule_type=f"{primary_result.rule_type}+{secondary_result.rule_type}" if secondary_result.hit else primary_result.rule_type,
            matched_patterns=list(set(merged_patterns))  # 去重
        )
    
    async def batch_detect(self, 
                          detections: List[Dict[str, str]],
                          max_concurrency: int = 10) -> List[Dict[str, Any]]:
        """批量检测"""
        
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def detect_single(detection_config):
            async with semaphore:
                return await self.detect(
                    category=detection_config['category'],
                    point=detection_config['point'],
                    text=detection_config['text']
                )
        
        # 并发执行所有检测任务
        tasks = [detect_single(config) for config in detections]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"批量检测第{i}个任务失败: {result}")
                processed_results.append({
                    'hit': False,
                    'confidence': 0.0,
                    'evidence': '',
                    'rule_type': 'error',
                    'matched_patterns': []
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    def add_rule(self, 
                category: str,
                point: str,
                keywords: List[str] = None,
                patterns: List[str] = None) -> bool:
        """动态添加规则"""
        
        try:
            if category not in self.rules:
                self.rules[category] = {}
                self.compiled_patterns[category] = {}
            
            if point not in self.rules[category]:
                self.rules[category][point] = {'keywords': [], 'patterns': []}
                self.compiled_patterns[category][point] = {'keywords': [], 'patterns': []}
            
            # 添加关键词
            if keywords:
                self.rules[category][point]['keywords'].extend(keywords)
                self.compiled_patterns[category][point]['keywords'].extend(keywords)
            
            # 添加并编译正则表达式
            if patterns:
                for pattern in patterns:
                    try:
                        compiled_pattern = re.compile(pattern, re.IGNORECASE)
                        self.rules[category][point]['patterns'].append(pattern)
                        self.compiled_patterns[category][point]['patterns'].append(
                            (compiled_pattern, pattern)
                        )
                    except re.error as e:
                        logger.warning(f"编译新规则失败: {pattern}, 错误: {e}")
                        continue
            
            # 清除相关缓存
            cache_keys_to_remove = [
                key for key in self.rule_cache.keys() 
                if key.startswith(f"{category}_{point}_")
            ]
            for key in cache_keys_to_remove:
                del self.rule_cache[key]
            
            logger.info(f"成功添加规则: {category}.{point}")
            return True
            
        except Exception as e:
            logger.error(f"添加规则失败: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取引擎统计信息"""
        
        try:
            category_stats = {}
            total_rules = 0
            
            for category, category_rules in self.compiled_patterns.items():
                category_stats[category] = {}
                for point, rule_config in category_rules.items():
                    keyword_count = len(rule_config['keywords'])
                    pattern_count = len(rule_config['patterns'])
                    category_stats[category][point] = {
                        'keywords': keyword_count,
                        'patterns': pattern_count,
                        'total': keyword_count + pattern_count
                    }
                    total_rules += keyword_count + pattern_count
            
            return {
                'total_rules': total_rules,
                'categories': len(self.compiled_patterns),
                'cache_size': len(self.rule_cache),
                'category_breakdown': category_stats
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
    
    def clear_cache(self):
        """清除缓存"""
        self.rule_cache.clear()
        logger.info("规则引擎缓存已清除")