"""导入示例数据"""
import sys
sys.path.append('.')

from app.db.database import get_db_context
from app.db.models import News
from datetime import datetime, timedelta


def import_sample_news():
    """导入示例快讯数据"""
    sample_news = [
        {
            "odaily_id": "sample_001",
            "title": "比特币突破 10 万美元大关",
            "content": "比特币价格今日突破 10 万美元，创历史新高。市场分析师认为这是机构投资者大量买入的结果。多家华尔街机构增持 BTC，推动价格持续上涨。",
            "published_at": datetime.utcnow() - timedelta(hours=1)
        },
        {
            "odaily_id": "sample_002",
            "title": "以太坊完成重大升级",
            "content": "以太坊成功完成 Dencun 升级，Gas 费用降低 90%，交易速度提升 10 倍。ETH 价格应声上涨 15%。",
            "published_at": datetime.utcnow() - timedelta(hours=2)
        },
        {
            "odaily_id": "sample_003",
            "title": "某 DeFi 项目获得 1 亿美元融资",
            "content": "去中心化借贷协议 XYZ 获得 a16z 领投的 1 亿美元 B 轮融资。该项目将用于产品开发和市场推广，其代币 XYZ 价格上涨 50%。",
            "published_at": datetime.utcnow() - timedelta(hours=3)
        },
        {
            "odaily_id": "sample_004",
            "title": "Solana 网络再次宕机",
            "content": "Solana 网络今日再次出现宕机，持续时间约 4 小时。这是今年第 3 次大规模宕机事件。SOL 价格下跌 8%。",
            "published_at": datetime.utcnow() - timedelta(hours=4)
        },
        {
            "odaily_id": "sample_005",
            "title": "美国 SEC 批准比特币现货 ETF",
            "content": "美国证券交易委员会（SEC）正式批准多家机构的比特币现货 ETF 申请。这被认为是加密货币行业的里程碑事件。",
            "published_at": datetime.utcnow() - timedelta(hours=5)
        },
        {
            "odaily_id": "sample_006",
            "title": "某 NFT 项目地板价暴跌 90%",
            "content": "曾经火爆的 NFT 项目 ABC 地板价从 10 ETH 暴跌至 1 ETH，跌幅达 90%。项目方被质疑跑路。",
            "published_at": datetime.utcnow() - timedelta(hours=6)
        },
        {
            "odaily_id": "sample_007",
            "title": "Uniswap V4 正式上线",
            "content": "去中心化交易所 Uniswap 发布 V4 版本，引入 Hooks 机制，允许开发者自定义流动性池逻辑。UNI 代币价格上涨 20%。",
            "published_at": datetime.utcnow() - timedelta(hours=7)
        },
        {
            "odaily_id": "sample_008",
            "title": "某交易所遭黑客攻击损失 2 亿美元",
            "content": "中心化交易所 DEF 遭黑客攻击，损失约 2 亿美元加密资产。交易所表示将全额赔偿用户损失。",
            "published_at": datetime.utcnow() - timedelta(hours=8)
        },
        {
            "odaily_id": "sample_009",
            "title": "Polygon 推出 zkEVM 主网",
            "content": "Polygon 正式推出 zkEVM 主网，提供以太坊等效的零知识证明扩容方案。MATIC 价格上涨 25%。",
            "published_at": datetime.utcnow() - timedelta(hours=9)
        },
        {
            "odaily_id": "sample_010",
            "title": "某稳定币脱锚跌至 0.8 美元",
            "content": "算法稳定币 XYZ 出现严重脱锚，价格跌至 0.8 美元。市场恐慌情绪蔓延，多个 DeFi 协议暂停相关业务。",
            "published_at": datetime.utcnow() - timedelta(hours=10)
        }
    ]
    
    with get_db_context() as db:
        for news_data in sample_news:
            # 检查是否已存在
            existing = db.query(News).filter(
                News.odaily_id == news_data['odaily_id']
            ).first()
            
            if existing:
                print(f"News {news_data['odaily_id']} already exists, skipping")
                continue
            
            # 创建新记录
            news = News(**news_data)
            db.add(news)
            print(f"Imported: {news_data['title']}")
        
        db.commit()
    
    print(f"\nImported {len(sample_news)} sample news items")


if __name__ == "__main__":
    import_sample_news()
