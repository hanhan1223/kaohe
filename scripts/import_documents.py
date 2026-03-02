"""批量导入 RAG 知识库文档"""
import sys
sys.path.append('.')

from app.services.rag.rag_service import RAGService
from pathlib import Path
import json
import re


def extract_markdown_metadata(content: str) -> tuple:
    """从 Markdown 文件中提取元数据和内容"""
    # 检查是否有 YAML front matter
    yaml_pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.match(yaml_pattern, content, re.DOTALL)
    
    if match:
        # 解析 YAML front matter
        front_matter = match.group(1)
        main_content = match.group(2)
        
        metadata = {}
        for line in front_matter.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip()] = value.strip()
        
        return metadata, main_content
    
    return {}, content


def extract_title_from_markdown(content: str) -> str:
    """从 Markdown 内容中提取标题"""
    # 查找第一个 # 标题
    lines = content.split('\n')
    for line in lines:
        if line.strip().startswith('# '):
            return line.strip()[2:].strip()
    
    return None


def import_from_json(json_file: str):
    """从 JSON 文件导入文档"""
    rag_service = RAGService()
    
    with open(json_file, 'r', encoding='utf-8') as f:
        documents = json.load(f)
    
    print(f"准备导入 {len(documents)} 篇文档...")
    
    success_count = 0
    fail_count = 0
    
    for idx, doc in enumerate(documents, 1):
        try:
            doc_id = rag_service.add_document(
                title=doc['title'],
                content=doc['content'],
                source=doc.get('source', 'unknown'),
                doc_type=doc.get('doc_type', 'article'),
                metadata=doc.get('metadata', {})
            )
            print(f"[{idx}/{len(documents)}] ✓ {doc['title'][:50]}... (ID: {doc_id})")
            success_count += 1
        except Exception as e:
            print(f"[{idx}/{len(documents)}] ✗ {doc['title'][:50]}... 错误: {e}")
            fail_count += 1
    
    print(f"\n导入完成！")
    print(f"成功: {success_count} 篇")
    print(f"失败: {fail_count} 篇")
    print(f"总文档数: {rag_service.get_document_count()}")
    print(f"总分块数: {rag_service.get_chunk_count()}")


def import_from_directory(directory: str, recursive: bool = False):
    """从目录导入文档（每个文件一篇文档）"""
    rag_service = RAGService()
    
    path = Path(directory)
    
    # 查找文件
    if recursive:
        files = list(path.rglob('*.txt')) + list(path.rglob('*.md'))
    else:
        files = list(path.glob('*.txt')) + list(path.glob('*.md'))
    
    print(f"在 {directory} 中找到 {len(files)} 个文件...")
    
    success_count = 0
    fail_count = 0
    
    for idx, file_path in enumerate(files, 1):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 如果是 Markdown 文件，尝试提取元数据
            if file_path.suffix == '.md':
                metadata, main_content = extract_markdown_metadata(content)
                
                # 尝试从内容中提取标题
                title = extract_title_from_markdown(main_content)
                if not title:
                    title = metadata.get('title', file_path.stem)
                
                # 从元数据中获取其他信息
                source = metadata.get('source', str(file_path))
                doc_type = metadata.get('type', metadata.get('category', 'article'))
                
                # 清理元数据
                clean_metadata = {k: v for k, v in metadata.items() 
                                if k not in ['title', 'source', 'type', 'category']}
                clean_metadata['filename'] = file_path.name
                
            else:
                # 纯文本文件
                title = file_path.stem
                main_content = content
                source = str(file_path)
                clean_metadata = {'filename': file_path.name}
                
                # 从文件名推断文档类型
                doc_type = 'article'
                if 'whitepaper' in file_path.name.lower():
                    doc_type = 'whitepaper'
                elif 'tokenomics' in file_path.name.lower():
                    doc_type = 'tokenomics'
            
            # 导入文档
            doc_id = rag_service.add_document(
                title=title,
                content=main_content,
                source=source,
                doc_type=doc_type,
                metadata=clean_metadata
            )
            
            print(f"[{idx}/{len(files)}] ✓ {title[:50]}... (ID: {doc_id})")
            success_count += 1
            
        except Exception as e:
            print(f"[{idx}/{len(files)}] ✗ {file_path.name} 错误: {e}")
            fail_count += 1
    
    print(f"\n导入完成！")
    print(f"成功: {success_count} 篇")
    print(f"失败: {fail_count} 篇")
    print(f"总文档数: {rag_service.get_document_count()}")
    print(f"总分块数: {rag_service.get_chunk_count()}")


def show_stats():
    """显示知识库统计信息"""
    rag_service = RAGService()
    
    print("知识库统计信息：")
    print(f"  文档总数: {rag_service.get_document_count()}")
    print(f"  分块总数: {rag_service.get_chunk_count()}")
    
    # 按类型统计
    from app.db.database import get_db_context
    from app.db.models import Document
    from sqlalchemy import func
    
    with get_db_context() as db:
        type_stats = db.query(
            Document.doc_type,
            func.count(Document.id)
        ).group_by(Document.doc_type).all()
        
        if type_stats:
            print("\n  按类型分布:")
            for doc_type, count in type_stats:
                print(f"    {doc_type}: {count} 篇")


def test_search(query: str, k: int = 5, method: str = "hybrid"):
    """测试检索功能"""
    rag_service = RAGService()
    
    print(f"搜索: '{query}'")
    print(f"检索方法: {method}")
    print(f"返回前 {k} 个结果:\n")
    
    results = rag_service.search(query, k=k, method=method)
    
    for idx, result in enumerate(results, 1):
        # 获取标题（从元数据中）
        title = result.get('metadata', {}).get('title', 'Unknown')
        
        # 获取分数
        if method == "hybrid":
            score = result.get('hybrid_score', 0)
            score_label = "混合分数"
        elif method == "bm25":
            score = result.get('bm25_score', 0)
            score_label = "BM25分数"
        else:  # vector
            score = result.get('vector_score', 0)
            score_label = "向量分数"
        
        print(f"{idx}. 【{title}】")
        print(f"   {score_label}: {score:.4f}")
        
        # 如果是混合检索，显示详细分数
        if method == "hybrid":
            print(f"   向量: {result.get('vector_score', 0):.4f}, BM25: {result.get('bm25_score', 0):.4f}")
        
        print(f"   内容: {result['content'][:150]}...")
        print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="导入 RAG 知识库文档",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 从 JSON 文件导入
  python scripts/import_documents.py --json data/documents.json
  
  # 从目录导入 Markdown 文件
  python scripts/import_documents.py --dir data/documents/
  
  # 递归导入子目录中的文件
  python scripts/import_documents.py --dir data/documents/ --recursive
  
  # 查看知识库统计
  python scripts/import_documents.py --stats
  
  # 测试检索
  python scripts/import_documents.py --test "比特币价格分析"
        """
    )
    
    parser.add_argument('--json', type=str, help='从 JSON 文件导入')
    parser.add_argument('--dir', type=str, help='从目录导入（.txt 和 .md 文件）')
    parser.add_argument('--recursive', action='store_true', help='递归导入子目录')
    parser.add_argument('--stats', action='store_true', help='显示知识库统计信息')
    parser.add_argument('--test', type=str, help='测试检索功能')
    parser.add_argument('-k', type=int, default=5, help='检索返回结果数量（默认 5）')
    
    args = parser.parse_args()
    
    if args.json:
        import_from_json(args.json)
    elif args.dir:
        import_from_directory(args.dir, args.recursive)
    elif args.stats:
        show_stats()
    elif args.test:
        test_search(args.test, args.k)
    else:
        parser.print_help()
