"""LangGraph 分析流水线"""
import json
import re
from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from app.core.config import settings


# 定义输出模型
class InvestmentValue(BaseModel):
    """投资价值判断"""
    has_value: bool = Field(description="是否有投资价值")
    reasoning: str = Field(description="判断理由")
    confidence: float = Field(description="置信度 0-1")


class TokenExtraction(BaseModel):
    """代币提取"""
    tokens: List[str] = Field(description="代币符号列表")
    reasoning: str = Field(description="提取理由")


class TrendAnalysis(BaseModel):
    """趋势分析"""
    token: str = Field(description="代币符号")
    trend: str = Field(description="趋势: BULLISH/BEARISH/NEUTRAL")
    reasoning: str = Field(description="分析理由")
    confidence: float = Field(description="置信度 0-1")


class InvestmentRecommendation(BaseModel):
    """投资建议"""
    recommendation: str = Field(description="建议: BUY/SELL/HOLD")
    reasoning: str = Field(description="建议理由")
    confidence: float = Field(description="置信度 0-1")
    risk_level: str = Field(description="风险等级: LOW/MEDIUM/HIGH")


# 定义状态
class AnalysisState(TypedDict):
    """分析流水线状态"""
    news_id: int
    title: str
    content: str
    
    # 各阶段结果
    has_investment_value: bool
    investment_reasoning: str
    investment_confidence: float
    
    tokens: List[str]
    token_reasoning: str
    
    rag_context: str
    
    trend_analyses: List[Dict]
    
    recommendation: str
    recommendation_reasoning: str
    recommendation_confidence: float
    risk_level: str
    
    # 流水线控制
    should_continue: bool
    error: str
    
    # 步骤记录
    steps: List[Dict]


