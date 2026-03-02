"""CoinGecko 市场数据服务"""
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import time


class CoinGeckoService:
    """CoinGecko API 服务 - 获取实时代币市场数据"""
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json"
        })
        self._cache = {}  # 简单缓存，避免频繁请求
        self._cache_ttl = 300  # 缓存 5 分钟
    
    def _get_from_cache(self, key: str) -> Optional[Dict]:
        """从缓存获取数据"""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return data
        return None
    
    def _set_cache(self, key: str, data: Dict):
        """设置缓存"""
        self._cache[key] = (data, time.time())
    
    def search_coin(self, query: str) -> Optional[Dict]:
        """
        搜索代币，获取 CoinGecko ID
        
        Args:
            query: 代币符号或名称（如 BTC, Bitcoin）
            
        Returns:
            代币基本信息，包含 id, symbol, name
        """
        cache_key = f"search_{query.lower()}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        try:
            response = self.session.get(
                f"{self.BASE_URL}/search",
                params={"query": query},
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            coins = data.get("coins", [])
            
            if not coins:
                return None
            
            # 返回第一个匹配结果
            result = {
                "id": coins[0]["id"],
                "symbol": coins[0]["symbol"].upper(),
                "name": coins[0]["name"],
                "market_cap_rank": coins[0].get("market_cap_rank")
            }
            
            self._set_cache(cache_key, result)
            return result
            
        except Exception as e:
            print(f"Search coin failed for {query}: {e}")
            return None
    
    def get_coin_data(self, coin_id: str) -> Optional[Dict]:
        """
        获取代币详细市场数据
        
        Args:
            coin_id: CoinGecko 代币 ID
            
        Returns:
            代币市场数据
        """
        cache_key = f"coin_{coin_id}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        try:
            response = self.session.get(
                f"{self.BASE_URL}/coins/{coin_id}",
                params={
                    "localization": "false",
                    "tickers": "false",
                    "community_data": "false",
                    "developer_data": "false"
                },
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            market_data = data.get("market_data", {})
            
            result = {
                "id": data["id"],
                "symbol": data["symbol"].upper(),
                "name": data["name"],
                "current_price_usd": market_data.get("current_price", {}).get("usd"),
                "market_cap_usd": market_data.get("market_cap", {}).get("usd"),
                "market_cap_rank": data.get("market_cap_rank"),
                "total_volume_usd": market_data.get("total_volume", {}).get("usd"),
                "price_change_24h": market_data.get("price_change_percentage_24h"),
                "price_change_7d": market_data.get("price_change_percentage_7d"),
                "price_change_30d": market_data.get("price_change_percentage_30d"),
                "circulating_supply": market_data.get("circulating_supply"),
                "total_supply": market_data.get("total_supply"),
                "max_supply": market_data.get("max_supply"),
                "ath": market_data.get("ath", {}).get("usd"),  # 历史最高价
                "atl": market_data.get("atl", {}).get("usd"),  # 历史最低价
            }
            
            self._set_cache(cache_key, result)
            return result
            
        except Exception as e:
            print(f"Get coin data failed for {coin_id}: {e}")
            return None
    
    def get_token_info(self, symbol: str) -> Optional[Dict]:
        """
        根据代币符号获取完整市场信息（组合方法）
        
        Args:
            symbol: 代币符号（如 BTC, ETH）
            
        Returns:
            完整的代币市场信息
        """
        # 先搜索获取 coin_id
        coin_info = self.search_coin(symbol)
        if not coin_info:
            return None
        
        # 再获取详细数据
        coin_data = self.get_coin_data(coin_info["id"])
        return coin_data
    
    def get_multiple_tokens_info(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        批量获取多个代币信息
        
        Args:
            symbols: 代币符号列表
            
        Returns:
            {symbol: token_info} 字典
        """
        results = {}
        
        for symbol in symbols:
            # 添加延迟避免 API 限流（免费版限制：50 次/分钟）
            time.sleep(1.2)
            
            token_info = self.get_token_info(symbol)
            if token_info:
                results[symbol] = token_info
        
        return results
    
    def format_token_info_for_llm(self, token_info: Dict) -> str:
        """
        格式化代币信息为 LLM 可读文本
        
        Args:
            token_info: 代币信息字典
            
        Returns:
            格式化的文本
        """
        if not token_info:
            return "未找到代币信息"
        
        price = token_info.get("current_price_usd")
        market_cap = token_info.get("market_cap_usd")
        change_24h = token_info.get("price_change_24h")
        change_7d = token_info.get("price_change_7d")
        
        # 格式化数字
        price_str = f"${price:,.2f}" if price else "N/A"
        market_cap_str = f"${market_cap:,.0f}" if market_cap else "N/A"
        change_24h_str = f"{change_24h:+.2f}%" if change_24h is not None else "N/A"
        change_7d_str = f"{change_7d:+.2f}%" if change_7d is not None else "N/A"
        
        text = f"""
代币: {token_info['name']} ({token_info['symbol']})
当前价格: {price_str}
市值: {market_cap_str}
市值排名: #{token_info.get('market_cap_rank', 'N/A')}
24小时涨跌: {change_24h_str}
7天涨跌: {change_7d_str}
流通供应量: {token_info.get('circulating_supply', 'N/A'):,.0f}
"""
        return text.strip()


# 测试函数
def test_coingecko_service():
    """测试 CoinGecko 服务"""
    service = CoinGeckoService()
    
    # 测试单个代币
    print("=== 测试 BTC ===")
    btc_info = service.get_token_info("BTC")
    if btc_info:
        print(service.format_token_info_for_llm(btc_info))
    
    print("\n=== 测试 ETH ===")
    eth_info = service.get_token_info("ETH")
    if eth_info:
        print(service.format_token_info_for_llm(eth_info))
    
    # 测试批量获取
    print("\n=== 批量测试 ===")
    tokens = service.get_multiple_tokens_info(["BTC", "ETH", "USDT"])
    for symbol, info in tokens.items():
        print(f"\n{symbol}:")
        print(service.format_token_info_for_llm(info))


if __name__ == "__main__":
    test_coingecko_service()
