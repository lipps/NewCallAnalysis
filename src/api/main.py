"""FastAPI主应用"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import asyncio
import uuid
import json
from datetime import datetime
from pathlib import Path

from ..models.schemas import (
    CallInput, CallAnalysisResult, BatchAnalysisInput,
    AnalysisConfig, QualityMetrics, BatchFileProcessRequest,
    BatchFileProcessResponse, ParsedFileInput, BatchProcessingConfig
)
from ..workflows.simplified_workflow import SimpleCallAnalysisWorkflow as CallAnalysisWorkflow
from ..engines.vector_engine import get_vector_engine
from ..engines.rule_engine import RuleEngine
from ..engines.llm_engine import get_llm_engine
from ..config.settings import settings
from ..utils.logger import get_logger
from ..utils.batch_processor import get_batch_processor, get_result_storage
from ..utils.file_parser import validate_file_batch

logger = get_logger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=settings.description,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量
workflow_instance = None


async def get_workflow() -> CallAnalysisWorkflow:
    """获取工作流实例"""
    global workflow_instance
    
    if workflow_instance is None:
        # 初始化引擎
        vector_engine = await get_vector_engine()
        rule_engine = RuleEngine()
        llm_engine = get_llm_engine()
        
        # 创建工作流
        workflow_instance = CallAnalysisWorkflow(
            vector_engine=vector_engine,
            rule_engine=rule_engine,
            llm_engine=llm_engine
        )
        
        logger.info("工作流实例已创建")
    
    return workflow_instance


@app.on_event("startup")
async def startup_event():
    """启动事件"""
    logger.info(f"启动 {settings.app_name} v{settings.version}")
    
    try:
        # 预热工作流
        await get_workflow()
        logger.info("应用启动完成")
    except Exception as e:
        logger.error(f"启动失败: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """关闭事件"""
    logger.info("应用正在关闭...")
    
    try:
        # 清理资源
        vector_engine = await get_vector_engine()
        await vector_engine.close()
        logger.info("应用关闭完成")
    except Exception as e:
        logger.error(f"关闭时出错: {e}")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"欢迎使用 {settings.app_name}",
        "version": settings.version,
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        workflow = await get_workflow()
        
        # 检查各个组件
        llm_health = await workflow.llm_engine.health_check()
        vector_stats = workflow.vector_engine.get_statistics()
        rule_stats = workflow.rule_engine.get_statistics()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "llm_engine": llm_health,
                "vector_engine": {
                    "status": "healthy" if vector_stats.get("document_count", 0) > 0 else "warning",
                    "document_count": vector_stats.get("document_count", 0)
                },
                "rule_engine": {
                    "status": "healthy",
                    "total_rules": rule_stats.get("total_rules", 0)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy", 
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@app.post("/analyze", response_model=CallAnalysisResult)
async def analyze_call(
    call_input: CallInput,
    config: Optional[AnalysisConfig] = None,
    workflow: CallAnalysisWorkflow = Depends(get_workflow)
) -> CallAnalysisResult:
    """分析单个通话"""
    
    try:
        logger.info(f"开始分析通话: {call_input.call_id}")
        
        if not call_input.transcript.strip():
            raise HTTPException(status_code=400, detail="通话转写文本不能为空")
        
        # 执行分析
        result = await workflow.execute(call_input, config)
        
        logger.info(f"通话分析完成: {call_input.call_id}")
        return result
        
    except Exception as e:
        logger.error(f"分析通话失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@app.post("/analyze/batch")
async def analyze_batch(
    batch_input: BatchAnalysisInput,
    background_tasks: BackgroundTasks,
    config: Optional[AnalysisConfig] = None,
    workflow: CallAnalysisWorkflow = Depends(get_workflow)
):
    """批量分析通话"""
    
    try:
        if not batch_input.calls:
            raise HTTPException(status_code=400, detail="批量分析列表不能为空")
        
        logger.info(f"开始批量分析: {batch_input.batch_id}, 数量: {len(batch_input.calls)}")
        
        # 启动后台任务
        task_id = str(uuid.uuid4())
        background_tasks.add_task(
            _execute_batch_analysis,
            task_id, batch_input.calls, config, workflow
        )
        
        return {
            "task_id": task_id,
            "batch_id": batch_input.batch_id,
            "status": "processing",
            "call_count": len(batch_input.calls),
            "message": "批量分析任务已启动"
        }
        
    except Exception as e:
        logger.error(f"启动批量分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动失败: {str(e)}")


async def _execute_batch_analysis(
    task_id: str,
    calls: List[CallInput],
    config: Optional[AnalysisConfig],
    workflow: CallAnalysisWorkflow
):
    """执行批量分析（后台任务）"""
    
    try:
        logger.info(f"执行批量分析任务: {task_id}")
        
        results = await workflow.execute_batch(calls, config, max_concurrency=5)
        
        # 这里可以将结果保存到数据库或缓存
        # 目前只记录日志
        success_count = sum(1 for r in results if r.confidence_score > 0)
        logger.info(f"批量分析完成: {task_id}, 成功: {success_count}/{len(results)}")
        
    except Exception as e:
        logger.error(f"批量分析任务失败: {task_id}, 错误: {e}")


@app.post("/analyze/quality", response_model=QualityMetrics)
async def calculate_quality_metrics(
    result: CallAnalysisResult
) -> QualityMetrics:
    """计算质量指标"""
    
    try:
        # 计算各项得分
        icebreak_score = _calculate_icebreak_score(result.icebreak)
        deduction_score = _calculate_deduction_score(result.演绎)
        interaction_score = _calculate_interaction_score(result.process)
        
        # 计算完成度
        completion_rate = _calculate_completion_rate(result.actions)
        
        # 计算综合得分
        overall_score = (
            icebreak_score * 0.25 +
            deduction_score * 0.35 +
            interaction_score * 0.25 +
            completion_rate * 100 * 0.15
        )
        
        return QualityMetrics(
            overall_score=round(overall_score, 1),
            icebreak_score=round(icebreak_score, 1),
            deduction_score=round(deduction_score, 1),
            interaction_score=round(interaction_score, 1),
            completion_rate=round(completion_rate, 2)
        )
        
    except Exception as e:
        logger.error(f"计算质量指标失败: {e}")
        raise HTTPException(status_code=500, detail=f"计算失败: {str(e)}")


def _calculate_icebreak_score(icebreak_data) -> float:
    """计算破冰得分"""
    total_points = 5  # 破冰要点总数
    hit_points = 0
    
    for field_name in ['professional_identity', 'value_help', 'time_notice', 
                      'company_background', 'free_teach']:
        field_data = getattr(icebreak_data, field_name, None)
        if field_data and getattr(field_data, 'hit', False):
            hit_points += 1
    
    return (hit_points / total_points) * 100


def _calculate_deduction_score(deduction_data) -> float:
    """计算演绎得分"""
    total_points = 6  # 演绎要点总数
    hit_points = 0
    
    for field_name in ['bs_explained', 'period_resonance_explained', 'control_funds_explained',
                      'bubugao_explained', 'value_quantify_explained', 'customer_stock_explained']:
        field_data = getattr(deduction_data, field_name, None)
        if field_data and getattr(field_data, 'hit', False):
            hit_points += 1
    
    return (hit_points / total_points) * 100


def _calculate_interaction_score(process_data) -> float:
    """计算互动得分"""
    # 基于通话时长和互动频率计算
    duration = getattr(process_data, 'explain_duration_min', 0)
    interaction_rate = getattr(process_data, 'interaction_rounds_per_min', 0)
    
    # 理想的互动频率是每分钟1-3次
    ideal_rate = 2.0
    if interaction_rate == 0:
        return 0
    
    # 计算与理想值的偏差
    deviation = abs(interaction_rate - ideal_rate) / ideal_rate
    score = max(0, 100 - deviation * 50)
    
    # 时长加分（10-20分钟为理想时长）
    if 10 <= duration <= 20:
        score += 10
    elif duration > 5:
        score += 5
    
    return min(100, score)


def _calculate_completion_rate(actions_data) -> float:
    """计算完成度"""
    total_actions = 0
    completed_actions = 0
    
    for field_name in ['professional_identity', 'value_help', 'time_notice', 
                      'company_background', 'free_teach', 'bs_explained',
                      'period_resonance_explained', 'control_funds_explained',
                      'bubugao_explained', 'value_quantify_explained', 
                      'customer_stock_explained']:
        
        action_data = getattr(actions_data, field_name, None)
        if action_data:
            total_actions += 1
            if getattr(action_data, 'executed', False):
                completed_actions += 1
    
    return completed_actions / total_actions if total_actions > 0 else 0.0


@app.get("/statistics")
async def get_statistics(
    workflow: CallAnalysisWorkflow = Depends(get_workflow)
):
    """获取系统统计信息"""
    
    try:
        return {
            "vector_engine": workflow.vector_engine.get_statistics(),
            "rule_engine": workflow.rule_engine.get_statistics(),
            "llm_engine": workflow.llm_engine.get_statistics(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@app.post("/config/rules")
async def add_rule(
    category: str,
    point: str,
    keywords: List[str] = None,
    patterns: List[str] = None,
    workflow: CallAnalysisWorkflow = Depends(get_workflow)
):
    """动态添加规则"""
    
    try:
        success = workflow.rule_engine.add_rule(category, point, keywords, patterns)
        
        if success:
            return {
                "message": f"规则添加成功: {category}.{point}",
                "keywords_added": len(keywords) if keywords else 0,
                "patterns_added": len(patterns) if patterns else 0
            }
        else:
            raise HTTPException(status_code=500, detail="规则添加失败")
            
    except Exception as e:
        logger.error(f"添加规则失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加失败: {str(e)}")


# ========== 生产级批量文件处理接口 ==========

@app.post("/analyze/batch/files", response_model=BatchFileProcessResponse)
async def process_batch_files(
    request: BatchFileProcessRequest,
    workflow: CallAnalysisWorkflow = Depends(get_workflow)
):
    """
    批量文件处理接口 - 生产级实现

    支持多文件并发处理，具备完善的错误处理、进度跟踪和结果存储
    """
    try:
        # 请求验证
        if not request.files:
            raise HTTPException(status_code=400, detail="文件列表不能为空")

        # 配置验证
        batch_config = BatchProcessingConfig()

        # 验证文件批次
        is_valid, validation_errors = validate_file_batch(request.files, batch_config)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"批次验证失败: {'; '.join(validation_errors)}"
            )

        logger.info(
            f"开始处理批量文件请求: {request.batch_id}, "
            f"文件数: {len(request.files)}, "
            f"总通话数: {sum(len(f.calls) for f in request.files)}"
        )

        # 获取批量处理器
        processor = await get_batch_processor(workflow, batch_config)

        # 处理批量请求
        response = await processor.process_batch(request)

        logger.info(
            f"批量处理完成: {request.batch_id}, "
            f"状态: {response.status}, "
            f"成功率: {response.statistics.overall_success_rate:.1%}"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量文件处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@app.get("/analyze/batch/{batch_id}/status")
async def get_batch_status(batch_id: str):
    """
    查询批次处理状态（异步处理时使用）
    """
    try:
        storage = get_result_storage()

        # 尝试读取批次结果
        batch_dir = Path(storage.base_path) / batch_id
        summary_path = batch_dir / "batch_summary.json"

        if not summary_path.exists():
            raise HTTPException(status_code=404, detail=f"批次 {batch_id} 不存在或尚未完成")

        with open(summary_path, 'r', encoding='utf-8') as f:
            batch_data = json.load(f)

        return batch_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询批次状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@app.get("/analyze/batch/{batch_id}/download/{filename}")
async def download_file_result(batch_id: str, filename: str):
    """
    下载单个文件的分析结果
    """
    try:
        storage = get_result_storage()
        batch_dir = Path(storage.base_path) / batch_id

        # 查找匹配的结果文件
        result_files = list(batch_dir.glob("*.analysis.json"))
        target_file = None

        for result_file in result_files:
            with open(result_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get('source_filename') == filename:
                    target_file = result_file
                    break

        if not target_file:
            raise HTTPException(
                status_code=404,
                detail=f"文件 {filename} 的分析结果不存在"
            )

        # 返回文件内容
        with open(target_file, 'r', encoding='utf-8') as f:
            content = json.load(f)

        return content

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载文件结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


@app.delete("/analyze/batch/{batch_id}")
async def cleanup_batch_results(batch_id: str):
    """
    清理批次结果（手动清理）
    """
    try:
        storage = get_result_storage()
        batch_dir = Path(storage.base_path) / batch_id

        if not batch_dir.exists():
            raise HTTPException(status_code=404, detail=f"批次 {batch_id} 不存在")

        # 删除批次目录
        import shutil
        shutil.rmtree(batch_dir)

        logger.info(f"已清理批次结果: {batch_id}")

        return {"message": f"批次 {batch_id} 结果已清理"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清理批次结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@app.get("/analyze/batch/config")
async def get_batch_config():
    """
    获取批量处理配置信息
    """
    config = BatchProcessingConfig()
    return {
        "config": config.dict(),
        "supported_file_types": [".json", ".jsonl", ".csv", ".txt"],
        "limits": {
            "max_files_per_batch": config.max_files_per_batch,
            "max_calls_per_batch": config.max_calls_per_batch,
            "max_file_size_mb": config.max_file_size_mb,
            "max_concurrent_files": config.max_concurrent_files
        }
    }


@app.post("/analyze/batch/cleanup-expired")
async def cleanup_expired_batches():
    """
    清理过期的批次结果（定时任务接口）
    """
    try:
        storage = get_result_storage()
        config = BatchProcessingConfig()

        storage.cleanup_expired_results(config.result_retention_hours)

        return {"message": "过期批次清理完成"}

    except Exception as e:
        logger.error(f"清理过期批次失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.api.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload,
        log_level=settings.logging.log_level.lower()
    )