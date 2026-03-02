"""Nacos 配置中心集成"""
import json
import os
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
import nacos
from loguru import logger


class NacosConfig:
    """Nacos 配置管理器"""
    
    def __init__(
        self,
        server_addresses: str,
        namespace: str = "public",
        username: Optional[str] = None,
        password: Optional[str] = None,
        group: str = "DEFAULT_GROUP",
        data_id: str = "web3-analysis"
    ):
        """
        初始化 Nacos 客户端
        
        Args:
            server_addresses: Nacos 服务器地址，如 "127.0.0.1:8848"
            namespace: 命名空间 ID
            username: 用户名（如果启用了鉴权）
            password: 密码
            group: 配置分组
            data_id: 配置 ID
        """
        self.server_addresses = server_addresses
        self.namespace = namespace
        self.group = group
        self.data_id = data_id
        
        # 创建 Nacos 客户端
        self.client = nacos.NacosClient(
            server_addresses=server_addresses,
            namespace=namespace,
            username=username,
            password=password
        )
        
        self._config_cache: Dict[str, Any] = {}
        self._listeners = []
        
        logger.info(f"Nacos 客户端初始化成功: {server_addresses}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        从 Nacos 获取配置
        
        Returns:
            配置字典
        """
        try:
            # 获取配置内容
            content = self.client.get_config(
                data_id=self.data_id,
                group=self.group
            )
            
            if not content:
                logger.warning(f"Nacos 配置为空: {self.data_id}")
                return {}
            
            # 解析 JSON 配置
            config = json.loads(content)
            self._config_cache = config
            
            logger.info(f"成功从 Nacos 获取配置: {self.data_id}")
            return config
            
        except Exception as e:
            logger.error(f"从 Nacos 获取配置失败: {e}")
            # 返回缓存的配置
            return self._config_cache
    
    def publish_config(self, config: Dict[str, Any]) -> bool:
        """
        发布配置到 Nacos
        
        Args:
            config: 配置字典
            
        Returns:
            是否成功
        """
        try:
            content = json.dumps(config, ensure_ascii=False, indent=2)
            
            result = self.client.publish_config(
                data_id=self.data_id,
                group=self.group,
                content=content
            )
            
            if result:
                logger.info(f"成功发布配置到 Nacos: {self.data_id}")
                self._config_cache = config
            else:
                logger.error(f"发布配置到 Nacos 失败: {self.data_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"发布配置到 Nacos 失败: {e}")
            return False
    
    def add_config_listener(self, callback):
        """
        添加配置监听器，配置变更时自动回调
        
        Args:
            callback: 回调函数，接收新配置作为参数
        """
        def listener(args):
            """配置变更监听器"""
            try:
                content = args.get('content', '')
                if content:
                    config = json.loads(content)
                    self._config_cache = config
                    logger.info(f"检测到配置变更: {self.data_id}")
                    
                    # 调用回调函数
                    callback(config)
            except Exception as e:
                logger.error(f"处理配置变更失败: {e}")
        
        # 添加监听器
        self.client.add_config_watcher(
            data_id=self.data_id,
            group=self.group,
            cb=listener
        )
        
        self._listeners.append(callback)
        logger.info(f"已添加配置监听器: {self.data_id}")
    
    def remove_config_listener(self):
        """移除配置监听器"""
        try:
            self.client.remove_config_watcher(
                data_id=self.data_id,
                group=self.group
            )
            self._listeners.clear()
            logger.info(f"已移除配置监听器: {self.data_id}")
        except Exception as e:
            logger.error(f"移除配置监听器失败: {e}")


class NacosSettings(BaseSettings):
    """
    集成 Nacos 的配置类
    支持从 Nacos 和本地 .env 文件读取配置
    """
    
    # Nacos 连接配置（从环境变量或 .env 读取）
    NACOS_SERVER_ADDRESSES: Optional[str] = None
    NACOS_NAMESPACE: str = "public"
    NACOS_USERNAME: Optional[str] = None
    NACOS_PASSWORD: Optional[str] = None
    NACOS_GROUP: str = "DEFAULT_GROUP"
    NACOS_DATA_ID: str = "web3-analysis"
    NACOS_ENABLED: bool = False
    
    # 应用配置（可以被 Nacos 覆盖）
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/web3_analysis"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    QUEUE_NAME: str = "analysis_tasks"
    DLQ_NAME: str = "analysis_tasks_dlq"
    
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai-hub.com/v1"
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-ada-002"
    
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "web3-investment-analysis"
    
    NEO4J_URI: Optional[str] = None
    NEO4J_USER: Optional[str] = None
    NEO4J_PASSWORD: Optional[str] = None
    
    # Knowledge Graph
    ENABLE_KNOWLEDGE_GRAPH: bool = False
    GRAPH_WEIGHT: float = 0.3
    
    # RAG Knowledge Base
    ENABLE_RAG: bool = True
    RAG_WEIGHT: float = 0.5
    
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    WORKER_CONCURRENCY: int = 5
    MAX_RETRIES: int = 3
    
    ODAILY_BASE_URL: str = "https://www.odaily.news"
    REQUEST_TIMEOUT: int = 30
    
    _nacos_client: Optional[NacosConfig] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 如果启用了 Nacos，初始化客户端并加载配置
        if self.NACOS_ENABLED and self.NACOS_SERVER_ADDRESSES:
            self._init_nacos()
    
    def _init_nacos(self):
        """初始化 Nacos 客户端并加载配置"""
        try:
            # 创建 Nacos 客户端
            self._nacos_client = NacosConfig(
                server_addresses=self.NACOS_SERVER_ADDRESSES,
                namespace=self.NACOS_NAMESPACE,
                username=self.NACOS_USERNAME,
                password=self.NACOS_PASSWORD,
                group=self.NACOS_GROUP,
                data_id=self.NACOS_DATA_ID
            )
            
            # 从 Nacos 加载配置
            nacos_config = self._nacos_client.get_config()
            
            # 用 Nacos 配置覆盖本地配置
            if nacos_config:
                self._update_from_nacos(nacos_config)
                logger.info("已从 Nacos 加载配置")
            
            # 注意：在 Windows 上禁用配置监听器以避免多进程问题
            # 如果需要动态更新配置，请手动调用 reload_from_nacos()
            # self._nacos_client.add_config_listener(self._on_config_change)
            
        except Exception as e:
            logger.error(f"初始化 Nacos 失败: {e}")
            logger.warning("将使用本地配置")
    
    def _update_from_nacos(self, nacos_config: Dict[str, Any]):
        """用 Nacos 配置更新当前配置"""
        for key, value in nacos_config.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logger.debug(f"更新配置: {key}")
    
    def _on_config_change(self, new_config: Dict[str, Any]):
        """配置变更回调"""
        logger.info("检测到 Nacos 配置变更，正在更新...")
        self._update_from_nacos(new_config)
        logger.info("配置更新完成")
    
    def publish_to_nacos(self) -> bool:
        """
        将当前配置发布到 Nacos
        
        Returns:
            是否成功
        """
        if not self._nacos_client:
            logger.error("Nacos 客户端未初始化")
            return False
        
        # 构建配置字典
        config = {
            "DATABASE_URL": self.DATABASE_URL,
            "RABBITMQ_URL": self.RABBITMQ_URL,
            "QUEUE_NAME": self.QUEUE_NAME,
            "DLQ_NAME": self.DLQ_NAME,
            "OPENAI_API_KEY": self.OPENAI_API_KEY,
            "OPENAI_API_BASE": self.OPENAI_API_BASE,
            "OPENAI_MODEL": self.OPENAI_MODEL,
            "OPENAI_EMBEDDING_MODEL": self.OPENAI_EMBEDDING_MODEL,
            "LANGCHAIN_TRACING_V2": self.LANGCHAIN_TRACING_V2,
            "LANGCHAIN_API_KEY": self.LANGCHAIN_API_KEY,
            "LANGCHAIN_PROJECT": self.LANGCHAIN_PROJECT,
            "NEO4J_URI": self.NEO4J_URI,
            "NEO4J_USER": self.NEO4J_USER,
            "NEO4J_PASSWORD": self.NEO4J_PASSWORD,
            "ENABLE_KNOWLEDGE_GRAPH": self.ENABLE_KNOWLEDGE_GRAPH,
            "GRAPH_WEIGHT": self.GRAPH_WEIGHT,
            "ENABLE_RAG": self.ENABLE_RAG,
            "RAG_WEIGHT": self.RAG_WEIGHT,
            "API_HOST": self.API_HOST,
            "API_PORT": self.API_PORT,
            "WORKER_CONCURRENCY": self.WORKER_CONCURRENCY,
            "MAX_RETRIES": self.MAX_RETRIES,
            "ODAILY_BASE_URL": self.ODAILY_BASE_URL,
            "REQUEST_TIMEOUT": self.REQUEST_TIMEOUT
        }
        
        return self._nacos_client.publish_config(config)
    
    def reload_from_nacos(self):
        """从 Nacos 重新加载配置"""
        if not self._nacos_client:
            logger.error("Nacos 客户端未初始化")
            return
        
        nacos_config = self._nacos_client.get_config()
        if nacos_config:
            self._update_from_nacos(nacos_config)
            logger.info("已从 Nacos 重新加载配置")


# 创建全局配置实例
def create_settings() -> NacosSettings:
    """创建配置实例"""
    return NacosSettings()


# 全局配置实例
settings = create_settings()
