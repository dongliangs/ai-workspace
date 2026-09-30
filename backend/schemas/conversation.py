from datetime import datetime
from pydantic import BaseModel, ConfigDict

from models.conversation import ConversationType
from models.message import MessageRole

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
    content: str

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role:MessageRole
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)