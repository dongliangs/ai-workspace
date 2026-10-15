from datetime import datetime
from pydantic import BaseModel


class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求"""
    name: str
    description: str | None = None


class KnowledgeBaseUpdate(BaseModel):
    """修改知识库请求"""
    name: str | None = None
    description: str | None = None


class KnowledgeBaseResponse(BaseModel):
    """知识库响应"""
    id: int
    user_id: int
    name: str
    description: str | None = None
    status: str
    conversation_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeBaseDetailResponse(KnowledgeBaseResponse):
    """知识库详情（含文档数量）"""
    document_count: int = 0
