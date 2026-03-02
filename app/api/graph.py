"""知识图谱管理 API 路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from app.services.graph.neo4j_service import Neo4jService

router = APIRouter(prefix="/api/v1/graph", tags=["Knowledge Graph"])


# ==================== 请求/响应模型 ====================

class CreateProjectRequest(BaseModel):
    """创建项目请求"""
    name: str = Field(..., description="项目名称")
    category: Optional[str] = Field(None, description="项目类别，如 DEX, Lending")
    website: Optional[str] = Field(None, description="官方网站")
    description: Optional[str] = Field(None, description="项目描述")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Uniswap",
                "category": "DEX",
                "website": "https://uniswap.org",
                "description": "去中心化交易所"
            }
        }


class CreateTokenRequest(BaseModel):
    """创建代币请求"""
    symbol: str = Field(..., description="代币符号")
    name: str = Field(..., description="代币名称")
    contract_address: Optional[str] = Field(None, description="合约地址")
    chain: Optional[str] = Field(None, description="所在链")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "UNI",
                "name": "Uniswap",
                "contract_address": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
                "chain": "Ethereum"
            }
        }


class CreatePersonRequest(BaseModel):
    """创建人物请求"""
    name: str = Field(..., description="姓名")
    role: Optional[str] = Field(None, description="角色，如 Founder, CEO")
    twitter: Optional[str] = Field(None, description="Twitter 账号")
    linkedin: Optional[str] = Field(None, description="LinkedIn 账号")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Hayden Adams",
                "role": "Founder",
                "twitter": "@haydenzadams"
            }
        }


class CreateInstitutionRequest(BaseModel):
    """创建投资机构请求"""
    name: str = Field(..., description="机构名称")
    type: Optional[str] = Field(None, description="机构类型，如 VC, Angel")
    website: Optional[str] = Field(None, description="官方网站")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "a16z",
                "type": "VC",
                "website": "https://a16z.com"
            }
        }


class CreateRelationshipRequest(BaseModel):
    """创建关系请求"""
    type: str = Field(..., description="关系类型")
    from_node: str = Field(..., description="起始节点名称")
    to_node: str = Field(..., description="目标节点名称")
    properties: Optional[Dict] = Field(None, description="关系属性")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "ISSUES",
                "from_node": "Uniswap",
                "to_node": "UNI",
                "properties": {}
            }
        }


class NodeResponse(BaseModel):
    """节点响应"""
    success: bool
    message: str
    node_id: Optional[int] = None


class RelationshipResponse(BaseModel):
    """关系响应"""
    success: bool
    message: str


# ==================== 节点管理接口 ====================

@router.post("/projects", response_model=NodeResponse)
async def create_project(request: CreateProjectRequest):
    """
    创建项目节点
    
    参数：
    - name: 项目名称（必填）
    - category: 项目类别
    - website: 官方网站
    - description: 项目描述
    """
    try:
        service = Neo4jService()
        
        properties = {}
        if request.category:
            properties['category'] = request.category
        if request.website:
            properties['website'] = request.website
        if request.description:
            properties['description'] = request.description
        
        node_id = service.create_project(request.name, properties)
        service.close()
        
        return NodeResponse(
            success=True,
            message=f"成功创建项目节点: {request.name}",
            node_id=node_id
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建项目失败: {str(e)}")


@router.post("/tokens", response_model=NodeResponse)
async def create_token(request: CreateTokenRequest):
    """
    创建代币节点
    
    参数：
    - symbol: 代币符号（必填）
    - name: 代币名称（必填）
    - contract_address: 合约地址
    - chain: 所在链
    """
    try:
        service = Neo4jService()
        
        properties = {}
        if request.contract_address:
            properties['contract_address'] = request.contract_address
        if request.chain:
            properties['chain'] = request.chain
        
        node_id = service.create_token(request.symbol, request.name, properties)
        service.close()
        
        return NodeResponse(
            success=True,
            message=f"成功创建代币节点: {request.symbol}",
            node_id=node_id
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建代币失败: {str(e)}")


@router.post("/persons", response_model=NodeResponse)
async def create_person(request: CreatePersonRequest):
    """
    创建人物节点
    
    参数：
    - name: 姓名（必填）
    - role: 角色
    - twitter: Twitter 账号
    - linkedin: LinkedIn 账号
    """
    try:
        service = Neo4jService()
        
        properties = {}
        if request.role:
            properties['role'] = request.role
        if request.twitter:
            properties['twitter'] = request.twitter
        if request.linkedin:
            properties['linkedin'] = request.linkedin
        
        node_id = service.create_person(request.name, properties)
        service.close()
        
        return NodeResponse(
            success=True,
            message=f"成功创建人物节点: {request.name}",
            node_id=node_id
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建人物失败: {str(e)}")


@router.post("/institutions", response_model=NodeResponse)
async def create_institution(request: CreateInstitutionRequest):
    """
    创建投资机构节点
    
    参数：
    - name: 机构名称（必填）
    - type: 机构类型
    - website: 官方网站
    """
    try:
        service = Neo4jService()
        
        properties = {}
        if request.type:
            properties['type'] = request.type
        if request.website:
            properties['website'] = request.website
        
        node_id = service.create_institution(request.name, properties)
        service.close()
        
        return NodeResponse(
            success=True,
            message=f"成功创建机构节点: {request.name}",
            node_id=node_id
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建机构失败: {str(e)}")


# ==================== 关系管理接口 ====================

@router.post("/relationships", response_model=RelationshipResponse)
async def create_relationship(request: CreateRelationshipRequest):
    """
    创建关系
    
    支持的关系类型：
    - ISSUES: 项目发行代币 (Project -> Token)
    - INVESTS_IN: 投资关系 (Institution -> Project)
    - FOUNDED_BY: 创始人关系 (Project -> Person)
    - WORKS_FOR: 工作关系 (Person -> Project)
    - BUILT_ON: 构建在公链上 (Project -> Blockchain)
    
    参数：
    - type: 关系类型（必填）
    - from_node: 起始节点名称（必填）
    - to_node: 目标节点名称（必填）
    - properties: 关系属性（可选）
    """
    try:
        service = Neo4jService()
        
        if request.type == "ISSUES":
            # 项目发行代币
            service.create_issues_relationship(request.from_node, request.to_node)
        
        elif request.type == "INVESTS_IN":
            # 投资关系
            amount = request.properties.get('amount') if request.properties else None
            round_type = request.properties.get('round') if request.properties else None
            service.create_invests_relationship(
                request.from_node,
                request.to_node,
                amount,
                round_type
            )
        
        elif request.type == "FOUNDED_BY":
            # 创始人关系
            service.create_founded_by_relationship(request.from_node, request.to_node)
        
        elif request.type == "BUILT_ON":
            # 构建在公链上
            service.create_built_on_relationship(request.from_node, request.to_node)
        
        else:
            service.close()
            raise HTTPException(
                status_code=400,
                detail=f"不支持的关系类型: {request.type}"
            )
        
        service.close()
        
        return RelationshipResponse(
            success=True,
            message=f"成功创建关系: {request.from_node} -{request.type}-> {request.to_node}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建关系失败: {str(e)}")


# ==================== 查询接口 ====================

@router.get("/projects/{project_name}")
async def get_project_info(project_name: str):
    """
    查询项目信息
    
    返回项目的完整信息，包括：
    - 项目基本信息
    - 发行的代币
    - 投资机构
    - 创始人
    - 部署的区块链
    """
    try:
        service = Neo4jService()
        info = service.find_project_info(project_name)
        service.close()
        
        if not info:
            raise HTTPException(status_code=404, detail=f"未找到项目: {project_name}")
        
        return {
            "success": True,
            "data": info
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/tokens/{token_symbol}/projects")
async def get_token_projects(token_symbol: str):
    """
    查询代币相关的项目
    
    返回发行该代币的项目列表
    """
    try:
        service = Neo4jService()
        projects = service.find_token_projects(token_symbol)
        service.close()
        
        return {
            "success": True,
            "data": projects,
            "count": len(projects)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/institutions/{institution_name}/portfolio")
async def get_institution_portfolio(institution_name: str):
    """
    查询投资机构的投资组合
    
    返回该机构投资的所有项目
    """
    try:
        service = Neo4jService()
        portfolio = service.find_institution_portfolio(institution_name)
        service.close()
        
        return {
            "success": True,
            "data": portfolio,
            "count": len(portfolio)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