class AnalysisPipeline:
    """投资分析流水线"""
    
    def __init__(self, rag_service=None, market_service=None, graph_rag_service=None):
        # 确保 LangSmith 追踪在 Pipeline 中也启用
        import os
        os.environ["LANGCHAIN_TRACING_V2"] = str(getattr(settings, 'LANGCHAIN_TRACING_V2', 'true')).lower()
        if hasattr(settings, 'LANGCHAIN_API_KEY'):
            os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
        if hasattr(settings, 'LANGCHAIN_PROJECT'):
            os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
        
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.0,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE
        )
        self.rag_service = rag_service
        self.market_service = market_service
        self.graph_rag_service = graph_rag_service  # 知识图谱服务
        
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        
        """构建分析流水线图"""
        workflow = StateGraph(AnalysisState)
        
        # 添加节点
        workflow.add_node("judge_investment_value", self.judge_investment_value)
        workflow.add_node("extract_tokens", self.extract_tokens)
        workflow.add_node("rag_enhance", self.rag_enhance)
        workflow.add_node("analyze_trends", self.analyze_trends)
        workflow.add_node("generate_recommendation", self.generate_recommendation)
        
        # 设置入口
        from langgraph.graph.state import START
        workflow.add_edge(START, "judge_investment_value")
        
        # 添加边
        workflow.add_conditional_edges(
            "judge_investment_value",
            self._should_continue_after_judgment,
            {
                "continue": "extract_tokens",
                "end": END
            }
        )
        workflow.add_edge("extract_tokens", "rag_enhance")
        workflow.add_edge("rag_enhance", "analyze_trends")
        workflow.add_edge("analyze_trends", "generate_recommendation")
        workflow.add_edge("generate_recommendation", END)
        
        return workflow.compile()
    
    def judge_investment_value(self, state: AnalysisState) -> AnalysisState:
        """步骤 1: 判断投资价值"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的 Web3 投资分析师。
分析给定的快讯，判断是否具有投资价值。

投资价值的判断标准：
1. 是否涉及代币价格变动、项目融资、技术突破等
2. 是否对市场有实质性影响
3. 是否包含可操作的投资信息

请以 JSON 格式返回，格式如下：
{{
  "has_value": true,
  "reasoning": "判断理由",
  "confidence": 0.8
}}

重要：只返回 JSON，不要添加任何其他文字。"""),
            ("user", "标题: {title}\n\n内容: {content}")
        ])
        
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "title": state["title"],
                "content": state["content"]
            })
            
            # 手动解析 JSON
            import json
            content = response.content if hasattr(response, 'content') else str(response)
            
            # 提取 JSON（可能包含在 markdown 代码块中）
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接提取 JSON 对象
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise ValueError(f"No JSON found in response: {content}")
            
            data = json.loads(json_str)
            result = InvestmentValue(**data)
            
            # result 是 InvestmentValue 对象
            state["has_investment_value"] = result.has_value
            state["investment_reasoning"] = result.reasoning
            state["investment_confidence"] = result.confidence
            state["should_continue"] = result.has_value
            
            state["steps"].append({
                "step": "judge_investment_value",
                "result": result.model_dump(),
                "status": "success"
            })
        except Exception as e:
            import traceback
            print(f"Investment value judgment error: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            # 默认值：假设有投资价值以继续流程
            state["has_investment_value"] = True
            state["investment_reasoning"] = "自动判断：快讯包含市场相关信息"
            state["investment_confidence"] = 0.5
            state["should_continue"] = True
            state["error"] = f"Investment value judgment failed: {str(e)}"
            state["steps"].append({
                "step": "judge_investment_value",
                "error": str(e),
                "status": "failed_with_fallback"
            })
        
        return state
    
    def extract_tokens(self, state: AnalysisState) -> AnalysisState:
        """步骤 2: 提取代币"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是 Web3 代币识别专家。
从快讯中提取所有相关的代币符号（如 BTC, ETH, USDT 等）。

请以 JSON 格式返回，格式如下：
{{
  "tokens": ["BTC", "ETH"],
  "reasoning": "提取理由"
}}

重要：只返回 JSON，不要添加任何其他文字。"""),
            ("user", "标题: {title}\n\n内容: {content}")
        ])
        
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "title": state["title"],
                "content": state["content"]
            })
            
            # 手动解析 JSON
            import json
            content = response.content if hasattr(response, 'content') else str(response)
            
            # 提取 JSON
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise ValueError(f"No JSON found in response: {content}")
            
            data = json.loads(json_str)
            result = TokenExtraction(**data)
            
            # result 是 TokenExtraction 对象
            state["tokens"] = result.tokens
            state["token_reasoning"] = result.reasoning
            
            state["steps"].append({
                "step": "extract_tokens",
                "result": result.model_dump(),
                "status": "success"
            })
        except Exception as e:
            import traceback
            print(f"Token extraction error: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            # Fallback: 中文名称映射 + $TOKEN 正则 + 扩展关键词匹配
            cn_to_symbol = {
                "比特币": "BTC", "以太坊": "ETH", "以太": "ETH", "泰达币": "USDT",
                "币安币": "BNB", "索拉纳": "SOL", "卡尔达诺": "ADA", "瑞波币": "XRP",
                "波卡": "DOT", "狗狗币": "DOGE", "马蹄": "MATIC", "莱特币": "LTC",
                "链接": "LINK", "波场": "TRX", "阿瓦雪": "AVAX", "宇宙": "ATOM",
                "近协议": "NEAR", "算法稳定币": "ALGO", "恒星币": "XLM", "艾达币": "ADA",
            }
            common_tokens = [
                "BTC", "ETH", "USDT", "BNB", "SOL", "ADA", "XRP", "DOT", "DOGE",
                "MATIC", "LTC", "LINK", "TRX", "AVAX", "ATOM", "NEAR", "ALGO",
                "XLM", "VET", "FIL", "ICP", "ETC", "HBAR", "SAND", "MANA",
                "AXS", "THETA", "FTM", "ONE", "EGLD", "FLOW", "CHZ", "ENJ",
                "AAVE", "UNI", "SUSHI", "CRV", "MKR", "COMP", "SNX", "YFI",
                "OP", "ARB", "APT", "SUI", "SEI", "TON", "PEPE", "SHIB",
            ]
            text = f"{state['title']} {state['content']}"
            text_upper = text.upper()
            found_tokens = []

            # 1. 中文名称映射
            for cn_name, symbol in cn_to_symbol.items():
                if cn_name in text and symbol not in found_tokens:
                    found_tokens.append(symbol)

            # 2. $TOKEN 格式（如 $BTC、$ETH）
            dollar_tokens = re.findall(r'\$([A-Z]{2,10})\b', text_upper)
            for t in dollar_tokens:
                if t not in found_tokens:
                    found_tokens.append(t)

            # 3. 已知代币符号关键词匹配
            for token in common_tokens:
                if token not in found_tokens and re.search(rf'\b{token}\b', text_upper):
                    found_tokens.append(token)
            
            state["tokens"] = found_tokens[:5]  # 最多5个
            state["token_reasoning"] = "通过关键词匹配提取"
            state["error"] = f"Token extraction failed: {str(e)}"
            state["steps"].append({
                "step": "extract_tokens",
                "error": str(e),
                "status": "failed_with_fallback"
            })
        
        return state
    
    def rag_enhance(self, state: AnalysisState) -> AnalysisState:
        """步骤 3: RAG 增强 + 市场数据补充"""
        context_parts = []
        docs = []  # 保证后续引用时始终有定义

        # 1. RAG 知识库检索（如果启用）
        if self.rag_service and settings.ENABLE_RAG and state.get("tokens"):
            try:
                # 构建查询
                query = f"{state['title']} {state['content']}"
                if state["tokens"]:
                    query += f" {' '.join(state['tokens'])}"
                
                # 检索相关文档
                docs = self.rag_service.search(query, k=5)
                
                if docs:
                    rag_context = "\n\n".join([doc["content"] for doc in docs])
                    rag_weight_pct = f"{settings.RAG_WEIGHT * 100:.1f}%"
                    context_parts.append(f"=== 知识库信息 (权重: {rag_weight_pct}) ===\n{rag_context}")
                    print(f"✓ RAG 知识库: 检索到 {len(docs)} 个相关文档")
                
            except Exception as e:
                print(f"RAG search failed: {e}")
        elif not settings.ENABLE_RAG:
            print("○ RAG 知识库未启用")
        
        # 2. 知识图谱增强（如果启用）
        if self.graph_rag_service and self.graph_rag_service.is_enabled() and state.get("tokens"):
            try:
                graph_contexts = []
                for token in state["tokens"][:5]:  # 限制最多 5 个代币
                    graph_context = self.graph_rag_service.get_token_context(token)
                    if graph_context:
                        graph_contexts.append(graph_context)
                
                if graph_contexts:
                    combined_graph_context = "\n\n".join(graph_contexts)
                    graph_weight_pct = f"{self.graph_rag_service.weight * 100:.1f}%"
                    context_parts.append(f"=== 知识图谱信息 (权重: {graph_weight_pct}) ===\n{combined_graph_context}")
                    print(f"✓ 知识图谱增强: 为 {len(graph_contexts)} 个代币添加了图谱上下文")
                
            except Exception as e:
                print(f"Knowledge graph enhancement failed: {e}")
        
        # 3. 实时市场数据获取
        if self.market_service and state.get("tokens"):
            try:
                market_info_list = []
                
                for token in state["tokens"][:5]:  # 限制最多 5 个代币
                    token_info = self.market_service.get_token_info(token)
                    if token_info:
                        formatted = self.market_service.format_token_info_for_llm(token_info)
                        market_info_list.append(formatted)
                
                if market_info_list:
                    market_context = "\n\n".join(market_info_list)
                    context_parts.append(f"=== 实时市场数据 ===\n{market_context}")
                
                state["steps"].append({
                    "step": "rag_enhance",
                    "result": {
                        "rag_enabled": settings.ENABLE_RAG,
                        "rag_docs_count": len(docs),
                        "graph_enabled": self.graph_rag_service.is_enabled() if self.graph_rag_service else False,
                        "market_tokens_count": len(market_info_list)
                    },
                    "status": "success"
                })
                
            except Exception as e:
                print(f"Market data fetch failed: {e}")
                state["steps"].append({
                    "step": "rag_enhance",
                    "error": str(e),
                    "status": "partial"
                })
        
        # 组合所有上下文
        state["rag_context"] = "\n\n".join(context_parts) if context_parts else ""
        
        if not context_parts:
            state["steps"].append({
                "step": "rag_enhance",
                "result": "No context available",
                "status": "skipped"
            })
        
        return state
    
    def analyze_trends(self, state: AnalysisState) -> AnalysisState:
        """步骤 4: 趋势分析"""
        if not state.get("tokens"):
            state["trend_analyses"] = []
            return state
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是 Web3 市场趋势分析师。
分析代币的涨跌趋势。

trend 只能是: BULLISH(看涨), BEARISH(看跌), NEUTRAL(中性)

请以 JSON 格式返回，格式如下：
{{
  "token": "ETH",
  "trend": "BULLISH",
  "reasoning": "分析理由",
  "confidence": 0.8
}}

重要：只返回 JSON，不要添加任何其他文字。"""),
            ("user", """快讯标题: {title}
快讯内容: {content}

代币: {token}

背景知识:
{rag_context}""")
        ])
        
        chain = prompt | self.llm
        
        trend_analyses = []
        for token in state["tokens"][:3]:  # 限制分析前 3 个代币
            try:
                response = chain.invoke({
                    "title": state["title"],
                    "content": state["content"],
                    "token": token,
                    "rag_context": state.get("rag_context", "")[:500]
                })
                
                # 手动解析 JSON
                import json
                content = response.content if hasattr(response, 'content') else str(response)
                
                # 提取 JSON
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                    else:
                        raise ValueError(f"No JSON found in response: {content}")
                
                data = json.loads(json_str)
                result = TrendAnalysis(**data)
                
                # result 是 TrendAnalysis 对象
                trend_analyses.append(result.model_dump())
                
            except Exception as e:
                import traceback
                print(f"Trend analysis failed for {token}: {e}")
                print(f"Traceback: {traceback.format_exc()}")
                # Fallback: 基于快讯内容的简单判断
                content_lower = f"{state['title']} {state['content']}".lower()
                if any(word in content_lower for word in ['上涨', '突破', '新高', '看涨', 'bullish', 'surge']):
                    trend = "BULLISH"
                elif any(word in content_lower for word in ['下跌', '暴跌', '看跌', 'bearish', 'crash', 'dump']):
                    trend = "BEARISH"
                else:
                    trend = "NEUTRAL"
                
                trend_analyses.append({
                    "token": token,
                    "trend": trend,
                    "reasoning": f"基于关键词分析：{trend}",
                    "confidence": 0.6
                })
        
        state["trend_analyses"] = trend_analyses
        state["steps"].append({
            "step": "analyze_trends",
            "result": {"analyses_count": len(trend_analyses)},
            "status": "success"
        })
        
        return state
    
    def generate_recommendation(self, state: AnalysisState) -> AnalysisState:
        """步骤 5: 生成投资建议"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是专业投资顾问。
基于分析结果给出投资建议。

recommendation 只能是: BUY(买入), SELL(卖出), HOLD(持有)
risk_level 只能是: LOW(低风险), MEDIUM(中等风险), HIGH(高风险)

请以 JSON 格式返回，格式如下：
{{
  "recommendation": "HOLD",
  "reasoning": "建议理由",
  "confidence": 0.6,
  "risk_level": "MEDIUM"
}}

重要：只返回 JSON，不要添加任何其他文字。"""),
            ("user", """快讯: {title}

投资价值判断: {investment_reasoning}

提取的代币: {tokens}

趋势分析结果: {trend_analyses}

背景知识: {rag_context}""")
        ])
        
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "title": state["title"],
                "investment_reasoning": state.get("investment_reasoning", ""),
                "tokens": ", ".join(state.get("tokens", [])),
                "trend_analyses": str(state.get("trend_analyses", []))[:500],
                "rag_context": state.get("rag_context", "")[:500]
            })
            
            # 手动解析 JSON
            import json
            content = response.content if hasattr(response, 'content') else str(response)
            
            # 提取 JSON
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise ValueError(f"No JSON found in response: {content}")
            
            data = json.loads(json_str)
            result = InvestmentRecommendation(**data)
            
            # result 是 InvestmentRecommendation 对象
            state["recommendation"] = result.recommendation
            state["recommendation_reasoning"] = result.reasoning
            state["recommendation_confidence"] = result.confidence
            state["risk_level"] = result.risk_level
            
            state["steps"].append({
                "step": "generate_recommendation",
                "result": result.model_dump(),
                "status": "success"
            })
        except Exception as e:
            import traceback
            print(f"Recommendation generation error: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            # Fallback: 基于趋势分析的简单逻辑
            trend_analyses = state.get("trend_analyses", [])
            
            if trend_analyses:
                bullish_count = sum(1 for t in trend_analyses if t.get("trend") == "BULLISH")
                bearish_count = sum(1 for t in trend_analyses if t.get("trend") == "BEARISH")
                
                if bullish_count > bearish_count:
                    recommendation = "BUY"
                    reasoning = f"多数代币({bullish_count}/{len(trend_analyses)})呈看涨趋势"
                    risk_level = "MEDIUM"
                elif bearish_count > bullish_count:
                    recommendation = "SELL"
                    reasoning = f"多数代币({bearish_count}/{len(trend_analyses)})呈看跌趋势"
                    risk_level = "MEDIUM"
                else:
                    recommendation = "HOLD"
                    reasoning = "趋势不明确，建议观望"
                    risk_level = "LOW"
            else:
                recommendation = "HOLD"
                reasoning = "缺乏足够信息，建议观望"
                risk_level = "LOW"
            
            state["recommendation"] = recommendation
            state["recommendation_reasoning"] = reasoning
            state["recommendation_confidence"] = 0.6
            state["risk_level"] = risk_level
            state["error"] = f"Recommendation generation failed: {str(e)}"
            state["steps"].append({
                "step": "generate_recommendation",
                "error": str(e),
                "status": "failed_with_fallback"
            })
        
        return state
    
    def _should_continue_after_judgment(self, state: AnalysisState) -> str:
        """判断是否继续分析"""
        return "continue" if state.get("should_continue", False) else "end"
    
    def run(self, news_id: int, title: str, content: str) -> Dict:
        """运行分析流水线"""
        initial_state = {
            "news_id": news_id,
            "title": title,
            "content": content,
            "steps": [],
            "should_continue": True,
            "error": ""
        }
        
        result = self.graph.invoke(initial_state)
        return result
