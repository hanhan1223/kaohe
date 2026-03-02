"""
知识图谱增强服务
用于在分析流程中查询和使用知识图谱数据
"""
from typing import List, Dict, Optional
from app.services.graph.neo4j_service import Neo4jService
from app.core.config import settings


class GraphRAGService:
    """知识图谱增强检索服务"""
    
    def __init__(self):
        self.enabled = settings.ENABLE_KNOWLEDGE_GRAPH
        self.weight = settings.GRAPH_WEIGHT
        
        if self.enabled:
            try:
                self.neo4j_service = Neo4jService()
            except Exception as e:
                print(f"⚠ 知识图谱服务初始化失败: {e}")
                self.enabled = False
                self.neo4j_service = None
        else:
            self.neo4j_service = None
    
    def is_enabled(self) -> bool:
        """检查知识图谱是否启用"""
        return self.enabled and self.neo4j_service is not None
    
    def get_token_context(self, token_symbol: str) -> str:
        """
        获取代币相关的知识图谱上下文
        
        Args:
            token_symbol: 代币符号
            
        Returns:
            格式化的上下文文本
        """
        if not self.is_enabled():
            return ""
        
        try:
            # 查询代币相关的项目
            projects = self.neo4j_service.find_token_projects(token_symbol)
            
            if not projects:
                return ""
            
            context_parts = [f"## 知识图谱信息 - {token_symbol}\n"]
            
            for project in projects:
                project_name = project.get('name', 'Unknown')
                
                # 获取项目详细信息
                project_info = self.neo4j_service.find_project_info(project_name)
                
                if project_info:
                    context_parts.append(f"\n### 项目: {project_name}")
                    
                    # 项目基本信息
                    proj = project_info.get('project', {})
                    if proj.get('category'):
                        context_parts.append(f"- 类别: {proj['category']}")
                    
                    # 创始人信息
                    founders = project_info.get('founders', [])
                    if founders:
                        context_parts.append(f"- 创始人: {', '.join(founders)}")
                    
                    # 投资机构信息
                    investors = project_info.get('investors', [])
                    if investors:
                        investor_names = [inv['name'] for inv in investors if inv.get('name')]
                        if investor_names:
                            context_parts.append(f"- 投资机构: {', '.join(investor_names[:5])}")
                        
                        # 融资信息
                        funding_info = []
                        for inv in investors:
                            if inv.get('round') and inv.get('amount'):
                                funding_info.append(f"{inv['round']}: ${inv['amount']:,.0f}")
                        if funding_info:
                            context_parts.append(f"- 融资轮次: {', '.join(funding_info[:3])}")
                    
                    # 公链信息
                    blockchains = project_info.get('blockchains', [])
                    if blockchains:
                        context_parts.append(f"- 部署链: {', '.join(blockchains)}")
            
            return "\n".join(context_parts)
        
        except Exception as e:
            print(f"获取知识图谱上下文失败: {e}")
            return ""
    
    def get_project_context(self, project_name: str) -> str:
        """
        获取项目相关的知识图谱上下文
        
        Args:
            project_name: 项目名称
            
        Returns:
            格式化的上下文文本
        """
        if not self.is_enabled():
            return ""
        
        try:
            project_info = self.neo4j_service.find_project_info(project_name)
            
            if not project_info:
                return ""
            
            context_parts = [f"## 知识图谱信息 - {project_name}\n"]
            
            # 项目基本信息
            proj = project_info.get('project', {})
            if proj.get('category'):
                context_parts.append(f"- 类别: {proj['category']}")
            
            # 代币信息
            tokens = project_info.get('tokens', [])
            if tokens:
                context_parts.append(f"- 代币: {', '.join(tokens)}")
            
            # 创始人信息
            founders = project_info.get('founders', [])
            if founders:
                context_parts.append(f"- 创始人: {', '.join(founders)}")
            
            # 投资机构信息
            investors = project_info.get('investors', [])
            if investors:
                investor_names = [inv['name'] for inv in investors if inv.get('name')]
                if investor_names:
                    context_parts.append(f"- 投资机构: {', '.join(investor_names)}")
                
                # 融资信息
                funding_info = []
                for inv in investors:
                    if inv.get('round') and inv.get('amount'):
                        funding_info.append(f"{inv['round']}: ${inv['amount']:,.0f}")
                if funding_info:
                    context_parts.append(f"- 融资轮次: {', '.join(funding_info)}")
            
            # 公链信息
            blockchains = project_info.get('blockchains', [])
            if blockchains:
                context_parts.append(f"- 部署链: {', '.join(blockchains)}")
            
            return "\n".join(context_parts)
        
        except Exception as e:
            print(f"获取知识图谱上下文失败: {e}")
            return ""
    
    def get_investor_context(self, investor_name: str) -> str:
        """
        获取投资机构相关的知识图谱上下文
        
        Args:
            investor_name: 投资机构名称
            
        Returns:
            格式化的上下文文本
        """
        if not self.is_enabled():
            return ""
        
        try:
            portfolio = self.neo4j_service.find_institution_portfolio(investor_name)
            
            if not portfolio:
                return ""
            
            context_parts = [f"## 知识图谱信息 - {investor_name} 投资组合\n"]
            
            for item in portfolio[:10]:  # 限制显示前 10 个
                project = item.get('project', 'Unknown')
                context_parts.append(f"- {project}")
                
                if item.get('round'):
                    context_parts.append(f"  轮次: {item['round']}")
                if item.get('amount'):
                    context_parts.append(f"  金额: ${item['amount']:,.0f}")
                if item.get('tokens'):
                    context_parts.append(f"  代币: {', '.join(item['tokens'])}")
            
            return "\n".join(context_parts)
        
        except Exception as e:
            print(f"获取知识图谱上下文失败: {e}")
            return ""
    
    def enhance_context(self, tokens: List[str], base_context: str) -> str:
        """
        使用知识图谱增强上下文
        
        Args:
            tokens: 代币符号列表
            base_context: 基础上下文（来自 RAG）
            
        Returns:
            增强后的上下文
        """
        if not self.is_enabled():
            return base_context
        
        graph_contexts = []
        
        for token in tokens:
            graph_context = self.get_token_context(token)
            if graph_context:
                graph_contexts.append(graph_context)
        
        if not graph_contexts:
            return base_context
        
        # 合并上下文
        enhanced_context = base_context
        if graph_contexts:
            enhanced_context += "\n\n" + "\n\n".join(graph_contexts)
            enhanced_context += f"\n\n注意：以上知识图谱信息权重为 {self.weight:.1%}"
        
        return enhanced_context
    
    def close(self):
        """关闭连接"""
        if self.neo4j_service:
            self.neo4j_service.close()


# 测试函数
def test_graph_rag_service():
    """测试知识图谱增强服务"""
    service = GraphRAGService()
    
    print(f"知识图谱是否启用: {service.is_enabled()}")
    
    if service.is_enabled():
        # 测试获取代币上下文
        print("\n测试获取 UNI 代币上下文:")
        context = service.get_token_context("UNI")
        print(context)
        
        # 测试获取项目上下文
        print("\n测试获取 Uniswap 项目上下文:")
        context = service.get_project_context("Uniswap")
        print(context)
        
        # 测试增强上下文
        print("\n测试增强上下文:")
        base_context = "这是基础的 RAG 上下文..."
        enhanced = service.enhance_context(["UNI"], base_context)
        print(enhanced)
    
    service.close()


if __name__ == "__main__":
    test_graph_rag_service()
