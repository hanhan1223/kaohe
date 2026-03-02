"""FastAPI 主应用"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api import analysis, data, market, graph
from app.core.config import settings
import threading
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建应用
app = FastAPI(
    title="Web3 Investment Analysis System",
    description="AI-driven Web3 investment analysis system powered by LangGraph",
    version="1.0.0"
)

# Worker 线程引用
worker_thread = None

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(analysis.router)
app.include_router(data.router)
app.include_router(market.router)
app.include_router(graph.router)


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    global worker_thread
    
    logger.info("Starting Web3 Investment Analysis System...")
    
    # 启动 Worker 线程
    try:
        from app.services.queue.worker import AnalysisWorker
        
        def run_worker():
            """在后台线程运行 Worker"""
            try:
                worker = AnalysisWorker()
                logger.info("Analysis Worker started in background thread")
                worker.start()
            except Exception as e:
                logger.error(f"Worker failed to start: {e}")
        
        worker_thread = threading.Thread(target=run_worker, daemon=True)
        worker_thread.start()
        logger.info("✓ Worker thread started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start worker thread: {e}")
        logger.warning("Worker not started - analysis tasks will not be processed")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("Shutting down Web3 Investment Analysis System...")
    
    # Worker 线程会自动清理（daemon=True）
    if worker_thread and worker_thread.is_alive():
        logger.info("Worker thread will be terminated")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Web3 Investment Analysis System",
        "version": "1.0.0",
        "docs": "/docs",
        "worker_status": "running" if worker_thread and worker_thread.is_alive() else "stopped"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "api": "running",
        "worker": "running" if worker_thread and worker_thread.is_alive() else "stopped"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )
