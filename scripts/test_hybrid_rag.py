"""测试混合 RAG 服务"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.rag.hybrid_rag_service import (
    HybridRAGService,
    SlidingWindowSplitter,
    BM25Retriever
)


def test_sliding_window_splitter():
    """测试滑动窗口切分器"""
    print("=" * 60)
    print("测试滑动窗口切分器")
    print("=" * 60)
    
    splitter = SlidingWindowSplitter(
        chunk_size=100,
        overlap_size=20
    )
    
    text = """比特币是一种去中心化的数字货币。它不需要中央银行或单一管理员。
比特币可以在点对点网络上从一个用户发送到另一个用户，无需中介。
网络通过加密验证交易，并将其记录在区块链上。
比特币由中本聪于2008年发明。比特币的供应量有限，最多只能有2100万枚。"""
    
    chunks = splitter.split_text(text)
    
    print(f"\n原文长度: {len(text)} 字符")
    print(f"切分块数: {len(chunks)} 块")
    print(f"块大小: {splitter.chunk_size} 字符")
    print(f"重叠大小: {splitter.overlap_size} 字符")
    
    for i, chunk in enumerate(chunks):
        print(f"\n--- 块 {i+1} ({len(chunk)} 字符) ---")
        print(chunk[:100] + "..." if len(chunk) > 100 else chunk)
        
        # 检查重叠
        if i > 0:
            prev_chunk = chunks[i-1]
            # 查找重叠部分
            overlap_found = False
            for j in range(min(50, len(prev_chunk))):
                suffix = prev_chunk[-j:]
                if chunk.startswith(suffix):
                    print(f"✓ 与前一块重叠 {j} 字符")
                    overlap_found = True
                    break
            if not overlap_found:
                print("⚠ 未检测到重叠")


def test_bm25_retriever():
    """测试 BM25 检索器"""
    print("\n" + "=" * 60)
    print("测试 BM25 检索器")
    print("=" * 60)
    
    # 准备语料库
    corpus = [
        "比特币是一种去中心化的数字货币",
        "以太坊支持智能合约功能",
        "DeFi 是去中心化金融的缩写",
        "Uniswap 是一个去中心化交易所",
        "比特币的价格波动很大"
    ]
    corpus_ids = [1, 2, 3, 4, 5]
    
    # 训练 BM25
    bm25 = BM25Retriever()
    bm25.fit(corpus, corpus_ids)
    
    print(f"\n语料库大小: {len(corpus)} 篇文档")
    print(f"平均文档长度: {bm25.avgdl:.2f} 词")
    print(f"词汇表大小: {len(bm25.idf)} 词")
    
    # 测试查询
    queries = [
        "比特币价格",
        "去中心化交易",
        "智能合约"
    ]
    
    for query in queries:
        print(f"\n查询: '{query}'")
        results = bm25.search(query, k=3)
        
        for rank, (doc_id, score) in enumerate(results, 1):
            doc_idx = corpus_ids.index(doc_id)
            print(f"  {rank}. [分数: {score:.4f}] {corpus[doc_idx]}")


def test_hybrid_search():
    """测试混合检索"""
    print("\n" + "=" * 60)
    print("测试混合检索（需要数据库）")
    print("=" * 60)
    
    try:
        service = HybridRAGService()
        
        # 检查是否有数据
        doc_count = service.get_document_count()
        chunk_count = service.get_chunk_count()
        
        print(f"\n知识库状态:")
        print(f"  文档数: {doc_count}")
        print(f"  分块数: {chunk_count}")
        
        if chunk_count == 0:
            print("\n⚠ 知识库为空，请先运行: python -m app.services.rag.rag_service")
            return
        
        # 测试查询
        query = "比特币的价格和市值"
        
        print(f"\n查询: '{query}'")
        print("\n" + "-" * 60)
        
        # 1. 向量检索
        print("\n【向量检索】")
        vector_results = service.vector_search(query, k=3)
        for i, result in enumerate(vector_results, 1):
            print(f"\n{i}. [向量分数: {result['vector_score']:.4f}]")
            print(f"   {result['content'][:100]}...")
        
        # 2. BM25 检索
        print("\n【BM25 检索】")
        bm25_results = service.bm25_search(query, k=3)
        for i, result in enumerate(bm25_results, 1):
            print(f"\n{i}. [BM25 分数: {result['bm25_score']:.4f}]")
            print(f"   {result['content'][:100]}...")
        
        # 3. 混合检索
        print("\n【混合检索】")
        hybrid_results = service.hybrid_search(query, k=3)
        for i, result in enumerate(hybrid_results, 1):
            print(f"\n{i}. [混合分数: {result['hybrid_score']:.4f}]")
            print(f"   向量: {result['vector_score']:.4f}, BM25: {result['bm25_score']:.4f}")
            print(f"   {result['content'][:100]}...")
        
        # 4. 对比不同方法
        print("\n" + "=" * 60)
        print("检索方法对比")
        print("=" * 60)
        
        methods = ["vector", "bm25", "hybrid"]
        for method in methods:
            results = service.search(query, k=3, method=method)
            print(f"\n【{method.upper()}】返回 {len(results)} 个结果")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_add_document():
    """测试添加文档（滑动窗口切分）"""
    print("\n" + "=" * 60)
    print("测试添加文档（滑动窗口切分）")
    print("=" * 60)
    
    try:
        service = HybridRAGService()
        
        # 添加测试文档
        test_doc = {
            "title": "测试文档 - Web3 投资分析",
            "content": """Web3 是下一代互联网的愿景，基于区块链技术构建。
            
