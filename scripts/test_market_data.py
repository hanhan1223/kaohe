"""测试市场数据服务"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.market.coingecko_service import CoinGeckoService


def test_single_token():
    """测试单个代币查询"""
    print("=" * 60)
    print("测试单个代币查询")
    print("=" * 60)
    
    service = CoinGeckoService()
    
    # 测试 BTC
    print("\n【测试 BTC】")
    btc_info = service.get_token_info("BTC")
    if btc_info:
        print(service.format_token_info_for_llm(btc_info))
        print(f"\n原始数据: {btc_info}")
    else:
        print("未找到 BTC 信息")
    
    # 测试 ETH
    print("\n【测试 ETH】")
    eth_info = service.get_token_info("ETH")
    if eth_info:
        print(service.format_token_info_for_llm(eth_info))
    else:
        print("未找到 ETH 信息")


def test_multiple_tokens():
    """测试批量代币查询"""
    print("\n" + "=" * 60)
    print("测试批量代币查询")
    print("=" * 60)
    
    service = CoinGeckoService()
    
    symbols = ["BTC", "ETH", "USDT"]
    print(f"\n查询代币: {', '.join(symbols)}")
    print("注意: 批量查询会有延迟以避免 API 限流...\n")
    
    tokens_info = service.get_multiple_tokens_info(symbols)
    
    for symbol, info in tokens_info.items():
        print(f"\n【{symbol}】")
        print(service.format_token_info_for_llm(info))


def test_search():
    """测试代币搜索"""
    print("\n" + "=" * 60)
    print("测试代币搜索")
    print("=" * 60)
    
    service = CoinGeckoService()
    
    queries = ["Bitcoin", "BTC", "Ethereum", "UNI"]
    
    for query in queries:
        print(f"\n搜索: {query}")
        result = service.search_coin(query)
        if result:
            print(f"  找到: {result['name']} ({result['symbol']}) - ID: {result['id']}")
            print(f"  市值排名: #{result.get('market_cap_rank', 'N/A')}")
        else:
            print(f"  未找到")


def test_cache():
    """测试缓存功能"""
    print("\n" + "=" * 60)
    print("测试缓存功能")
    print("=" * 60)
    
    service = CoinGeckoService()
    
    import time
    
    print("\n第一次查询 BTC（从 API 获取）...")
    start = time.time()
    btc_info1 = service.get_token_info("BTC")
    time1 = time.time() - start
    print(f"耗时: {time1:.2f} 秒")
    
    print("\n第二次查询 BTC（从缓存获取）...")
    start = time.time()
    btc_info2 = service.get_token_info("BTC")
    time2 = time.time() - start
    print(f"耗时: {time2:.2f} 秒")
    
    print(f"\n缓存加速: {time1/time2:.1f}x")


def test_integration_with_pipeline():
    """测试与分析流水线集成"""
    print("\n" + "=" * 60)
    print("测试与分析流水线集成")
    print("=" * 60)
    
    from app.services.analysis.pipeline import AnalysisPipeline
    from app.services.rag.rag_service import RAGService
    
    # 创建服务
    rag_service = RAGService()
    market_service = CoinGeckoService()
    
    # 创建流水线
    pipeline = AnalysisPipeline(
        rag_service=rag_service,
        market_service=market_service
    )
    
    print("\n✓ 流水线创建成功，已集成市场数据服务")
    print(f"  - RAG 服务: {'已启用' if pipeline.rag_service else '未启用'}")
    print(f"  - 市场数据服务: {'已启用' if pipeline.market_service else '未启用'}")
    
    # 模拟一个简单的状态测试
    print("\n模拟代币信息获取...")
    test_tokens = ["BTC", "ETH"]
    
    for token in test_tokens:
        info = market_service.get_token_info(token)
        if info:
            print(f"\n{token}:")
            print(f"  价格: ${info['current_price_usd']:,.2f}")
            print(f"  24h涨跌: {info['price_change_24h']:+.2f}%")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("CoinGecko 市场数据服务测试")
    print("=" * 60)
    
    try:
        # 1. 测试单个代币
        test_single_token()
        
        # 2. 测试搜索
        test_search()
        
        # 3. 测试缓存
        test_cache()
        
        # 4. 测试批量查询（可选，会比较慢）
        print("\n是否测试批量查询？(y/n): ", end="")
        if input().lower() == 'y':
            test_multiple_tokens()
        
        # 5. 测试集成
        test_integration_with_pipeline()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
