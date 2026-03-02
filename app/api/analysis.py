"""分析 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List
import uuid
from datetime import datetime

from app.db.database import get_db
from app.db.models import News, Analysis
from app.models.schemas import (
    NewsSubmitRequest,
    BatchSubmitRequest,
    SubmitResponse,
    BatchSubmitResponse,
    AnalysisResponse,
    AnalysisOverview,
    ErrorResponse
)
from app.services.queue.rabbitmq import rabbitmq_service

router = APIRouter(prefix="/api/v1/analysis", tags=["Analysis"])


@router.post("/submit", response_model=SubmitResponse)
async def submit_analysis(
    request: NewsSubmitRequest,
    db: Session = Depends(get_db)
):
    """
    提交单条快讯分析
    
    可以通过以下方式提交：
    1. 提供 news_id - 分析已存在的快讯
    2. 提供 title 和 content - 创建新快讯并分析
    """
    # 获取或创建快讯
    if request.news_id:
        news = db.query(News).filter(News.id == request.news_id).first()
        if not news:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"News with id {request.news_id} not found"
            )
    elif request.title and request.content:
        # 创建新快讯
        news = News(
            odaily_id=f"manual_{uuid.uuid4().hex[:8]}",
            title=request.title,
            content=request.content,
            published_at=datetime.utcnow()
        )
        db.add(news)
        db.commit()
        db.refresh(news)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either news_id or (title and content) must be provided"
        )
    
    # 生成任务 ID
    task_id = f"task_{news.id}_{int(datetime.utcnow().timestamp())}"
    
    # 发送到消息队列
    message = {
        "task_id": task_id,
        "news_id": news.id
    }
    
    success = rabbitmq_service.publish(message)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit analysis task"
        )
    
    return SubmitResponse(
        task_id=task_id,
        news_id=news.id,
        message="Analysis task submitted successfully"
    )


@router.post("/batch", response_model=BatchSubmitResponse)
async def batch_submit_analysis(
    request: BatchSubmitRequest,
    db: Session = Depends(get_db)
):
    """
    批量提交分析任务
    
    - 会检查每个快讯是否存在
    - 返回所有提交结果，包括成功和失败的
    - 失败的任务会在 message 中说明原因
    """
    tasks = []
    
    # 调试日志：记录接收到的 news_ids
    print(f"[DEBUG] 批量提交接收到的 news_ids: {request.news_ids}")
    print(f"[DEBUG] news_ids 数量: {len(request.news_ids)}")
    
    for index, news_id in enumerate(request.news_ids):
        print(f"[DEBUG] 处理第 {index} 个 ID: {news_id}")
    for index, news_id in enumerate(request.news_ids):
        print(f"[DEBUG] 处理第 {index} 个 ID: {news_id}")
        # 检查快讯是否存在
        news = db.query(News).filter(News.id == news_id).first()
        if not news:
            print(f"[DEBUG] News ID {news_id} 不存在")
            # 记录失败的任务
            tasks.append(SubmitResponse(
                task_id=f"failed_{news_id}",
                news_id=news_id,
                message=f"Failed: News with id {news_id} not found"
            ))
            continue
        
        print(f"[DEBUG] News ID {news_id} 存在，准备提交到队列")
        # 生成任务 ID
        task_id = f"task_{news_id}_{int(datetime.utcnow().timestamp())}"
        
        # 发送到消息队列
        message = {
            "task_id": task_id,
            "news_id": news_id
        }
        
        if rabbitmq_service.publish(message):
            print(f"[DEBUG] News ID {news_id} 成功发送到队列")
            tasks.append(SubmitResponse(
                task_id=task_id,
                news_id=news_id,
                message="Submitted successfully"
            ))
        else:
            print(f"[DEBUG] News ID {news_id} 发送到队列失败")
            # 记录发送失败的任务
            tasks.append(SubmitResponse(
                task_id=f"failed_{news_id}",
                news_id=news_id,
                message="Failed: Unable to publish to message queue"
            ))
    
    # 统计成功和失败数量
    success_count = sum(1 for task in tasks if not task.task_id.startswith("failed_"))
    failed_count = len(tasks) - success_count
    
    print(f"[DEBUG] 处理完成: 总共 {len(tasks)} 个任务，成功 {success_count} 个，失败 {failed_count} 个")
    print(f"[DEBUG] 返回的 tasks: {[{'news_id': t.news_id, 'task_id': t.task_id} for t in tasks]}")
    
    return BatchSubmitResponse(
        tasks=tasks,
        total=len(tasks),
        message=f"Batch submit completed: {success_count} succeeded, {failed_count} failed"
    )


@router.get("/{news_id}", response_model=AnalysisResponse)
async def get_analysis(
    news_id: int,
    db: Session = Depends(get_db)
):
    """查询分析结果"""
    analysis = db.query(Analysis).filter(
        Analysis.news_id == news_id
    ).order_by(desc(Analysis.created_at)).first()
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis for news {news_id} not found"
        )
    
    return analysis


@router.get("/", response_model=List[AnalysisResponse])
async def list_analyses(
    skip: int = 0,
    limit: int = 20,
    status: str = None,
    db: Session = Depends(get_db)
):
    """查询分析列表"""
    query = db.query(Analysis)
    
    if status:
        query = query.filter(Analysis.pipeline_status == status)
    
    analyses = query.order_by(desc(Analysis.created_at)).offset(skip).limit(limit).all()
    
    return analyses


@router.get("/overview/stats", response_model=AnalysisOverview)
async def get_analysis_overview(db: Session = Depends(get_db)):
    """获取分析概览统计"""
    # 总数统计
    total = db.query(func.count(Analysis.id)).scalar()
    completed = db.query(func.count(Analysis.id)).filter(
        Analysis.pipeline_status == "completed"
    ).scalar()
    pending = db.query(func.count(Analysis.id)).filter(
        Analysis.pipeline_status == "pending"
    ).scalar()
    failed = db.query(func.count(Analysis.id)).filter(
        Analysis.pipeline_status == "failed"
    ).scalar()
    
    # 投资价值分布
    has_value = db.query(func.count(Analysis.id)).filter(
        Analysis.has_investment_value == True
    ).scalar()
    no_value = db.query(func.count(Analysis.id)).filter(
        Analysis.has_investment_value == False
    ).scalar()
    
    # 建议分布
    buy_count = db.query(func.count(Analysis.id)).filter(
        Analysis.recommendation == "BUY"
    ).scalar()
    sell_count = db.query(func.count(Analysis.id)).filter(
        Analysis.recommendation == "SELL"
    ).scalar()
    hold_count = db.query(func.count(Analysis.id)).filter(
        Analysis.recommendation == "HOLD"
    ).scalar()
    
    # 热门代币（需要从 JSON 字段中统计）
    # 这里简化处理，实际应该用更复杂的查询
    top_tokens = []
    
    # 平均置信度
    avg_confidence = db.query(func.avg(Analysis.confidence_score)).filter(
        Analysis.confidence_score.isnot(None)
    ).scalar() or 0.0
    
    return AnalysisOverview(
        total_analyses=total or 0,
        completed=completed or 0,
        pending=pending or 0,
        failed=failed or 0,
        has_value_count=has_value or 0,
        no_value_count=no_value or 0,
        buy_count=buy_count or 0,
        sell_count=sell_count or 0,
        hold_count=hold_count or 0,
        top_tokens=top_tokens,
        avg_confidence=float(avg_confidence)
    )
