"""Neo4j 知识图谱服务"""
from typing import List, Dict, Optional
from neo4j import GraphDatabase
from app.core.config import settings


class Neo4jService:
    """Neo4j 知识图谱服务"""
    
    def __init__(self):
        if not settings.NEO4J_URI:
            raise ValueError("Neo4j URI not configured")
        
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
    
    def close(self):
        """关闭连接"""
        self.driver.close()
    
    def create_project(self, name: str, properties: Dict = None) -> int:
        """创建项目节点"""
        with self.driver.session() as session:
            result = session.run(
                """
                CREATE (p:Project {name: $name})
                SET p += $properties
                RETURN id(p) as id
                """,
                name=name,
                properties=properties or {}
            )
            return result.single()["id"]
    
    def create_token(self, symbol: str, name: str, properties: Dict = None) -> int:
        """创建代币节点"""
        with self.driver.session() as session:
            result = session.run(
                """
                MERGE (t:Token {symbol: $symbol})
                SET t.name = $name
                SET t += $properties
                RETURN id(t) as id
                """,
                symbol=symbol,
                name=name,
                properties=properties or {}
            )
            return result.single()["id"]
    
    def create_person(self, name: str, properties: Dict = None) -> int:
        """创建人物节点"""
        with self.driver.session() as session:
            result = session.run(
                """
                CREATE (p:Person {name: $name})
                SET p += $properties
                RETURN id(p) as id
                """,
                name=name,
                properties=properties or {}
            )
            return result.single()["id"]
    
    def create_institution(self, name: str, properties: Dict = None) -> int:
        """创建投资机构节点"""
        with self.driver.session() as session:
            result = session.run(
                """
                CREATE (i:Institution {name: $name})
                SET i += $properties
                RETURN id(i) as id
                """,
                name=name,
                properties=properties or {}
            )
            return result.single()["id"]
    
    def create_blockchain(self, name: str, properties: Dict = None) -> int:
        """创建公链节点"""
        with self.driver.session() as session:
            result = session.run(
                """
                CREATE (b:Blockchain {name: $name})
                SET b += $properties
                RETURN id(b) as id
                """,
                name=name,
                properties=properties or {}
            )
            return result.single()["id"]
    
    def create_issues_relationship(self, project_name: str, token_symbol: str):
        """创建项目发行代币关系"""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (p:Project {name: $project_name})
                MATCH (t:Token {symbol: $token_symbol})
                MERGE (p)-[:ISSUES]->(t)
                """,
                project_name=project_name,
                token_symbol=token_symbol
            )
    
    def create_invests_relationship(
        self,
        institution_name: str,
        project_name: str,
        amount: float = None,
        round: str = None
    ):
        """创建投资关系"""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (i:Institution {name: $institution_name})
                MATCH (p:Project {name: $project_name})
                MERGE (i)-[r:INVESTS]->(p)
                SET r.amount = $amount, r.round = $round
                """,
                institution_name=institution_name,
                project_name=project_name,
                amount=amount,
                round=round
            )
    
    def create_founded_by_relationship(self, project_name: str, person_name: str):
        """创建创始人关系"""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (p:Project {name: $project_name})
                MATCH (person:Person {name: $person_name})
                MERGE (p)-[:FOUNDED_BY]->(person)
                """,
                project_name=project_name,
                person_name=person_name
            )
    
    def create_built_on_relationship(self, project_name: str, blockchain_name: str):
        """创建构建在公链上的关系"""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (p:Project {name: $project_name})
                MATCH (b:Blockchain {name: $blockchain_name})
                MERGE (p)-[:BUILT_ON]->(b)
                """,
                project_name=project_name,
                blockchain_name=blockchain_name
            )
    
    def find_project_info(self, project_name: str) -> Optional[Dict]:
        """查询项目信息"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:Project {name: $project_name})
                OPTIONAL MATCH (p)-[:ISSUES]->(t:Token)
                OPTIONAL MATCH (i:Institution)-[inv:INVESTS]->(p)
                OPTIONAL MATCH (p)-[:FOUNDED_BY]->(person:Person)
                OPTIONAL MATCH (p)-[:BUILT_ON]->(b:Blockchain)
                RETURN p, 
                       collect(DISTINCT t.symbol) as tokens,
                       collect(DISTINCT {name: i.name, amount: inv.amount, round: inv.round}) as investors,
                       collect(DISTINCT person.name) as founders,
                       collect(DISTINCT b.name) as blockchains
                """,
                project_name=project_name
            )
            
            record = result.single()
            if not record:
                return None
            
            return {
                "project": dict(record["p"]),
                "tokens": record["tokens"],
                "investors": record["investors"],
                "founders": record["founders"],
                "blockchains": record["blockchains"]
            }
    
    def find_token_projects(self, token_symbol: str) -> List[Dict]:
        """查询代币相关项目"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:Project)-[:ISSUES]->(t:Token {symbol: $token_symbol})
                RETURN p.name as project_name, p
                """,
                token_symbol=token_symbol
            )
            
            return [dict(record["p"]) for record in result]
    
    def find_institution_portfolio(self, institution_name: str) -> List[Dict]:
        """查询投资机构的投资组合"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (i:Institution {name: $institution_name})-[inv:INVESTS]->(p:Project)
                OPTIONAL MATCH (p)-[:ISSUES]->(t:Token)
                RETURN p.name as project_name, 
                       inv.amount as amount, 
                       inv.round as round,
                       collect(t.symbol) as tokens
                """,
                institution_name=institution_name
            )
            
            return [
                {
                    "project": record["project_name"],
                    "amount": record["amount"],
                    "round": record["round"],
                    "tokens": record["tokens"]
                }
                for record in result
            ]


def build_sample_graph():
    """构建示例知识图谱"""
    service = Neo4jService()
    
    try:
        # 创建公链
        service.create_blockchain("Ethereum", {"type": "Layer1"})
        service.create_blockchain("Polygon", {"type": "Layer2"})
        
        # 创建项目
        service.create_project("Uniswap", {"category": "DEX"})
        service.create_project("Aave", {"category": "Lending"})
        
        # 创建代币
        service.create_token("UNI", "Uniswap", {"type": "Governance"})
        service.create_token("AAVE", "Aave", {"type": "Governance"})
        
        # 创建投资机构
        service.create_institution("a16z", {"type": "VC"})
        service.create_institution("Paradigm", {"type": "VC"})
        
        # 创建人物
        service.create_person("Hayden Adams", {"role": "Founder"})
        service.create_person("Stani Kulechov", {"role": "Founder"})
        
        # 创建关系
        service.create_issues_relationship("Uniswap", "UNI")
        service.create_issues_relationship("Aave", "AAVE")
        
        service.create_invests_relationship("a16z", "Uniswap", 11000000, "Series A")
        service.create_invests_relationship("Paradigm", "Uniswap", 11000000, "Series A")
        
        service.create_founded_by_relationship("Uniswap", "Hayden Adams")
        service.create_founded_by_relationship("Aave", "Stani Kulechov")
        
        service.create_built_on_relationship("Uniswap", "Ethereum")
        service.create_built_on_relationship("Aave", "Ethereum")
        service.create_built_on_relationship("Aave", "Polygon")
        
        print("Sample knowledge graph built successfully!")
        
    finally:
        service.close()


if __name__ == "__main__":
    build_sample_graph()
