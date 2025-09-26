"""
生产级批量处理管理器
负责文件批量分析的调度、执行、结果管理和存储
"""

import asyncio
import json
import uuid
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable
import time
import psutil
from concurrent.futures import ThreadPoolExecutor

from ..models.schemas import (
    ParsedFileInput, BatchFileProcessRequest, BatchFileProcessResponse,
    FileProcessingResult, FileProcessingMetrics, BatchProcessingStatistics,
    BatchFileProcessStatus, CallAnalysisResult, AnalysisConfig,
    BatchProcessingConfig
)
from ..workflows.simplified_workflow import SimpleCallAnalysisWorkflow
from ..utils.logger import get_logger

logger = get_logger(__name__)


class BatchProcessingError(Exception):
    """批量处理错误"""
    pass


class ResultStorage:
    """结果存储管理器"""

    def __init__(self, base_path: str = "./batch_results"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_file_result(self,
                        batch_id: str,
                        filename: str,
                        results: List[CallAnalysisResult]) -> str:
        """保存单个文件的分析结果"""
        batch_dir = self.base_path / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)

        # 生成安全的文件名
        safe_filename = self._sanitize_filename(filename)
        result_filename = f"{safe_filename}.analysis.json"
        result_path = batch_dir / result_filename

        # 序列化结果
        serialized_results = [result.dict() for result in results]

        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump({
                'source_filename': filename,
                'analysis_results': serialized_results,
                'result_count': len(results),
                'generated_at': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)

        logger.info(f"保存文件结果: {result_path}")
        return str(result_path)

    def save_batch_summary(self,
                          batch_id: str,
                          response: BatchFileProcessResponse) -> str:
        """保存批次汇总结果"""
        batch_dir = self.base_path / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)

        summary_path = batch_dir / "batch_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(response.dict(), f, ensure_ascii=False, indent=2)

        logger.info(f"保存批次汇总: {summary_path}")
        return str(summary_path)

    def cleanup_expired_results(self, retention_hours: int = 24):
        """清理过期的结果文件"""
        cutoff_time = datetime.now() - timedelta(hours=retention_hours)
        cleaned_count = 0

        for batch_dir in self.base_path.iterdir():
            if not batch_dir.is_dir():
                continue

            # 检查目录修改时间
            dir_mtime = datetime.fromtimestamp(batch_dir.stat().st_mtime)
            if dir_mtime < cutoff_time:
                try:
                    import shutil
                    shutil.rmtree(batch_dir)
                    cleaned_count += 1
                    logger.info(f"清理过期批次: {batch_dir.name}")
                except Exception as e:
                    logger.error(f"清理批次 {batch_dir.name} 失败: {e}")

        logger.info(f"清理完成，删除了 {cleaned_count} 个过期批次")

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """清理文件名中的非法字符"""
        import re
        # 移除文件扩展名
        name_without_ext = Path(filename).stem
        # 替换非法字符
        safe_name = re.sub(r'[^\w\-_\.]', '_', name_without_ext)
        # 限制长度
        return safe_name[:50]


class ProgressTracker:
    """进度跟踪器"""

    def __init__(self, batch_id: str, total_files: int):
        self.batch_id = batch_id
        self.total_files = total_files
        self.completed_files = 0
        self.failed_files = 0
        self.start_time = time.time()
        self.callbacks: List[Callable] = []

    def add_progress_callback(self, callback: Callable):
        """添加进度回调函数"""
        self.callbacks.append(callback)

    async def update_progress(self, file_result: FileProcessingResult):
        """更新进度"""
        if file_result.status == BatchFileProcessStatus.SUCCESS:
            self.completed_files += 1
        else:
            self.failed_files += 1

        progress_info = {
            'batch_id': self.batch_id,
            'total_files': self.total_files,
            'completed_files': self.completed_files,
            'failed_files': self.failed_files,
            'progress_percentage': (self.completed_files + self.failed_files) / self.total_files * 100,
            'elapsed_time': time.time() - self.start_time
        }

        # 调用所有回调函数
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(progress_info)
                else:
                    callback(progress_info)
            except Exception as e:
                logger.error(f"进度回调执行失败: {e}")


