"""市场数据 API 路由"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Optional

from app.services.market.coingecko_service import CoinGeckoService

router = APIRouter(prefix="/api/v1/market", tags=["Market Data"])


# ==================== 请求/响应模型 ====================

class TokenInfoRequest(BaseModel):
    """代币信息查询请求"""
    symbol: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTC"
            }
        }


class BatchTokenInfoRequest(BaseModel):
    """批量代币信息查询请求"""
    symbols: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbols": ["BTC", "ETH", "USDT"]
            }
        }


class TokenInfoResponse(BaseModel):
    """代币信息响应"""
    symbol: str
    name: str
    current_price_usd: Optional[float]
    market_cap_usd: Optional[float]
    market_cap_rank: Optional[int]
    price_change_24h: Optional[float]
    price_change_7d: Optional[float]
    price_change_30d: Optional[float]
    total_volume_usd: Optional[float]
    circulating_supply: Optional[float]
    total_supply: Optional[float]
    max_supply: Optional[float]
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTC",
                "name": "Bitcoin",
                "current_price_usd": 50000.0,
                "market_cap_usd": 950000000000.0,
                "market_cap_rank": 1,
                "price_change_24h": 2.5,
                "price_change_7d": 5.3,
                "price_change_30d": 10.2,
                "total_volume_usd": 25000000000.0,
                "circulating_supply": 19000000.0,
                "total_supply": 21000000.0,
                "max_supply": 21000000.0
            }
        }


class SearchCoinRequest(BaseModel):
    """搜索代币请求"""
    query: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Bitcoin"
            }
        }


class SearchCoinResponse(BaseModel):
    """搜索代币响应"""
    id: str
    symbol: str
    name: str
    market_cap_rank: Optional[int]


# ==================== API 端点 ====================

@router.post("/token/info", response_model=TokenInfoResponse)
async def get_token_info(request: TokenInfoRequest):
    """
    获取单个代币的市场信息
    
    - **symbol**: 代币符号（如 BTC, ETH）
    
    返回代币的实时价格、市值、涨跌幅等信息
    """
    try:
        service = CoinGeckoService()
        token_info = service.get_token_info(request.symbol)
        
        if not token_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"代币 {request.symbol} 未找到"
            )
        
        return TokenInfoResponse(**token_info)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取代币信息失败: {str(e)}"
        )


@router.post("/token/batch", response_model=Dict[str, TokenInfoResponse])
async def get_batch_token_info(request: BatchTokenInfoRequest):
    """
    批量获取多个代币的市场信息
    
    - **symbols**: 代币符号列表
    
    注意：批量查询会有延迟以避免 API 限流
    """
    try:
        service = CoinGeckoService()
        tokens_info = service.get_multiple_tokens_info(request.symbols)
        
        result = {}
        for symbol, info in tokens_info.items():
            result[symbol] = TokenInfoResponse(**info)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量获取代币信息失败: {str(e)}"
        )


@router.post("/search", response_model=SearchCoinResponse)
async def search_coin(request: SearchCoinRequest):
    """
    搜索代币
    
    - **query**: 搜索关键词（代币名称或符号）
    
    返回匹配的代币基本信息
    """
    try:
        service = CoinGeckoService()
        coin_info = service.search_coin(request.query)
        
        if not coin_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到匹配 '{request.query}' 的代币"
            )
        
        return SearchCoinResponse(**coin_info)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索失败: {str(e)}"
        )


@router.get("/token/{symbol}/formatted")
async def get_token_info_formatted(symbol: str):
    """
    获取格式化的代币信息（用于 LLM）
    
    - **symbol**: 代币符号
    
    返回格式化的文本，适合作为 LLM 的上下文
    """
    try:
        service = CoinGeckoService()
        token_info = service.get_token_info(symbol)
        
        if not token_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"代币 {symbol} 未找到"
            )
        
        formatted_text = service.format_token_info_for_llm(token_info)
        
        return {
            "symbol": symbol,
            "formatted_text": formatted_text,
            "raw_data": token_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取代币信息失败: {str(e)}"
        )


@router.get("/health")
async def market_service_health():
    """
    检查市场数据服务健康状态
    
    尝试获取 BTC 信息来验证服务是否正常
    """
    try:
        service = CoinGeckoService()
        btc_info = service.get_token_info("BTC")
        
        if btc_info:
            return {
                "status": "healthy",
                "message": "市场数据服务正常",
                "test_query": "BTC",
                "test_result": "success"
            }
        else:
            return {
                "status": "degraded",
                "message": "市场数据服务可能存在问题",
                "test_query": "BTC",
                "test_result": "failed"
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"市场数据服务不可用: {str(e)}"
        )
