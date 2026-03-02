"""API 数据模型"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime


# 请求模型
class NewsSubmitRequest(BaseModel):
    """提交快讯分析请求"""
    news_id: Optional[int] = Field(None, description="快讯 ID（已存在的快讯）")
    title: Optional[str] = Field(None, description="快讯标题（新快讯）")
    content: Optional[str] = Field(None, description="快讯内容（新快讯）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "news_id": 123,
            }
        }


class BatchSubmitRequest(BaseModel):
    """批量提交请求"""
    news_ids: List[int] = Field(..., description="快讯 ID 列表")
    
    class Config:
        json_schema_extra = {
            "example": {
                "news_ids": [1, 2, 3, 4, 5]
            }
        }


# 响应模型
class NewsResponse(BaseModel):
    """快讯响应"""
    id: int
    title: str
    content: str
    published_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TokenInfo(BaseModel):
    """代币信息"""
    symbol: str
    trend: Optional[str] = None
    confidence: Optional[float] = None


class AnalysisStepResult(BaseModel):
    """分析步骤结果"""
    step: str
    status: str
    result: Optional[Dict] = None
    error: Optional[str] = None


class AnalysisResponse(BaseModel):
    """分析结果响应"""
    id: int
    news_id: int
    
    # 投资价值
    has_investment_value: Optional[bool] = None
    investment_reasoning: Optional[str] = None
    
    # 代币
    tokens: Optional[List[str]] = None
    
    # 趋势分析
    trend_analysis: Optional[List[Dict]] = None
    
    # 投资建议
    recommendation: Optional[str] = None
    recommendation_reasoning: Optional[str] = None
    confidence_score: Optional[float] = None
    risk_level: Optional[str] = None  # 添加风险等级字段
    
    # 状态
    pipeline_status: str
    pipeline_steps: Optional[List[Dict]] = None
    error_message: Optional[str] = None
    
    # 时间
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class SubmitResponse(BaseModel):
    """提交响应"""
    task_id: str
    news_id: int
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_123_1234567890",
                "news_id": 123,
                "message": "Analysis task submitted successfully"
            }
        }


class BatchSubmitResponse(BaseModel):
    """批量提交响应"""
    tasks: List[SubmitResponse]
    total: int
    message: str


class AnalysisOverview(BaseModel):
    """分析概览"""
    total_analyses: int
    completed: int
    pending: int
    failed: int
    
    # 投资价值分布
    has_value_count: int
    no_value_count: int
    
    # 建议分布
    buy_count: int
    sell_count: int
    hold_count: int
    
    # 热门代币
    top_tokens: List[Dict[str, int]]
    
    # 平均置信度
    avg_confidence: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_analyses": 100,
                "completed": 85,
                "pending": 10,
                "failed": 5,
                "has_value_count": 60,
                "no_value_count": 25,
                "buy_count": 30,
                "sell_count": 15,
                "hold_count": 40,
                "top_tokens": [
                    {"token": "BTC", "count": 25},
                    {"token": "ETH", "count": 20}
                ],
                "avg_confidence": 0.78
            }
        }


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Not Found",
                "detail": "News with id 123 not found"
            }
        }
