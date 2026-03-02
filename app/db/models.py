from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, Float, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class News(Base):
    """快讯表"""
    __tablename__ = "news"
    
    id = Column(Integer, primary_key=True, index=True)
    odaily_id = Column(String(100), unique=True, index=True, comment="Odaily 快讯 ID")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容")
    published_at = Column(DateTime, comment="发布时间")
    source_url = Column(String(500), comment="来源链接")
    raw_data = Column(JSON, comment="原始数据")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    analyses = relationship("Analysis", back_populates="news")


class Analysis(Base):
    """分析结果表"""
    __tablename__ = "analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    news_id = Column(Integer, ForeignKey("news.id"), nullable=False, index=True)
    
    # 投资价值判断
    has_investment_value = Column(Boolean, comment="是否有投资价值")
    investment_reasoning = Column(Text, comment="投资价值判断理由")
    
    # 代币提取
    tokens = Column(JSON, comment="提取的代币列表")
    
    # 趋势分析
    trend_analysis = Column(JSON, comment="趋势分析结果")
    
    # 投资建议
    recommendation = Column(String(50), comment="投资建议: BUY/SELL/HOLD")
    recommendation_reasoning = Column(Text, comment="建议理由")
    confidence_score = Column(Float, comment="置信度分数 0-1")
    risk_level = Column(String(50), comment="风险等级: LOW/MEDIUM/HIGH")
    
    # 流水线执行信息
    pipeline_status = Column(String(50), default="pending", comment="流水线状态")
    pipeline_steps = Column(JSON, comment="各步骤详细结果")
    error_message = Column(Text, comment="错误信息")
    
    # LangSmith 追踪
    langsmith_run_id = Column(String(100), comment="LangSmith Run ID")
    
    # 时间戳
    started_at = Column(DateTime, comment="开始分析时间")
    completed_at = Column(DateTime, comment="完成分析时间")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    news = relationship("News", back_populates="analyses")
    
    __table_args__ = (
        Index("idx_analysis_status", "pipeline_status"),
        Index("idx_analysis_recommendation", "recommendation"),
    )


class Document(Base):
    """RAG 知识库文档表"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, comment="文档标题")
    content = Column(Text, nullable=False, comment="文档内容")
    source = Column(String(500), comment="文档来源")
    doc_type = Column(String(50), comment="文档类型: whitepaper/article/tokenomics")
    doc_metadata = Column(JSON, comment="元数据")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    chunks = relationship("DocumentChunk", back_populates="document")


class DocumentChunk(Base):
    """文档分块表"""
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False, comment="分块索引")
    content = Column(Text, nullable=False, comment="分块内容")
    embedding = Column(Vector(1536), comment="向量嵌入")
    chunk_metadata = Column(JSON, comment="元数据")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    document = relationship("Document", back_populates="chunks")
    
    __table_args__ = (
        Index("idx_chunk_embedding", "embedding", postgresql_using="ivfflat"),
    )


class TaskRecord(Base):
    """任务记录表（用于幂等性）"""
    __tablename__ = "task_records"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(100), unique=True, index=True, comment="任务唯一 ID")
    news_id = Column(Integer, ForeignKey("news.id"), nullable=False)
    status = Column(String(50), default="pending", comment="任务状态")
    retry_count = Column(Integer, default=0, comment="重试次数")
    error_message = Column(Text, comment="错误信息")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