class BatchProcessor:
    """批量处理管理器"""

    def __init__(self,
                 workflow: SimpleCallAnalysisWorkflow,
                 config: BatchProcessingConfig,
                 storage: Optional[ResultStorage] = None):
        self.workflow = workflow
        self.config = config
        self.storage = storage or ResultStorage()

        # 性能监控
        self.process = psutil.Process()

    async def process_batch(self,
                           request: BatchFileProcessRequest,
                           progress_callback: Optional[Callable] = None) -> BatchFileProcessResponse:
        """处理批量文件请求"""
        start_time = datetime.now()
        batch_id = request.batch_id

        logger.info(f"开始处理批次 {batch_id}, 文件数: {len(request.files)}")

        # 初始化进度跟踪
        progress_tracker = ProgressTracker(batch_id, len(request.files))
        if progress_callback:
            progress_tracker.add_progress_callback(progress_callback)

        # 过滤有效文件
        valid_files = [f for f in request.files if f.parse_status.value == "success"]
        if not valid_files:
            return self._create_failed_response(
                request, start_time, "没有有效的文件可处理"
            )

        # 并发处理文件
        processing_options = request.processing_options
        max_concurrency = min(
            processing_options.get('max_concurrency', 3),
            self.config.max_concurrent_files
        )

        semaphore = asyncio.Semaphore(max_concurrency)
        tasks = []

        for file_input in valid_files:
            task = asyncio.create_task(
                self._process_single_file(
                    file_input,
                    request.config,
                    semaphore,
                    progress_tracker,
                    batch_id
                )
            )
            tasks.append(task)

        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        file_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"处理文件 {valid_files[i].source_filename} 异常: {result}")
                file_results.append(
                    self._create_failed_file_result(
                        valid_files[i].source_filename,
                        f"处理异常: {str(result)}"
                    )
                )
            else:
                file_results.append(result)

        # 添加解析失败的文件到结果中
        for file_input in request.files:
            if file_input.parse_status.value != "success":
                file_results.append(
                    self._create_failed_file_result(
                        file_input.source_filename,
                        file_input.parse_error or "文件解析失败"
                    )
                )

        # 生成统计信息
        end_time = datetime.now()
        statistics = self._calculate_statistics(file_results, start_time, end_time)

        # 确定批次状态
        batch_status = self._determine_batch_status(statistics)

        # 创建响应
        response = BatchFileProcessResponse(
            batch_id=batch_id,
            status=batch_status,
            files=file_results,
            statistics=statistics,
            processing_start_time=start_time.isoformat(),
            processing_end_time=end_time.isoformat()
        )

        # 保存结果
        if processing_options.get('result_storage', 'local') == 'local':
            batch_result_path = self.storage.save_batch_summary(batch_id, response)
            response.batch_result_path = batch_result_path

        logger.info(
            f"批次 {batch_id} 处理完成: "
            f"成功 {statistics.successful_files}, "
            f"失败 {statistics.failed_files}, "
            f"耗时 {statistics.total_duration_seconds:.1f}s"
        )

        return response

    async def _process_single_file(self,
                                  file_input: ParsedFileInput,
                                  config: Optional[AnalysisConfig],
                                  semaphore: asyncio.Semaphore,
                                  progress_tracker: ProgressTracker,
                                  batch_id: str) -> FileProcessingResult:
        """处理单个文件"""
        filename = file_input.source_filename
        start_time = time.time()
        memory_before = self.process.memory_info().rss / 1024 / 1024  # MB

        async with semaphore:
            try:
                logger.info(f"开始处理文件: {filename}, 通话数: {len(file_input.calls)}")

                # 分析通话
                analysis_results = await self.workflow.execute_batch(
                    file_input.calls,
                    config,
                    max_concurrency=self.config.max_concurrent_files
                )

                # 计算指标
                end_time = time.time()
                duration = end_time - start_time
                memory_after = self.process.memory_info().rss / 1024 / 1024  # MB

                avg_confidence = sum(
                    result.confidence_score for result in analysis_results
                ) / len(analysis_results) if analysis_results else 0.0

                metrics = FileProcessingMetrics(
                    call_count=len(analysis_results),
                    processing_duration_seconds=duration,
                    average_confidence=avg_confidence,
                    memory_usage_mb=max(0, memory_after - memory_before)
                )

                # 保存文件结果
                result_path = None
                try:
                    result_path = self.storage.save_file_result(
                        batch_id, filename, analysis_results
                    )
                except Exception as e:
                    logger.error(f"保存文件结果失败: {e}")

                file_result = FileProcessingResult(
                    source_filename=filename,
                    status=BatchFileProcessStatus.SUCCESS,
                    results=analysis_results,
                    metrics=metrics,
                    processed_at=datetime.now().isoformat(),
                    result_file_path=result_path
                )

                logger.info(
                    f"文件 {filename} 处理完成: "
                    f"{len(analysis_results)} 条结果, "
                    f"耗时 {duration:.1f}s, "
                    f"平均置信度 {avg_confidence:.2f}"
                )

                await progress_tracker.update_progress(file_result)
                return file_result

            except Exception as e:
                logger.error(f"处理文件 {filename} 失败: {e}")
                logger.error(traceback.format_exc())

                file_result = self._create_failed_file_result(filename, str(e))
                await progress_tracker.update_progress(file_result)
                return file_result

    def _create_failed_file_result(self,
                                  filename: str,
                                  error_message: str) -> FileProcessingResult:
        """创建失败的文件处理结果"""
        return FileProcessingResult(
            source_filename=filename,
            status=BatchFileProcessStatus.FAILED,
            results=[],
            error_message=error_message,
            processed_at=datetime.now().isoformat()
        )

    def _create_failed_response(self,
                               request: BatchFileProcessRequest,
                               start_time: datetime,
                               error_message: str) -> BatchFileProcessResponse:
        """创建失败的批次响应"""
        end_time = datetime.now()
        failed_results = [
            self._create_failed_file_result(f.source_filename, error_message)
            for f in request.files
        ]

        statistics = BatchProcessingStatistics(
            total_files=len(request.files),
            successful_files=0,
            failed_files=len(request.files),
            partial_success_files=0,
            total_calls_processed=0,
            total_duration_seconds=(end_time - start_time).total_seconds(),
            average_calls_per_file=0.0,
            processing_rate_calls_per_second=0.0,
            overall_success_rate=0.0
        )

        return BatchFileProcessResponse(
            batch_id=request.batch_id,
            status=BatchFileProcessStatus.FAILED,
            files=failed_results,
            statistics=statistics,
            processing_start_time=start_time.isoformat(),
            processing_end_time=end_time.isoformat()
        )

    def _calculate_statistics(self,
                             file_results: List[FileProcessingResult],
                             start_time: datetime,
                             end_time: datetime) -> BatchProcessingStatistics:
        """计算批量处理统计信息"""
        total_files = len(file_results)
        successful_files = sum(1 for r in file_results if r.status == BatchFileProcessStatus.SUCCESS)
        failed_files = sum(1 for r in file_results if r.status == BatchFileProcessStatus.FAILED)
        partial_success_files = sum(1 for r in file_results if r.status == BatchFileProcessStatus.PARTIAL_SUCCESS)

        total_calls = sum(len(r.results) for r in file_results)
        total_duration = (end_time - start_time).total_seconds()

        return BatchProcessingStatistics(
            total_files=total_files,
            successful_files=successful_files,
            failed_files=failed_files,
            partial_success_files=partial_success_files,
            total_calls_processed=total_calls,
            total_duration_seconds=total_duration,
            average_calls_per_file=total_calls / total_files if total_files > 0 else 0.0,
            processing_rate_calls_per_second=total_calls / total_duration if total_duration > 0 else 0.0,
            overall_success_rate=successful_files / total_files if total_files > 0 else 0.0
        )

    def _determine_batch_status(self, statistics: BatchProcessingStatistics) -> BatchFileProcessStatus:
        """确定批次处理状态"""
        if statistics.successful_files == statistics.total_files:
            return BatchFileProcessStatus.SUCCESS
        elif statistics.successful_files == 0:
            return BatchFileProcessStatus.FAILED
        else:
            return BatchFileProcessStatus.PARTIAL_SUCCESS


# 全局实例管理
_global_processor: Optional[BatchProcessor] = None
_global_storage: Optional[ResultStorage] = None


def get_result_storage() -> ResultStorage:
    """获取全局结果存储实例"""
    global _global_storage
    if _global_storage is None:
        _global_storage = ResultStorage()
    return _global_storage


async def get_batch_processor(workflow: SimpleCallAnalysisWorkflow,
                             config: Optional[BatchProcessingConfig] = None) -> BatchProcessor:
    """获取批量处理器实例"""
    global _global_processor

    if _global_processor is None:
        processing_config = config or BatchProcessingConfig()
        storage = get_result_storage()
        _global_processor = BatchProcessor(workflow, processing_config, storage)
        logger.info("初始化全局批量处理器")

    return _global_processor


async def cleanup_batch_processor():
    """清理批量处理器资源"""
    global _global_processor
    _global_processor = None
    logger.info("批量处理器已清理")