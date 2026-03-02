"""RabbitMQ Worker - 消费分析任务"""
import signal
import sys
import threading
from datetime import datetime
from app.services.queue.rabbitmq import rabbitmq_service
from app.services.analysis.pipeline import AnalysisPipeline
from app.services.rag.rag_service import RAGService
from app.services.market.coingecko_service import CoinGeckoService
from app.services.graph.graph_rag_service import GraphRAGService
from app.core.config import settings
from app.db.database import get_db_context
from app.db.models import News, Analysis, TaskRecord
from app.core.config import settings


class AnalysisWorker:
    """分析任务 Worker"""
    
    def __init__(self):
        # 设置 LangSmith 环境变量（确保在 Worker 线程中也能追踪）
        import os
        os.environ["LANGCHAIN_TRACING_V2"] = str(settings.LANGCHAIN_TRACING_V2).lower()
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
        
        self.rag_service = RAGService()
        self.market_service = CoinGeckoService()
        self.graph_rag_service = GraphRAGService()  # 初始化知识图谱服务
        
        self.pipeline = AnalysisPipeline(
            market_service=self.market_service,
            graph_rag_service=self.graph_rag_service  # 传入知识图谱服务
        )
        self.running = True
    
    def process_task(self, message: dict) -> bool:
        """
        处理分析任务
        
        Args:
            message: 任务消息
            
        Returns:
            是否处理成功
        """
        task_id = message.get("task_id")
        news_id = message.get("news_id")
        
        if not task_id or not news_id:
            print(f"Invalid message: {message}")
            return False
        
        print(f"Processing task {task_id} for news {news_id}")
        
        with get_db_context() as db:
            # 幂等性检查
            existing_task = db.query(TaskRecord).filter(
                TaskRecord.task_id == task_id
            ).first()
            
            if existing_task:
                if existing_task.status == "completed":
                    print(f"Task {task_id} already completed, skipping")
                    return True
                
                # 检查重试次数
                if existing_task.retry_count >= settings.MAX_RETRIES:
                    print(f"Task {task_id} exceeded max retries")
                    existing_task.status = "failed"
                    db.commit()
                    return False
                
                # 增加重试计数
                existing_task.retry_count += 1
                db.commit()
            else:
                # 创建任务记录
                task_record = TaskRecord(
                    task_id=task_id,
                    news_id=news_id,
                    status="processing"
                )
                db.add(task_record)
                db.commit()
            
            # 获取快讯数据
            news = db.query(News).filter(News.id == news_id).first()
            if not news:
                print(f"News {news_id} not found")
                return False
            
            try:
                # 创建分析记录
                analysis = Analysis(
                    news_id=news_id,
                    pipeline_status="running",
                    started_at=datetime.utcnow()
                )
                db.add(analysis)
                db.flush()
                
                # 运行分析流水线
                result = self.pipeline.run(
                    news_id=news_id,
                    title=news.title,
                    content=news.content
                )
                
                # 更新分析结果
                analysis.has_investment_value = result.get("has_investment_value", False)
                analysis.investment_reasoning = result.get("investment_reasoning", "")
                analysis.tokens = result.get("tokens", [])
                analysis.trend_analysis = result.get("trend_analyses", [])  # 注意：这里是 trend_analyses
                analysis.recommendation = result.get("recommendation", "HOLD")
                analysis.recommendation_reasoning = result.get("recommendation_reasoning", "")
                analysis.confidence_score = result.get("recommendation_confidence", 0.0)
                analysis.pipeline_steps = result.get("steps", [])
                analysis.pipeline_status = "completed"
                analysis.completed_at = datetime.utcnow()
                analysis.risk_level = result.get("risk_level", "MEDIUM")  # 添加风险等级
                
                # 更新任务状态
                task_record = db.query(TaskRecord).filter(
                    TaskRecord.task_id == task_id
                ).first()
                if task_record:
                    task_record.status = "completed"
                
                db.commit()
                
                print(f"Task {task_id} completed successfully")
                return True
                
            except Exception as e:
                print(f"Error processing task {task_id}: {e}")
                
                # 更新错误信息
                analysis.pipeline_status = "failed"
                analysis.error_message = str(e)
                analysis.completed_at = datetime.utcnow()
                
                task_record = db.query(TaskRecord).filter(
                    TaskRecord.task_id == task_id
                ).first()
                if task_record:
                    task_record.error_message = str(e)
                
                db.commit()
                return False
    
    def start(self):
        """启动 Worker"""
        print(f"Starting analysis worker with concurrency: {settings.WORKER_CONCURRENCY}")
        
        # 只在主线程中注册信号处理
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            rabbitmq_service.consume(
                callback=self.process_task,
                prefetch_count=settings.WORKER_CONCURRENCY
            )
        except KeyboardInterrupt:
            print("\nShutting down worker...")
        finally:
            rabbitmq_service.close()
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"\nReceived signal {signum}, shutting down...")
        self.running = False
        rabbitmq_service.close()
        sys.exit(0)


if __name__ == "__main__":
    worker = AnalysisWorker()
    worker.start()
