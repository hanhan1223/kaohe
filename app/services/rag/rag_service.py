"""RAG 知识库服务"""
from app.services.rag.hybrid_rag_service import HybridRAGService

# 使用混合 RAG 服务作为默认实现
RAGService = HybridRAGService

__all__ = ["RAGService", "HybridRAGService"]


def build_knowledge_base():
    """构建知识库（示例）"""
    from app.services.rag.hybrid_rag_service import HybridRAGService
    
    rag_service = HybridRAGService()
    
    # 示例文档
    sample_docs = [
        {
            "title": "比特币白皮书",
            "content": """比特币：一种点对点的电子现金系统
            
比特币是一种去中心化的数字货币，不需要中央银行或单一管理员。
它可以在点对点比特币网络上从一个用户发送到另一个用户，无需中介。

网络通过加密验证交易，并将其记录在称为区块链的公共分布式账本中。
比特币由一个名为中本聪的未知人士或团体于 2008 年发明。

比特币的供应量有限，最多只能有 2100 万枚。这种稀缺性是其价值的重要因素之一。""",
            "source": "bitcoin.org",
            "doc_type": "whitepaper"
        },
        {
            "title": "以太坊智能合约",
            "content": """以太坊是一个去中心化的开源区块链平台，具有智能合约功能。

智能合约是存储在区块链上的程序，当满足预定条件时自动执行。
它们用于自动化协议的执行，使所有参与者可以立即确定结果，无需中介参与。

以太坊的原生加密货币是以太币（ETH）。它是仅次于比特币的第二大加密货币。
以太坊于 2015 年由 Vitalik Buterin 等人创立。""",
            "source": "ethereum.org",
            "doc_type": "whitepaper"
        },
        {
            "title": "DeFi 去中心化金融",
            "content": """DeFi（去中心化金融）是基于区块链的金融服务，不依赖传统金融中介。

主要 DeFi 应用包括：
1. 去中心化交易所（DEX）- 如 Uniswap, SushiSwap
2. 借贷协议 - 如 Aave, Compound
3. 稳定币 - 如 DAI, USDC
4. 流动性挖矿和收益农场

DeFi 的优势包括透明度、可访问性和可组合性。
但也存在智能合约风险、价格波动等挑战。""",
            "source": "defipulse.com",
            "doc_type": "article"
        }
    ]
    
    print("Building knowledge base with sliding window chunking...")
    for doc in sample_docs:
        doc_id = rag_service.add_document(**doc)
        print(f"Added document: {doc['title']} (ID: {doc_id})")
    
    print(f"\nTotal documents: {rag_service.get_document_count()}")
    print(f"Total chunks: {rag_service.get_chunk_count()}")
    print("Knowledge base built successfully!")


if __name__ == "__main__":
    build_knowledge_base()
