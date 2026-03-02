"""混合 RAG 服务 - 支持滑动窗口切分和 BM25 检索"""
from typing import List, Dict, Tuple
from langchain_openai import OpenAIEmbeddings
from sqlalchemy import select, func, text
from app.db.models import Document, DocumentChunk
from app.db.database import get_db_context
from app.core.config import settings
import jieba
import jieba.analyse
from collections import Counter
import math


class SlidingWindowSplitter:
    """滑动窗口文本切分器"""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        overlap_size: int = 50,
        separators: List[str] = None
    ):
        """
        初始化滑动窗口切分器
        
        Args:
            chunk_size: 每个分块的大小（字符数）
            overlap_size: 重叠部分的大小（字符数）
            separators: 分隔符列表，用于智能切分
        """
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.separators = separators or ["\n\n", "\n", "。", "！", "？", ". ", "! ", "? "]
    
    def split_text(self, text: str) -> List[str]:
        """
        使用滑动窗口切分文本
        
        Args:
            text: 待切分的文本
            
        Returns:
            切分后的文本块列表
        """
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            # 确定当前块的结束位置
            end = start + self.chunk_size
            
            # 如果不是最后一块，尝试在分隔符处切分
            if end < len(text):
                # 在 chunk_size 附近寻找最佳分隔点
                best_split = end
                search_start = max(start + self.chunk_size - 100, start)
                search_end = min(end + 100, len(text))
                
                for separator in self.separators:
                    # 在搜索范围内查找分隔符
                    pos = text.rfind(separator, search_start, search_end)
                    if pos != -1 and abs(pos - end) < abs(best_split - end):
                        best_split = pos + len(separator)
                
                end = best_split
            
            # 提取当前块
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # 移动到下一个位置（考虑重叠）
            if end >= len(text):
                break
            
            start = end - self.overlap_size
            
            # 确保不会陷入无限循环
            if chunks and start <= len(chunks[-1]):
                start = end
        
        return chunks


