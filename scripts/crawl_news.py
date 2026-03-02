"""爬取 Odaily 快讯脚本"""
import sys
sys.path.append('.')

from app.services.crawler.odaily_crawler import OdailyCrawler, clean_news_data
from app.db.database import get_db_context
from app.db.models import News
from datetime import datetime


def crawl_and_save_news(pages: int = 5):
    """爬取并保存快讯"""
    crawler = OdailyCrawler()
    total_saved = 0
    
    for page in range(1, pages + 1):
        print(f"Crawling page {page}...")
        
        news_list = crawler.fetch_news_list(page=page)
        
        for news_data in news_list:
            # 清洗数据
            cleaned = clean_news_data(news_data)
            if not cleaned:
                continue
            
            # 保存到数据库
            with get_db_context() as db:
                # 检查是否已存在
                existing = db.query(News).filter(
                    News.odaily_id == cleaned['odaily_id']
                ).first()
                
                if existing:
                    print(f"News {cleaned['odaily_id']} already exists, skipping")
                    continue
                
                # 准备 raw_data（将 datetime 转换为字符串）
                raw_data_for_json = news_data.copy()
                if 'published_at' in raw_data_for_json and raw_data_for_json['published_at']:
                    raw_data_for_json['published_at'] = raw_data_for_json['published_at'].isoformat()
                
                # 创建新记录
                news = News(
                    odaily_id=cleaned['odaily_id'],
                    title=cleaned['title'],
                    content=cleaned['content'],
                    published_at=cleaned.get('published_at'),
                    source_url=cleaned.get('source_url'),
                    raw_data=raw_data_for_json
                )
                db.add(news)
                db.commit()
                
                total_saved += 1
                print(f"Saved news: {cleaned['title'][:50]}...")
    
    print(f"\nTotal saved: {total_saved} news items")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Crawl Odaily news")
    parser.add_argument("--pages", type=int, default=5, help="Number of pages to crawl")
    
    args = parser.parse_args()
    
    crawl_and_save_news(pages=args.pages)
