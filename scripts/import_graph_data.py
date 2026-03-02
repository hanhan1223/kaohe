"""导入知识图谱数据"""
import sys
sys.path.append('.')

from app.services.graph.neo4j_service import Neo4jService
import json


def import_from_json(json_file: str):
    """从 JSON 文件导入图数据"""
    service = Neo4jService()
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 导入公链
        for blockchain in data.get('blockchains', []):
            service.create_blockchain(
                blockchain['name'],
                blockchain.get('properties', {})
            )
            print(f"Created blockchain: {blockchain['name']}")
        
        # 导入项目
        for project in data.get('projects', []):
            service.create_project(
                project['name'],
                project.get('properties', {})
            )
            print(f"Created project: {project['name']}")
        
        # 导入代币
        for token in data.get('tokens', []):
            service.create_token(
                token['symbol'],
                token['name'],
                token.get('properties', {})
            )
            print(f"Created token: {token['symbol']}")
        
        # 导入投资机构
        for institution in data.get('institutions', []):
            service.create_institution(
                institution['name'],
                institution.get('properties', {})
            )
            print(f"Created institution: {institution['name']}")
        
        # 导入人物
        for person in data.get('persons', []):
            service.create_person(
                person['name'],
                person.get('properties', {})
            )
            print(f"Created person: {person['name']}")
        
        # 创建关系
        for rel in data.get('relationships', []):
            rel_type = rel['type']
            
            if rel_type == 'ISSUES':
                service.create_issues_relationship(
                    rel['project'],
                    rel['token']
                )
            elif rel_type == 'INVESTS':
                service.create_invests_relationship(
                    rel['institution'],
                    rel['project'],
                    rel.get('amount'),
                    rel.get('round')
                )
            elif rel_type == 'FOUNDED_BY':
                service.create_founded_by_relationship(
                    rel['project'],
                    rel['person']
                )
            elif rel_type == 'BUILT_ON':
                service.create_built_on_relationship(
                    rel['project'],
                    rel['blockchain']
                )
            
            print(f"Created relationship: {rel_type}")
        
        print(f"\n✓ Successfully imported graph data from {json_file}")
        
    except Exception as e:
        print(f"✗ Error importing graph data: {e}")
    finally:
        service.close()


def import_sample_data():
    """导入示例数据"""
    service = Neo4jService()
    
    try:
        print("Importing sample Web3 knowledge graph...")
        
        # 公链
        service.create_blockchain("Ethereum", {"type": "Layer1", "symbol": "ETH"})
        service.create_blockchain("Solana", {"type": "Layer1", "symbol": "SOL"})
        service.create_blockchain("Arbitrum", {"type": "Layer2", "parent": "Ethereum"})
        service.create_blockchain("Optimism", {"type": "Layer2", "parent": "Ethereum"})
        
        # 项目
        service.create_project("Uniswap", {"category": "DEX", "tvl": "5B"})
        service.create_project("Aave", {"category": "Lending", "tvl": "10B"})
        service.create_project("Compound", {"category": "Lending", "tvl": "3B"})
        service.create_project("MakerDAO", {"category": "Stablecoin", "tvl": "8B"})
        
        # 代币
        service.create_token("UNI", "Uniswap", {"type": "Governance", "supply": "1B"})
        service.create_token("AAVE", "Aave", {"type": "Governance", "supply": "16M"})
        service.create_token("COMP", "Compound", {"type": "Governance", "supply": "10M"})
        service.create_token("MKR", "MakerDAO", {"type": "Governance", "supply": "1M"})
        service.create_token("DAI", "MakerDAO", {"type": "Stablecoin", "supply": "5B"})
        
        # 投资机构
        service.create_institution("a16z", {"type": "VC", "aum": "35B"})
        service.create_institution("Paradigm", {"type": "VC", "aum": "13B"})
        service.create_institution("Coinbase Ventures", {"type": "VC", "aum": "1B"})
        service.create_institution("Binance Labs", {"type": "VC", "aum": "7.5B"})
        
        # 人物
        service.create_person("Hayden Adams", {"role": "Founder", "twitter": "@haydenzadams"})
        service.create_person("Stani Kulechov", {"role": "Founder", "twitter": "@StaniKulechov"})
        service.create_person("Robert Leshner", {"role": "Founder", "twitter": "@rleshner"})
        service.create_person("Rune Christensen", {"role": "Founder", "twitter": "@RuneKek"})
        
        # 创建关系
        # 项目发行代币
        service.create_issues_relationship("Uniswap", "UNI")
        service.create_issues_relationship("Aave", "AAVE")
        service.create_issues_relationship("Compound", "COMP")
        service.create_issues_relationship("MakerDAO", "MKR")
        service.create_issues_relationship("MakerDAO", "DAI")
        
        # 投资关系
        service.create_invests_relationship("a16z", "Uniswap", 11000000, "Series A")
        service.create_invests_relationship("Paradigm", "Uniswap", 11000000, "Series A")
        service.create_invests_relationship("a16z", "Compound", 25000000, "Series A")
        service.create_invests_relationship("Coinbase Ventures", "Compound", 8200000, "Seed")
        service.create_invests_relationship("a16z", "MakerDAO", 15000000, "Series A")
        
        # 创始人关系
        service.create_founded_by_relationship("Uniswap", "Hayden Adams")
        service.create_founded_by_relationship("Aave", "Stani Kulechov")
        service.create_founded_by_relationship("Compound", "Robert Leshner")
        service.create_founded_by_relationship("MakerDAO", "Rune Christensen")
        
        # 构建在公链上
        service.create_built_on_relationship("Uniswap", "Ethereum")
        service.create_built_on_relationship("Uniswap", "Arbitrum")
        service.create_built_on_relationship("Uniswap", "Optimism")
        service.create_built_on_relationship("Aave", "Ethereum")
        service.create_built_on_relationship("Compound", "Ethereum")
        service.create_built_on_relationship("MakerDAO", "Ethereum")
        
        print("\n✓ Sample knowledge graph imported successfully!")
        print("\nYou can now query the graph:")
        print("  - Find project info: service.find_project_info('Uniswap')")
        print("  - Find token projects: service.find_token_projects('UNI')")
        print("  - Find institution portfolio: service.find_institution_portfolio('a16z')")
        
    except Exception as e:
        print(f"✗ Error importing sample data: {e}")
    finally:
        service.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Import knowledge graph data")
    parser.add_argument("--file", type=str, help="JSON file to import")
    parser.add_argument("--sample", action="store_true", help="Import sample data")
    
    args = parser.parse_args()
    
    if args.file:
        import_from_json(args.file)
    elif args.sample:
        import_sample_data()
    else:
        print("Please specify --file or --sample")
        print("Usage:")
        print("  python scripts/import_graph_data.py --sample")
        print("  python scripts/import_graph_data.py --file data/graph_data.json")