class BM25Retriever:
    """BM25 关键词检索器"""
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        初始化 BM25 检索器
        
        Args:
            k1: 词频饱和参数
            b: 长度归一化参数
        """
        self.k1 = k1
        self.b = b
        self.corpus = []
        self.corpus_ids = []
        self.doc_freqs = Counter()
        self.idf = {}
        self.doc_len = []
        self.avgdl = 0
    
    def fit(self, corpus: List[str], corpus_ids: List[int]):
        """
        训练 BM25 模型
        
        Args:
            corpus: 文档列表
            corpus_ids: 文档 ID 列表
        """
        self.corpus = corpus
        self.corpus_ids = corpus_ids
        
        # 分词并统计
        tokenized_corpus = []
        for doc in corpus:
            tokens = list(jieba.cut_for_search(doc))
            tokenized_corpus.append(tokens)
            self.doc_len.append(len(tokens))
            
            # 统计文档频率
            for token in set(tokens):
                self.doc_freqs[token] += 1
        
        # 计算平均文档长度
        self.avgdl = sum(self.doc_len) / len(self.doc_len) if self.doc_len else 0
        
        # 计算 IDF
        num_docs = len(corpus)
        for token, freq in self.doc_freqs.items():
            self.idf[token] = math.log((num_docs - freq + 0.5) / (freq + 0.5) + 1)
        
        self.tokenized_corpus = tokenized_corpus
    
    def get_scores(self, query: str) -> List[Tuple[int, float]]:
        """
        计算查询与所有文档的 BM25 分数
        
        Args:
            query: 查询文本
            
        Returns:
            [(chunk_id, score), ...] 列表
        """
        query_tokens = list(jieba.cut_for_search(query))
        scores = []
        
        for idx, (doc_tokens, doc_id) in enumerate(zip(self.tokenized_corpus, self.corpus_ids)):
            score = 0
            doc_len = self.doc_len[idx]
            
            for token in query_tokens:
                if token not in self.idf:
                    continue
                
                # 计算词频
                tf = doc_tokens.count(token)
                
                # BM25 公式
                idf = self.idf[token]
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                score += idf * numerator / denominator
            
            scores.append((doc_id, score))
        
        return scores
    
    def search(self, query: str, k: int = 5) -> List[Tuple[int, float]]:
        """
        搜索最相关的文档
        
        Args:
            query: 查询文本
            k: 返回结果数量
            
        Returns:
            [(chunk_id, score), ...] 列表，按分数降序排列
        """
        scores = self.get_scores(query)
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]


class HybridRAGService:
    """混合 RAG 服务 - 结合向量检索和 BM25 关键词检索"""
    
    def __init__(self, config=None):
        """
        初始化混合 RAG 服务
        
        Args:
            config: 配置类（可选），默认使用 RAGConfig
        """
        from app.services.rag.config import RAGConfig
        
        self.config = config or RAGConfig
        
        self.embeddings = OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE
        )
        self.text_splitter = SlidingWindowSplitter(
            **self.config.get_splitter_config()
        )
        self.bm25 = None
        self._init_bm25()
    
    def _init_bm25(self):
        """初始化 BM25 检索器"""
        with get_db_context() as db:
            chunks = db.query(DocumentChunk).all()
            if chunks:
                corpus = [chunk.content for chunk in chunks]
                corpus_ids = [chunk.id for chunk in chunks]
                self.bm25 = BM25Retriever(**self.config.get_bm25_config())
                self.bm25.fit(corpus, corpus_ids)
    
    def add_document(
        self,
        title: str,
        content: str,
        source: str,
        doc_type: str,
        metadata: Dict = None
    ) -> Tuple[int, int]:
        """
        添加文档到知识库（使用滑动窗口切分）
        
        Args:
            title: 文档标题
            content: 文档内容
            source: 文档来源
            doc_type: 文档类型
            metadata: 元数据
            
        Returns:
            (文档 ID, 分块数量)
        """
        with get_db_context() as db:
            # 去重：同一 source 已存在则直接返回
            existing = db.query(Document).filter(Document.source == source).first()
            if existing:
                chunks_count = db.query(func.count(DocumentChunk.id)).filter(
                    DocumentChunk.document_id == existing.id
                ).scalar()
                return existing.id, chunks_count

            # 创建文档记录
            doc = Document(
                title=title,
                content=content,
                source=source,
                doc_type=doc_type,
                doc_metadata=metadata or {}
            )
            db.add(doc)
            db.flush()
            
            # 使用滑动窗口切分
            chunks = self.text_splitter.split_text(content)
            
            print(f"文档 '{title}' 切分为 {len(chunks)} 个块（滑动窗口，重叠 {self.text_splitter.overlap_size} 字符）")
            
            # 生成嵌入并保存
            for idx, chunk_text in enumerate(chunks):
                embedding = self.embeddings.embed_query(chunk_text)
                
                chunk = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=idx,
                    content=chunk_text,
                    embedding=embedding,
                    chunk_metadata={
                        "title": title,
                        "doc_type": doc_type,
                        "chunk_index": idx,
                        "chunk_size": len(chunk_text),
                        "overlap_size": self.text_splitter.overlap_size
                    }
                )
                db.add(chunk)
            
            db.commit()
            
            # 重新初始化 BM25
            self._init_bm25()
            
            return doc.id, len(chunks)
    
    def vector_search(
        self,
        query: str,
        k: int = 10,
        doc_type: str = None
    ) -> List[Dict]:
        """
        向量语义搜索
        
        Args:
            query: 查询文本
            k: 返回结果数量
            doc_type: 文档类型过滤
            
        Returns:
            相关文档列表
        """
        query_embedding = self.embeddings.embed_query(query)
        
        with get_db_context() as db:
            stmt = select(
                DocumentChunk,
                DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")
            )
            
            if doc_type:
                stmt = stmt.join(Document).where(Document.doc_type == doc_type)
            
            stmt = stmt.order_by("distance").limit(k)
            results = db.execute(stmt).all()
            
            return [
                {
                    "chunk_id": chunk.id,
                    "content": chunk.content,
                    "metadata": chunk.chunk_metadata,
                    "vector_score": 1 - distance,  # 转换为相似度分数
                    "document_id": chunk.document_id
                }
                for chunk, distance in results
            ]
    
    def bm25_search(self, query: str, k: int = 10) -> List[Dict]:
        """
        BM25 关键词搜索
        
        Args:
            query: 查询文本
            k: 返回结果数量
            
        Returns:
            相关文档列表
        """
        if not self.bm25:
            return []
        
        results = self.bm25.search(query, k=k)
        
        with get_db_context() as db:
            chunks_dict = {}
            chunk_ids = [chunk_id for chunk_id, _ in results]
            
            if chunk_ids:
                chunks = db.query(DocumentChunk).filter(
                    DocumentChunk.id.in_(chunk_ids)
                ).all()
                
                for chunk in chunks:
                    chunks_dict[chunk.id] = chunk
            
            return [
                {
                    "chunk_id": chunk_id,
                    "content": chunks_dict[chunk_id].content,
                    "metadata": chunks_dict[chunk_id].chunk_metadata,
                    "bm25_score": score,
                    "document_id": chunks_dict[chunk_id].document_id
                }
                for chunk_id, score in results
                if chunk_id in chunks_dict
            ]
    
    def hybrid_search(
        self,
        query: str,
        k: int = 5,
        doc_type: str = None,
        vector_weight: float = None,
        bm25_weight: float = None
    ) -> List[Dict]:
        """
        混合搜索：结合向量检索和 BM25 关键词检索
        
        Args:
            query: 查询文本
            k: 返回结果数量
            doc_type: 文档类型过滤
            vector_weight: 向量检索权重（可选，默认使用配置）
            bm25_weight: BM25 检索权重（可选，默认使用配置）
            
        Returns:
            相关文档列表，按混合分数排序
        """
        # 使用配置的默认权重
        if vector_weight is None:
            vector_weight = self.config.VECTOR_WEIGHT
        if bm25_weight is None:
            bm25_weight = self.config.BM25_WEIGHT
        
        # 获取更多候选结果用于重排序
        candidate_k = k * self.config.CANDIDATE_MULTIPLIER
        
        # 向量检索
        vector_results = self.vector_search(query, k=candidate_k, doc_type=doc_type)
        
        # BM25 检索
        bm25_results = self.bm25_search(query, k=candidate_k)
        
        # 归一化分数
        def normalize_scores(results, score_key):
            if not results:
                return results
            
            scores = [r[score_key] for r in results]
            min_score = min(scores)
            max_score = max(scores)
            
            if max_score - min_score > 0:
                for r in results:
                    r[f"{score_key}_normalized"] = (r[score_key] - min_score) / (max_score - min_score)
            else:
                for r in results:
                    r[f"{score_key}_normalized"] = 1.0
            
            return results
        
        vector_results = normalize_scores(vector_results, "vector_score")
        bm25_results = normalize_scores(bm25_results, "bm25_score")
        
        # 合并结果
        combined = {}
        
        for result in vector_results:
            chunk_id = result["chunk_id"]
            combined[chunk_id] = {
                "chunk_id": chunk_id,
                "content": result["content"],
                "metadata": result["metadata"],
                "document_id": result["document_id"],
                "vector_score": result.get("vector_score_normalized", 0),
                "bm25_score": 0
            }
        
        for result in bm25_results:
            chunk_id = result["chunk_id"]
            if chunk_id in combined:
                combined[chunk_id]["bm25_score"] = result.get("bm25_score_normalized", 0)
            else:
                combined[chunk_id] = {
                    "chunk_id": chunk_id,
                    "content": result["content"],
                    "metadata": result["metadata"],
                    "document_id": result["document_id"],
                    "vector_score": 0,
                    "bm25_score": result.get("bm25_score_normalized", 0)
                }
        
        # 计算混合分数
        for chunk_id, result in combined.items():
            result["hybrid_score"] = (
                vector_weight * result["vector_score"] +
                bm25_weight * result["bm25_score"]
            )
        
        # 排序并返回 top-k
        sorted_results = sorted(
            combined.values(),
            key=lambda x: x["hybrid_score"],
            reverse=True
        )
        
        return sorted_results[:k]
    
    def search(
        self,
        query: str,
        k: int = 5,
        doc_type: str = None,
        method: str = "hybrid"
    ) -> List[Dict]:
        """
        统一搜索接口
        
        Args:
            query: 查询文本
            k: 返回结果数量
            doc_type: 文档类型过滤
            method: 检索方法 ("vector", "bm25", "hybrid")
            
        Returns:
            相关文档列表
        """
        if method == "vector":
            return self.vector_search(query, k, doc_type)
        elif method == "bm25":
            return self.bm25_search(query, k)
        elif method == "hybrid":
            return self.hybrid_search(query, k, doc_type)
        else:
            raise ValueError(f"Unknown search method: {method}")
    
    def get_document_count(self) -> int:
        """获取文档总数"""
        with get_db_context() as db:
            return db.query(func.count(Document.id)).scalar()
    
    def get_chunk_count(self) -> int:
        """获取分块总数"""
        with get_db_context() as db:
            return db.query(func.count(DocumentChunk.id)).scalar()


# 向后兼容：保持原有接口
RAGService = HybridRAGService
