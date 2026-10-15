from datetime import datetime
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    """文档响应"""
    id: int
    knowledge_base_id: int
    file_id: int
    filename: str
    file_type: str
    status: str
    chunk_count: int
    error_message: str | None = None
    created_at: datetime
    indexed_at: datetime | None = None

    model_config = {"from_attributes": True}


class KnowledgeChatRequest(BaseModel):
    """知识库问答请求"""
    question: str
    conversation_id: int | None = None
