"""RAG 服务配置"""
from typing import List


class RAGConfig:
    """RAG 服务配置"""
    
    # 滑动窗口切分配置
    CHUNK_SIZE: int = 1000  # 每个分块的大小（字符数）
    OVERLAP_SIZE: int = 200  # 重叠部分的大小（字符数）
    
    # 分隔符优先级（从高到低）
    SEPARATORS: List[str] = [
        "\n\n",  # 段落分隔
        "\n",    # 行分隔
        "。",    # 中文句号
        "！",    # 中文感叹号
        "？",    # 中文问号
        ". ",    # 英文句号
        "! ",    # 英文感叹号
        "? ",    # 英文问号
        "；",    # 中文分号
        "; ",    # 英文分号
        "，",    # 中文逗号
        ", ",    # 英文逗号
    ]
    
    # BM25 配置
    BM25_K1: float = 1.5  # 词频饱和参数（越大，词频影响越大）
    BM25_B: float = 0.75  # 长度归一化参数（0-1，越大长度影响越大）
    
    # 混合检索配置
    VECTOR_WEIGHT: float = 0.7  # 向量检索权重
    BM25_WEIGHT: float = 0.3    # BM25 检索权重
    
    # 检索配置
    DEFAULT_K: int = 5  # 默认返回结果数量
    CANDIDATE_MULTIPLIER: int = 3  # 候选结果倍数（用于重排序）
    
    # 默认检索方法
    DEFAULT_METHOD: str = "hybrid"  # "vector", "bm25", "hybrid"
    
    @classmethod
    def get_splitter_config(cls) -> dict:
        """获取切分器配置"""
        return {
            "chunk_size": cls.CHUNK_SIZE,
            "overlap_size": cls.OVERLAP_SIZE,
            "separators": cls.SEPARATORS
        }
    
    @classmethod
    def get_bm25_config(cls) -> dict:
        """获取 BM25 配置"""
        return {
            "k1": cls.BM25_K1,
            "b": cls.BM25_B
        }
    
    @classmethod
    def get_hybrid_config(cls) -> dict:
        """获取混合检索配置"""
        return {
            "vector_weight": cls.VECTOR_WEIGHT,
            "bm25_weight": cls.BM25_WEIGHT
        }


# 预设配置方案

class BalancedConfig(RAGConfig):
    """平衡配置 - 向量和 BM25 权重相等"""
    VECTOR_WEIGHT = 0.5
    BM25_WEIGHT = 0.5


class SemanticFocusedConfig(RAGConfig):
    """语义优先配置 - 更重视向量检索"""
    VECTOR_WEIGHT = 0.7
    BM25_WEIGHT = 0.3


class KeywordFocusedConfig(RAGConfig):
    """关键词优先配置 - 更重视 BM25 检索"""
    VECTOR_WEIGHT = 0.3
    BM25_WEIGHT = 0.7


class LargeChunkConfig(RAGConfig):
    """大块配置 - 适合长文档"""
    CHUNK_SIZE = 1500
    OVERLAP_SIZE = 300


class SmallChunkConfig(RAGConfig):
    """小块配置 - 适合精确检索"""
    CHUNK_SIZE = 500
    OVERLAP_SIZE = 100


# 使用示例：
# from app.services.rag.config import SemanticFocusedConfig
# service = HybridRAGService(config=SemanticFocusedConfig)
