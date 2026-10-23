from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Generic, TypeVar

T = TypeVar("T")

from models.conversation import ConversationType
from models.message import MessageRole

class PageResponse(BaseModel, Generic[T]):
    ### 通用分页响应
    items: list[T]
    total: int
    page: int
    page_size: int

class ConversationCreate(BaseModel):
    # 会话标题（工作台输入框发送时通常把问题作为标题）
    title: str
    # 会话类型，默认 chat
    type: ConversationType = ConversationType.CHAT

class ConversationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    type: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class MessageCreate(BaseModel):
    # 消息内容
    content: str
    # 携带的文件 id 列表（可选），三种会话类型都可携带
    file_ids: list[int] | None = None

class MessageFile(BaseModel):
    """消息关联的附件文件信息（前端历史消息附件展示用）"""

    id: int
    name: str
    size: int

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role:MessageRole
    content: str
    created_at: datetime
    # 关联的附件文件列表（含文件名/大小，前端加载历史时展示附件 chip）
    files: list[MessageFile] = []
    # Agent 工具执行结果（刷新页面后恢复图表/数据）
    tool_results: list | None = None

    model_config = ConfigDict(from_attributes=True)