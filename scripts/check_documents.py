"""检查知识库文档"""
import sys
sys.path.append('.')

from app.db.database import get_db_context
from app.db.models import Document, DocumentChunk
from sqlalchemy import func
from datetime import datetime, timedelta

def check_documents():
    """检查文档和分块"""
    with get_db_context() as db:
        # 统计文档
        doc_count = db.query(func.count(Document.id)).scalar()
        print(f"\n📚 文档总数: {doc_count}")
        
        # 统计分块
        chunk_count = db.query(func.count(DocumentChunk.id)).scalar()
        print(f"📄 分块总数: {chunk_count}")
        
        # 今天添加的文档
        today = datetime.now().date()
        today_docs = db.query(Document).filter(
            func.date(Document.created_at) == today
        ).all()
        
        print(f"\n📅 今天添加的文档: {len(today_docs)}")
        
        if today_docs:
            for doc in today_docs:
                chunks = db.query(func.count(DocumentChunk.id)).filter(
                    DocumentChunk.document_id == doc.id
                ).scalar()
                print(f"  [{doc.id}] {doc.title[:60]}... ({chunks} 块) - {doc.created_at}")
        else:
            print("  ❌ 今天没有添加任何文档")
        
        # 按类型统计
        print(f"\n按类型统计:")
        type_stats = db.query(
            Document.doc_type,
            func.count(Document.id)
        ).group_by(Document.doc_type).all()
        
        for doc_type, count in type_stats:
            print(f"  {doc_type}: {count}")
        
        # 检查向量
        print(f"\n检查向量嵌入:")
        chunks_with_embedding = db.query(func.count(DocumentChunk.id)).filter(
            DocumentChunk.embedding.isnot(None)
        ).scalar()
        print(f"  有向量的分块: {chunks_with_embedding}/{chunk_count}")
        
        if chunks_with_embedding < chunk_count:
            print(f"  ⚠️ 警告: {chunk_count - chunks_with_embedding} 个分块缺少向量!")

if __name__ == "__main__":
    check_documents()
