"""测试 with_structured_output"""
import sys
sys.path.append('.')

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from app.core.config import settings


class InvestmentValue(BaseModel):
    """投资价值判断"""
    has_value: bool = Field(description="是否有投资价值")
    reasoning: str = Field(description="判断理由")
    confidence: float = Field(description="置信度 0-1")


def test_structured_output():
    """测试结构化输出"""
    print("=== 测试 with_structured_output ===\n")
    
    # 打印配置
    print(f"OpenAI Model: {settings.OPENAI_MODEL}")
    print(f"OpenAI Base URL: {settings.OPENAI_API_BASE}")
    print(f"API Key: {settings.OPENAI_API_KEY[:10]}..." if settings.OPENAI_API_KEY else "Not set")
    print()
    
    # 创建 LLM
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.0,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE
    )
    
    # 使用 with_structured_output
    structured_llm = llm.with_structured_output(InvestmentValue)
    
    # 创建 prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个专业的 Web3 投资分析师。
分析给定的快讯，判断是否具有投资价值。

投资价值的判断标准：
1. 是否涉及代币价格变动、项目融资、技术突破等
2. 是否对市场有实质性影响
3. 是否包含可操作的投资信息"""),
        ("user", "标题: {title}\n\n内容: {content}")
    ])
    
    chain = prompt | structured_llm
    
    # 测试数据
    test_title = "比特币突破10万美元大关"
    test_content = "今日比特币价格突破10万美元，创历史新高。市场分析师认为这是机构投资者大量买入的结果。"
    
    print(f"测试标题: {test_title}")
    print(f"测试内容: {test_content}\n")
    
    try:
        print("调用 LLM...")
        result = chain.invoke({
            "title": test_title,
            "content": test_content
        })
        
        print(f"\n✓ 调用成功!")
        print(f"Result type: {type(result)}")
        print(f"Result: {result}")
        
        if result is None:
            print("\n❌ 错误: LLM 返回了 None")
        else:
            print(f"\n结果:")
            print(f"  has_value: {result.has_value}")
            print(f"  reasoning: {result.reasoning}")
            print(f"  confidence: {result.confidence}")
            
    except Exception as e:
        import traceback
        print(f"\n❌ 调用失败: {e}")
        print(f"\nTraceback:\n{traceback.format_exc()}")


if __name__ == "__main__":
    test_structured_output()
