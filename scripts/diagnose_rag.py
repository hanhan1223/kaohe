"""诊断 RAG 知识库状态"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import get_db_context
from app.db.models import Document, DocumentChunk
from sqlalchemy import func


def diagnose_database():
    """诊断数据库状态"""
    print("=" * 60)
    print("RAG 知识库诊断")
    print("=" * 60)
    
    with get_db_context() as db:
        # 1. 文档统计
        doc_count = db.query(func.count(Document.id)).scalar()
        chunk_count = db.query(func.count(DocumentChunk.id)).scalar()
        
        print(f"\n【基本统计】")
        print(f"  文档总数: {doc_count}")
        print(f"  分块总数: {chunk_count}")
        
        if doc_count == 0:
            print("\n⚠ 知识库为空！")
            print("  请先导入文档:")
            print("  python scripts/import_documents.py --dir data/documents/")
            return
        
        # 2. 按类型统计
        print(f"\n【按类型分布】")
        type_stats = db.query(
            Document.doc_type,
            func.count(Document.id)
        ).group_by(Document.doc_type).all()
        
        for doc_type, count in type_stats:
            print(f"  {doc_type}: {count} 篇")
        
        # 3. 分块统计
        print(f"\n【分块统计】")
        avg_chunks = db.query(
            func.avg(
                db.query(func.count(DocumentChunk.id))
                .filter(DocumentChunk.document_id == Document.id)
                .correlate(Document)
                .scalar_subquery()
            )
        ).scalar()
        
        if avg_chunks:
            print(f"  平均每篇文档分块数: {avg_chunks:.1f}")
        
        # 查询分块大小分布
        chunks = db.query(DocumentChunk).limit(100).all()
        if chunks:
            chunk_sizes = [len(chunk.content) for chunk in chunks]
            avg_size = sum(chunk_sizes) / len(chunk_sizes)
            min_size = min(chunk_sizes)
            max_size = max(chunk_sizes)
            
            print(f"  分块大小（前100个）:")
            print(f"    平均: {avg_size:.0f} 字符")
            print(f"    最小: {min_size} 字符")
            print(f"    最大: {max_size} 字符")
        
        # 4. 检查切分方式
        print(f"\n【切分方式检查】")
        
        # 检查是否有重叠
        sample_doc = db.query(Document).first()
        if sample_doc:
            doc_chunks = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == sample_doc.id
            ).order_by(DocumentChunk.chunk_index).all()
            
            if len(doc_chunks) > 1:
                # 检查相邻块是否有重叠
                has_overlap = False
                overlap_sizes = []
                
                for i in range(len(doc_chunks) - 1):
                    chunk1 = doc_chunks[i].content
                    chunk2 = doc_chunks[i + 1].content
                    
                    # 检查 chunk2 的开头是否在 chunk1 中出现
                    for length in range(min(300, len(chunk2)), 50, -10):
                        prefix = chunk2[:length]
                        if prefix in chunk1:
                            has_overlap = True
                            overlap_sizes.append(length)
                            break
                
                if has_overlap:
                    avg_overlap = sum(overlap_sizes) / len(overlap_sizes)
                    print(f"  ✓ 使用滑动窗口切分")
                    print(f"  平均重叠大小: {avg_overlap:.0f} 字符")
                else:
                    print(f"  ⚠ 未检测到重叠（可能使用传统切分）")
            else:
                print(f"  文档只有 1 个分块，无法检测")
        
        # 5. 检查向量嵌入
        print(f"\n【向量嵌入检查】")
        chunks_with_embedding = db.query(func.count(DocumentChunk.id)).filter(
            DocumentChunk.embedding.isnot(None)
        ).scalar()
        
        print(f"  有向量的分块: {chunks_with_embedding}/{chunk_count}")
        
        if chunks_with_embedding < chunk_count:
            print(f"  ⚠ 有 {chunk_count - chunks_with_embedding} 个分块缺少向量")
        else:
            print(f"  ✓ 所有分块都有向量")
        
        # 6. 检查元数据
        print(f"\n【元数据检查】")
        sample_chunk = db.query(DocumentChunk).first()
        if sample_chunk and sample_chunk.chunk_metadata:
            print(f"  元数据字段: {list(sample_chunk.chunk_metadata.keys())}")
            
            # 检查是否有新的元数据字段（滑动窗口特有）
            if 'overlap_size' in sample_chunk.chunk_metadata:
                print(f"  ✓ 包含滑动窗口元数据")
                print(f"    块大小: {sample_chunk.chunk_metadata.get('chunk_size')}")
                print(f"    重叠大小: {sample_chunk.chunk_metadata.get('overlap_size')}")
            else:
                print(f"  ⚠ 缺少滑动窗口元数据（可能是旧数据）")
        
        # 7. 列出文档
        print(f"\n【文档列表】")
        docs = db.query(Document).limit(10).all()
        for i, doc in enumerate(docs, 1):
            chunk_count_for_doc = db.query(func.count(DocumentChunk.id)).filter(
                DocumentChunk.document_id == doc.id
            ).scalar()
            print(f"  {i}. {doc.title[:50]}... ({chunk_count_for_doc} 块)")


def check_bm25():
    """检查 BM25 状态"""
    print("\n" + "=" * 60)
    print("BM25 检索器检查")
    print("=" * 60)
    
    try:
        from app.services.rag.rag_service import RAGService
        
        service = RAGService()
        
        if service.bm25:
            print(f"\n✓ BM25 已初始化")
            print(f"  语料库大小: {len(service.bm25.corpus)} 篇")
            print(f"  词汇表大小: {len(service.bm25.idf)} 词")
            print(f"  平均文档长度: {service.bm25.avgdl:.1f} 词")
        else:
            print(f"\n⚠ BM25 未初始化")
            print(f"  可能原因: 知识库为空")
    except Exception as e:
        print(f"\n✗ BM25 检查失败: {e}")


def test_retrieval():
    """测试检索功能"""
    print("\n" + "=" * 60)
    print("检索功能测试")
    print("=" * 60)
    
    try:
        from app.services.rag.rag_service import RAGService
        
        service = RAGService()
        
        # 测试查询
        test_queries = [
            "比特币",
            "以太坊",
            "DeFi"
        ]
        
        for query in test_queries:
            print(f"\n查询: '{query}'")
            
            try:
                # 测试混合检索
                results = service.search(query, k=2, method="hybrid")
                
                if results:
                    print(f"  ✓ 返回 {len(results)} 个结果")
                    for i, result in enumerate(results, 1):
                        title = result.get('metadata', {}).get('title', 'Unknown')
                        score = result.get('hybrid_score', 0)
                        print(f"    {i}. {title[:40]}... (分数: {score:.4f})")
                else:
                    print(f"  ⚠ 无结果")
            except Exception as e:
                print(f"  ✗ 检索失败: {e}")
    
    except Exception as e:
        print(f"\n✗ 检索测试失败: {e}")


def provide_recommendations():
    """提供建议"""
    print("\n" + "=" * 60)
    print("建议")
    print("=" * 60)
    
    with get_db_context() as db:
        doc_count = db.query(func.count(Document.id)).scalar()
        chunk_count = db.query(func.count(DocumentChunk.id)).scalar()
        
        if doc_count == 0:
            print("\n1. 导入文档到知识库:")
            print("   python scripts/import_documents.py --dir data/documents/")
        else:
            # 检查是否使用旧切分
            sample_chunk = db.query(DocumentChunk).first()
            if sample_chunk and 'overlap_size' not in sample_chunk.chunk_metadata:
                print("\n1. ⚠ 检测到旧的切分方式")
                print("   建议重新导入文档以使用滑动窗口切分:")
                print("   ")
                print("   # 1. 清空知识库")
                print("   python -c \"from app.db.database import get_db_context; from app.db.models import Document, DocumentChunk; db = get_db_context().__enter__(); db.query(DocumentChunk).delete(); db.query(Document).delete(); db.commit()\"")
                print("   ")
                print("   # 2. 重新导入")
                print("   python scripts/import_documents.py --dir data/documents/")
            else:
                print("\n1. ✓ 知识库状态良好")
        
        print("\n2. 测试检索功能:")
        print("   python scripts/import_documents.py --test \"比特币价格\"")
        
        print("\n3. 对比不同检索方法:")
        print("   python scripts/import_documents.py --test \"比特币\" --method vector")
        print("   python scripts/import_documents.py --test \"比特币\" --method bm25")
        print("   python scripts/import_documents.py --test \"比特币\" --method hybrid")
        
        print("\n4. 查看详细文档:")
        print("   HYBRID_RAG.md")


def main():
    """主函数"""
    print("\n")
    
    # 1. 诊断数据库
    diagnose_database()
    
    # 2. 检查 BM25
    check_bm25()
    
    # 3. 测试检索
    test_retrieval()
    
    # 4. 提供建议
    provide_recommendations()
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
