from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os
from pathlib import Path

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """应用配置"""
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/web3_analysis"
    
    # RabbitMQ
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    QUEUE_NAME: str = "analysis_tasks"
    DLQ_NAME: str = "analysis_tasks_dlq"
    
    # OpenAI / OpenAI-compatible API
    OPENAI_API_KEY: str
    OPENAI_API_BASE: str = "https://api.openai-hub.com/v1"
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-ada-002"
    
    # LangSmith
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "web3-investment-analysis"
    
    # Neo4j
    NEO4J_URI: Optional[str] = None
    NEO4J_USER: Optional[str] = None
    NEO4J_PASSWORD: Optional[str] = None
    
    # Knowledge Graph
    ENABLE_KNOWLEDGE_GRAPH: bool = False  # 是否启用知识图谱
    GRAPH_WEIGHT: float = 0.3  # 知识图谱在分析中的权重 (0-1)
    
    # RAG Knowledge Base
    ENABLE_RAG: bool = True  # 是否启用 RAG 知识库
    RAG_WEIGHT: float = 0.5  # RAG 在分析中的权重 (0-1)
    
    # Application
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    WORKER_CONCURRENCY: int = 5
    MAX_RETRIES: int = 3
    
    # Crawler
    ODAILY_BASE_URL: str = "https://www.odaily.news"
    REQUEST_TIMEOUT: int = 30
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'
    )


def get_settings() -> Settings:
    """
    获取配置实例
    
    根据环境变量 NACOS_ENABLED 决定使用本地配置还是 Nacos 配置
    
    Returns:
        配置实例
    """
    # 先加载 .env 文件
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)
    
    # 检查是否启用 Nacos
    nacos_enabled = os.getenv("NACOS_ENABLED", "false").lower() == "true"
    
    if nacos_enabled:
        try:
            # 尝试导入 Nacos 配置
            from app.core.nacos_config import NacosSettings
            print("✓ 使用 Nacos 配置中心")
            return NacosSettings()
        except ImportError as e:
            print(f"⚠ Nacos SDK 导入失败: {e}")
            print("提示：运行 'pip install nacos-sdk-python==0.1.11 loguru' 安装依赖")
            return Settings()
        except Exception as e:
            print(f"⚠ Nacos 初始化失败: {e}")
            print("回退到本地配置")
            return Settings()
    else:
        print("✓ 使用本地配置文件")
        return Settings()


# 创建配置实例
settings = get_settings()
