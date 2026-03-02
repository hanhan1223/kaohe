"""检查失败的任务"""
import sys
sys.path.append('.')

from app.db.database import get_db_context
from app.db.models import TaskRecord, Analysis, News

def check_failed_tasks():
    """检查失败的任务"""
    with get_db_context() as db:
        # 查询失败或重试中的任务
        failed_tasks = db.query(TaskRecord).filter(
            TaskRecord.status.in_(["processing", "failed"])
        ).order_by(TaskRecord.created_at.desc()).limit(10).all()
        
        print(f"\n=== 失败/处理中的任务 (最近10条) ===\n")
        
        for task in failed_tasks:
            print(f"Task ID: {task.task_id}")
            print(f"News ID: {task.news_id}")
            print(f"Status: {task.status}")
            print(f"Retry Count: {task.retry_count}")
            print(f"Error: {task.error_message or 'No error message'}")
            print(f"Created: {task.created_at}")
            
            # 获取对应的快讯
            news = db.query(News).filter(News.id == task.news_id).first()
            if news:
                print(f"News Title: {news.title[:50]}...")
            
            # 获取对应的分析记录
            analysis = db.query(Analysis).filter(
                Analysis.news_id == task.news_id
            ).order_by(Analysis.created_at.desc()).first()
            
            if analysis:
                print(f"Analysis Status: {analysis.pipeline_status}")
                print(f"Analysis Error: {analysis.error_message or 'No error'}")
            
            print("-" * 80)

if __name__ == "__main__":
    check_failed_tasks()
