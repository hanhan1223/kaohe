"""系统集成测试脚本"""
import sys
sys.path.append('.')

import time
import requests
from app.db.database import get_db_context
from app.db.models import News, Analysis


def test_api_health():
    """测试 API 健康检查"""
    print("Testing API health...")
    response = requests.get("http://localhost:8000/health")
    assert response.status_code == 200
    print("✓ API is healthy")


def test_submit_analysis():
    """测试提交分析任务"""
    print("\nTesting submit analysis...")
    
    # 获取一条快讯
    with get_db_context() as db:
        news = db.query(News).first()
        if not news:
            print("✗ No news found in database")
            return None
    
    # 提交分析
    response = requests.post(
        "http://localhost:8000/api/v1/analysis/submit",
        json={"news_id": news.id}
    )
    
    assert response.status_code == 200
    result = response.json()
    print(f"✓ Analysis submitted: task_id={result['task_id']}")
    
    return news.id


def test_batch_submit():
    """测试批量提交"""
    print("\nTesting batch submit...")
    
    # 获取多条快讯
    with get_db_context() as db:
        news_list = db.query(News).limit(5).all()
        news_ids = [n.id for n in news_list]
    
    if not news_ids:
        print("✗ No news found in database")
        return
    
    # 批量提交
    response = requests.post(
        "http://localhost:8000/api/v1/analysis/batch",
        json={"news_ids": news_ids}
    )
    
    assert response.status_code == 200
    result = response.json()
    print(f"✓ Batch submitted: {result['total']} tasks")


def test_get_analysis(news_id: int, max_wait: int = 60):
    """测试查询分析结果"""
    print(f"\nTesting get analysis (waiting up to {max_wait}s)...")
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        response = requests.get(f"http://localhost:8000/api/v1/analysis/{news_id}")
        
        if response.status_code == 200:
            result = response.json()
            
            if result['pipeline_status'] == 'completed':
                print("✓ Analysis completed")
                print(f"  - Has investment value: {result['has_investment_value']}")
                print(f"  - Tokens: {result['tokens']}")
                print(f"  - Recommendation: {result['recommendation']}")
                print(f"  - Confidence: {result['confidence_score']}")
                return result
            elif result['pipeline_status'] == 'failed':
                print(f"✗ Analysis failed: {result['error_message']}")
                return None
            else:
                print(f"  Waiting... (status: {result['pipeline_status']})")
        
        time.sleep(5)
    
    print("✗ Analysis timeout")
    return None


def test_overview():
    """测试分析概览"""
    print("\nTesting analysis overview...")
    
    response = requests.get("http://localhost:8000/api/v1/analysis/overview/stats")
    
    if response.status_code == 200:
        result = response.json()
        print("✓ Overview retrieved")
        print(f"  - Total analyses: {result['total_analyses']}")
        print(f"  - Completed: {result['completed']}")
        print(f"  - Has value: {result['has_value_count']}")
        print(f"  - BUY: {result['buy_count']}, SELL: {result['sell_count']}, HOLD: {result['hold_count']}")
        print(f"  - Avg confidence: {result['avg_confidence']:.2f}")
    else:
        print("✗ Failed to get overview")


def test_accuracy():
    """测试准确率"""
    print("\nTesting accuracy...")
    
    with get_db_context() as db:
        # 获取已完成的分析
        analyses = db.query(Analysis).filter(
            Analysis.pipeline_status == 'completed'
        ).all()
        
        if not analyses:
            print("✗ No completed analyses found")
            return
        
        print(f"Found {len(analyses)} completed analyses")
        
        # 统计
        has_value_count = sum(1 for a in analyses if a.has_investment_value)
        has_tokens_count = sum(1 for a in analyses if a.tokens)
        has_recommendation_count = sum(1 for a in analyses if a.recommendation)
        
        print(f"  - Has investment value: {has_value_count}/{len(analyses)} ({has_value_count/len(analyses)*100:.1f}%)")
        print(f"  - Has tokens: {has_tokens_count}/{len(analyses)} ({has_tokens_count/len(analyses)*100:.1f}%)")
        print(f"  - Has recommendation: {has_recommendation_count}/{len(analyses)} ({has_recommendation_count/len(analyses)*100:.1f}%)")
        
        # 计算平均置信度
        confidences = [a.confidence_score for a in analyses if a.confidence_score]
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
            print(f"  - Average confidence: {avg_confidence:.2f}")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Web3 Investment Analysis System - Integration Test")
    print("=" * 60)
    
    try:
        # 1. 健康检查
        test_api_health()
        
        # 2. 提交分析
        news_id = test_submit_analysis()
        
        # 3. 批量提交
        test_batch_submit()
        
        # 4. 等待并查询结果
        if news_id:
            test_get_analysis(news_id)
        
        # 5. 查询概览
        time.sleep(5)  # 等待一些任务完成
        test_overview()
        
        # 6. 测试准确率
        test_accuracy()
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
