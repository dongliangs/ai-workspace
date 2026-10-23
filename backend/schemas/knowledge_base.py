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
    doc_count: int
    # 可检索片段总数（实时聚合文档表 chunk_count，仅统计索引成功文档；表内不冗余存储）
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
