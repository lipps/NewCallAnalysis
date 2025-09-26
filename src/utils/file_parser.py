"""
生产级文件解析器模块
支持JSON/CSV/TXT文件解析，具备完善的错误处理、内存优化和扩展性
"""

import json
import csv
import io
import re
import traceback
from typing import List, Dict, Any, Optional, Union, Tuple, Iterator
from datetime import datetime
from pathlib import Path
import tempfile
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from pydantic import ValidationError

from ..models.schemas import (
    CallInput, ParsedFileInput, FileParseStatus,
    BatchProcessingConfig
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


class FileParserError(Exception):
    """文件解析错误基类"""
    pass


class FileSizeError(FileParserError):
    """文件大小超限错误"""
    pass


class FileFormatError(FileParserError):
    """文件格式错误"""
    pass


class FileContentError(FileParserError):
    """文件内容错误"""
    pass


class StreamingFileParser:
    """流式文件解析器 - 生产级实现"""

    def __init__(self, config: Optional[BatchProcessingConfig] = None):
        self.config = config or BatchProcessingConfig()
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="FileParser")

        # 支持的文件类型
        self.supported_extensions = {'.json', '.jsonl', '.csv', '.txt'}

        # 编码检测优先级
        self.encoding_priority = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'ascii']

    async def parse_files(self,
                         uploaded_files: List[Any],
                         batch_id: str) -> List[ParsedFileInput]:
        """
        异步解析多个文件

        Args:
            uploaded_files: Streamlit上传的文件对象列表
            batch_id: 批次ID

        Returns:
            解析结果列表
        """
        tasks = []
        for file_obj in uploaded_files:
            task = asyncio.create_task(
                self._parse_single_file_async(file_obj, batch_id)
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常结果
        parsed_files = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                filename = getattr(uploaded_files[i], 'name', f'file_{i}')
                logger.error(f"解析文件 {filename} 失败: {result}")
                parsed_files.append(self._create_failed_result(filename, str(result)))
            else:
                parsed_files.append(result)

        return parsed_files

    async def _parse_single_file_async(self,
                                      file_obj: Any,
                                      batch_id: str) -> ParsedFileInput:
        """异步解析单个文件"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._parse_single_file_sync,
            file_obj,
            batch_id
        )

    def _parse_single_file_sync(self, file_obj: Any, batch_id: str) -> ParsedFileInput:
        """同步解析单个文件"""
        filename = getattr(file_obj, 'name', 'unknown_file')
        start_time = datetime.now()

        try:
            # 文件大小检查
            file_size = getattr(file_obj, 'size', 0)
            if file_size > self.config.max_file_size_mb * 1024 * 1024:
                raise FileSizeError(
                    f"文件大小 {file_size/1024/1024:.1f}MB 超过限制 {self.config.max_file_size_mb}MB"
                )

            # 文件扩展名检查
            file_ext = Path(filename).suffix.lower()
            if file_ext not in self.supported_extensions:
                raise FileFormatError(f"不支持的文件类型: {file_ext}")

            # 读取文件内容
            file_content = self._read_file_content(file_obj)

            # 根据文件类型解析
            calls, warnings = self._parse_by_extension(file_ext, file_content, filename)

            # 验证解析结果
            if not calls:
                warnings.append("文件中未找到有效的通话记录")

            # 通话数量检查
            if len(calls) > self.config.max_calls_per_batch:
                warnings.append(
                    f"通话数量 {len(calls)} 超过批次限制 {self.config.max_calls_per_batch}，将截取前 {self.config.max_calls_per_batch} 条"
                )
                calls = calls[:self.config.max_calls_per_batch]

            logger.info(f"成功解析文件 {filename}: {len(calls)} 条通话记录")

            return ParsedFileInput(
                source_filename=filename,
                file_size_bytes=file_size,
                parse_status=FileParseStatus.SUCCESS,
                calls=calls,
                parse_warnings=warnings,
                parsed_at=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"解析文件 {filename} 失败: {e}")
            return self._create_failed_result(filename, str(e), getattr(file_obj, 'size', 0))

    def _read_file_content(self, file_obj: Any) -> str:
        """读取文件内容并自动检测编码"""
        content_bytes = file_obj.read()

        # 尝试不同编码
        for encoding in self.encoding_priority:
            try:
                content = content_bytes.decode(encoding)
                logger.debug(f"使用编码 {encoding} 成功读取文件")
                return content
            except UnicodeDecodeError:
                continue

        # 所有编码都失败，使用错误处理模式
        content = content_bytes.decode('utf-8', errors='replace')
        logger.warning("使用fallback编码读取文件，可能存在字符错误")
        return content

    def _parse_by_extension(self,
                           file_ext: str,
                           content: str,
                           filename: str) -> Tuple[List[CallInput], List[str]]:
        """根据文件扩展名选择解析方法"""
        warnings = []

        if file_ext == '.json':
            return self._parse_json(content, warnings)
        elif file_ext == '.jsonl':
            return self._parse_jsonl(content, warnings)
        elif file_ext == '.csv':
            return self._parse_csv(content, warnings)
        elif file_ext == '.txt':
            return self._parse_txt(content, filename, warnings)
        else:
            raise FileFormatError(f"不支持的文件类型: {file_ext}")

    def _parse_json(self, content: str, warnings: List[str]) -> Tuple[List[CallInput], List[str]]:
        """解析JSON文件"""
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise FileContentError(f"JSON格式错误: {e}")

        calls = []

        # 支持多种JSON结构
        if isinstance(data, list):
            # List[CallInput] 或 List[Dict]
            for i, item in enumerate(data):
                try:
                    call_input = self._dict_to_call_input(item, f"item_{i}")
                    calls.append(call_input)
                except ValidationError as e:
                    warnings.append(f"第 {i+1} 条记录验证失败: {e}")

        elif isinstance(data, dict):
            if 'calls' in data:
                # {"calls": [...]} 结构
                for i, item in enumerate(data['calls']):
                    try:
                        call_input = self._dict_to_call_input(item, f"call_{i}")
                        calls.append(call_input)
                    except ValidationError as e:
                        warnings.append(f"calls[{i}] 验证失败: {e}")
            else:
                # 单个CallInput对象
                try:
                    call_input = self._dict_to_call_input(data, "single_call")
                    calls.append(call_input)
                except ValidationError as e:
                    raise FileContentError(f"JSON对象验证失败: {e}")
        else:
            raise FileContentError("JSON根节点必须是对象或数组")

        return calls, warnings

    def _parse_jsonl(self, content: str, warnings: List[str]) -> Tuple[List[CallInput], List[str]]:
        """解析JSONL文件（每行一个JSON对象）"""
        calls = []
        lines = content.strip().split('\n')

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
                call_input = self._dict_to_call_input(data, f"line_{line_num}")
                calls.append(call_input)
            except json.JSONDecodeError as e:
                warnings.append(f"第 {line_num} 行JSON格式错误: {e}")
            except ValidationError as e:
                warnings.append(f"第 {line_num} 行数据验证失败: {e}")

        return calls, warnings

    def _parse_csv(self, content: str, warnings: List[str]) -> Tuple[List[CallInput], List[str]]:
        """解析CSV文件"""
        try:
            # 使用pandas读取CSV，支持自动类型推断
            df = pd.read_csv(io.StringIO(content))
        except Exception as e:
            raise FileContentError(f"CSV读取失败: {e}")

        # 检查必需列
        required_columns = {'transcript'}
        available_columns = set(df.columns.str.lower())

        if not required_columns.issubset(available_columns):
            missing = required_columns - available_columns
            raise FileContentError(f"CSV文件缺少必需列: {missing}")

        calls = []
        for index, row in df.iterrows():
            try:
                # 构建CallInput数据
                call_data = {
                    'call_id': str(row.get('call_id', f'csv_row_{index}')),
                    'transcript': str(row['transcript']).strip(),
                }

                # 可选字段
                optional_fields = ['customer_id', 'sales_id', 'call_time']
                for field in optional_fields:
                    if field in df.columns and pd.notna(row[field]):
                        call_data[field] = str(row[field])

                # 验证transcript不为空
                if not call_data['transcript'] or call_data['transcript'] == 'nan':
                    warnings.append(f"第 {index+1} 行transcript为空，跳过")
                    continue

                call_input = CallInput(**call_data)
                calls.append(call_input)

            except ValidationError as e:
                warnings.append(f"第 {index+1} 行数据验证失败: {e}")
            except Exception as e:
                warnings.append(f"第 {index+1} 行处理失败: {e}")

        return calls, warnings

    def _parse_txt(self,
                   content: str,
                   filename: str,
                   warnings: List[str]) -> Tuple[List[CallInput], List[str]]:
        """解析TXT文件"""
        calls = []

        # 清理内容
        content = content.strip()
        if not content:
            return calls, ["TXT文件内容为空"]

        # 检查是否包含多个对话分隔符
        # 支持常见的分隔符模式
        separators = [
            r'\n---+\n',           # --- 分隔符
            r'\n={3,}\n',          # === 分隔符
            r'\n通话\d+[：:]\n',   # 通话1: 分隔符
            r'\n\[对话\d+\]\n',   # [对话1] 分隔符
        ]

        segments = [content]  # 默认整个文件为一个对话

        # 尝试分割
        for separator_pattern in separators:
            potential_segments = re.split(separator_pattern, content, flags=re.MULTILINE | re.IGNORECASE)
            if len(potential_segments) > 1:
                segments = [seg.strip() for seg in potential_segments if seg.strip()]
                logger.info(f"检测到分隔符，分割为 {len(segments)} 个对话段")
                break

        # 处理每个对话段
        for i, segment in enumerate(segments):
            if len(segment) < 10:  # 过滤过短的段落
                warnings.append(f"第 {i+1} 个对话段内容过短，跳过")
                continue

            try:
                call_id = f"{Path(filename).stem}_part_{i+1}" if len(segments) > 1 else Path(filename).stem

                call_input = CallInput(
                    call_id=call_id,
                    transcript=segment.strip(),
                    metadata={'source_file': filename, 'segment_index': i}
                )
                calls.append(call_input)

            except ValidationError as e:
                warnings.append(f"第 {i+1} 个对话段验证失败: {e}")

        return calls, warnings

    def _dict_to_call_input(self, data: Dict[str, Any], fallback_id: str) -> CallInput:
        """将字典转换为CallInput对象"""
        # 确保call_id存在
        if 'call_id' not in data:
            data['call_id'] = fallback_id

        # 确保transcript存在且非空
        if 'transcript' not in data or not data['transcript']:
            raise ValidationError("transcript字段缺失或为空")

        return CallInput(**data)

    def _create_failed_result(self,
                             filename: str,
                             error_msg: str,
                             file_size: int = 0) -> ParsedFileInput:
        """创建失败的解析结果"""
        return ParsedFileInput(
            source_filename=filename,
            file_size_bytes=file_size,
            parse_status=FileParseStatus.FAILED,
            calls=[],
            parse_error=error_msg,
            parsed_at=datetime.now().isoformat()
        )

    async def cleanup(self):
        """清理资源"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
            logger.debug("文件解析器线程池已关闭")


# 全局解析器实例
_global_parser: Optional[StreamingFileParser] = None


async def get_file_parser(config: Optional[BatchProcessingConfig] = None) -> StreamingFileParser:
    """获取全局文件解析器实例"""
    global _global_parser

    if _global_parser is None:
        _global_parser = StreamingFileParser(config)
        logger.info("初始化全局文件解析器")

    return _global_parser


async def cleanup_file_parser():
    """清理全局文件解析器"""
    global _global_parser

    if _global_parser is not None:
        await _global_parser.cleanup()
        _global_parser = None
        logger.info("全局文件解析器已清理")


# 便利函数
async def parse_uploaded_files(uploaded_files: List[Any],
                              batch_id: str,
                              config: Optional[BatchProcessingConfig] = None) -> List[ParsedFileInput]:
    """
    解析上传的文件列表

    Args:
        uploaded_files: 上传的文件对象列表
        batch_id: 批次ID
        config: 批量处理配置

    Returns:
        解析结果列表
    """
    parser = await get_file_parser(config)
    return await parser.parse_files(uploaded_files, batch_id)


def validate_file_batch(files: List[ParsedFileInput],
                       config: BatchProcessingConfig) -> Tuple[bool, List[str]]:
    """
    验证文件批次是否符合处理要求

    Args:
        files: 解析后的文件列表
        config: 批量处理配置

    Returns:
        (是否有效, 错误信息列表)
    """
    errors = []

    # 检查文件数量
    if len(files) > config.max_files_per_batch:
        errors.append(f"文件数量 {len(files)} 超过限制 {config.max_files_per_batch}")

    # 检查总通话数量
    total_calls = sum(len(f.calls) for f in files)
    if total_calls > config.max_calls_per_batch:
        errors.append(f"总通话数量 {total_calls} 超过限制 {config.max_calls_per_batch}")

    # 检查是否有成功解析的文件
    successful_files = [f for f in files if f.parse_status == FileParseStatus.SUCCESS]
    if not successful_files:
        errors.append("没有成功解析的文件")

    return len(errors) == 0, errors