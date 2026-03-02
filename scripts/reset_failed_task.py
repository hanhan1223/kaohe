"""重置失败的任务"""
import sys
sys.path.append('.')

from app.db.database import get_db_context
from app.db.models import TaskRecord, Analysis

def reset_task(task_id: str):
    """重置指定任务"""
    with get_db_context() as db:
        # 查找任务
        task = db.query(TaskRecord).filter(TaskRecord.task_id == task_id).first()
        
        if not task:
            print(f"Task {task_id} not found")
            return
        
        print(f"Resetting task {task_id}...")
        print(f"  News ID: {task.news_id}")
        print(f"  Current Status: {task.status}")
        print(f"  Retry Count: {task.retry_count}")
        
        # 重置任务状态
        task.status = "pending"
        task.retry_count = 0
        task.error_message = None
        
        # 删除失败的分析记录
        db.query(Analysis).filter(
            Analysis.news_id == task.news_id,
            Analysis.pipeline_status == "failed"
        ).delete()
        
        db.commit()
        print(f"✓ Task {task_id} has been reset")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
        reset_task(task_id)
    else:
        # 重置所有失败的任务
        with get_db_context() as db:
            failed_tasks = db.query(TaskRecord).filter(
                TaskRecord.status == "failed"
            ).all()
            
            print(f"Found {len(failed_tasks)} failed tasks")
            
            for task in failed_tasks:
                print(f"\nResetting task {task.task_id}...")
                task.status = "pending"
                task.retry_count = 0
                task.error_message = None
                
                # 删除失败的分析记录
                db.query(Analysis).filter(
                    Analysis.news_id == task.news_id,
                    Analysis.pipeline_status == "failed"
                ).delete()
            
            db.commit()
            print(f"\n✓ Reset {len(failed_tasks)} tasks")
