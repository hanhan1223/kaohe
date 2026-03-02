"""测试知识库搜索"""
import sys
sys.path.append('.')

from app.services.rag.hybrid_rag_service import HybridRAGService

def test_search():
    """测试搜索功能"""
    rag = HybridRAGService()
    
    print("\n=== 测试向量搜索 ===")
    query = "代币经济学"
    results = rag.vector_search(query, k=3)
    
    print(f"\n查询: {query}")
    print(f"结果数: {len(results)}")
    
    for i, result in enumerate(results, 1):
        print(f"\n[{i}] 分数: {result['vector_score']:.4f}")
        print(f"内容: {result['content'][:100]}...")
        print(f"元数据: {result['metadata']}")
    
    print("\n=== 测试 BM25 搜索 ===")
    results = rag.bm25_search(query, k=3)
    
    print(f"\n查询: {query}")
    print(f"结果数: {len(results)}")
    
    for i, result in enumerate(results, 1):
        print(f"\n[{i}] 分数: {result['bm25_score']:.4f}")
        print(f"内容: {result['content'][:100]}...")
    
    print("\n=== 测试混合搜索 ===")
    results = rag.hybrid_search(query, k=3)
    
    print(f"\n查询: {query}")
    print(f"结果数: {len(results)}")
    
    for i, result in enumerate(results, 1):
        print(f"\n[{i}] 混合分数: {result['hybrid_score']:.4f}")
        print(f"  向量分数: {result['vector_score']:.4f}")
        print(f"  BM25分数: {result['bm25_score']:.4f}")
        print(f"内容: {result['content'][:100]}...")

if __name__ == "__main__":
    test_search()