Web3 的核心特征包括去中心化、用户拥有数据、代币经济等。
在 Web3 生态中，用户可以真正拥有自己的数字资产和数据。

比特币是第一个成功的区块链应用，它证明了去中心化货币的可行性。
以太坊则进一步扩展了区块链的应用场景，引入了智能合约。

DeFi（去中心化金融）是 Web3 最重要的应用领域之一。
通过 DeFi 协议，用户可以进行借贷、交易、流动性挖矿等金融活动。

NFT（非同质化代币）是另一个重要的 Web3 应用。
NFT 可以代表数字艺术品、游戏道具、虚拟土地等独特的数字资产。

Web3 投资需要关注项目的技术实力、团队背景、代币经济模型等因素。
同时也要注意市场风险、监管风险、技术风险等。""",
            "source": "test",
            "doc_type": "article"
        }
        
        print("\n添加文档...")
        doc_id = service.add_document(**test_doc)
        print(f"✓ 文档已添加，ID: {doc_id}")
        
        # 查询统计
        print(f"\n知识库统计:")
        print(f"  文档总数: {service.get_document_count()}")
        print(f"  分块总数: {service.get_chunk_count()}")
        
        # 测试检索
        print("\n测试检索新添加的文档...")
        query = "Web3 投资风险"
        results = service.search(query, k=2, method="hybrid")
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. [分数: {result['hybrid_score']:.4f}]")
            print(f"   {result['content'][:150]}...")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("混合 RAG 服务测试套件")
    print("=" * 60)
    
    # 1. 测试滑动窗口切分
    test_sliding_window_splitter()
    
    # 2. 测试 BM25
    test_bm25_retriever()
    
    # 3. 测试混合检索（需要数据库）
    print("\n是否测试混合检索？(需要数据库连接) (y/n): ", end="")
    if input().lower() == 'y':
        test_hybrid_search()
    
    # 4. 测试添加文档
    print("\n是否测试添加文档？(会修改数据库) (y/n): ", end="")
    if input().lower() == 'y':
        test_add_document()
    
    print("\n" + "=" * 60)
    print("✓ 测试完成")
    print("=" * 60)
    
    print("\n功能特性:")
    print("  ✓ 滑动窗口切分（重叠部分保留上下文）")
    print("  ✓ BM25 关键词检索（基于词频统计）")
    print("  ✓ 向量语义检索（基于 OpenAI Embeddings）")
    print("  ✓ 混合检索（结合向量和 BM25）")
    print("  ✓ 可配置的权重调整")


if __name__ == "__main__":
    main()
