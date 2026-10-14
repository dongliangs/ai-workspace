from datetime import datetime
from enum import Enum

from pydantic.color import Color
from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


#消息角色

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Message(Base):

    __tablename__ = "message"

    #消息ID
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="消息ID"
    )

    #所属会话 ID
    conversation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("conversation.id"),
        nullable=False,
        index=True,
        comment="会话ID"
    )

    #消息角色
    role: Mapped[MessageRole] = mapped_column(
        SQLEnum(MessageRole),
        nullable=False,
        comment="消息角色"
    )

    #消息内容
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="消息内容"
    )

    #工具执行结果（Agent 模式下持久化 tool_result 事件，刷新页面不丢失）
    tool_results: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        comment="工具执行结果（JSON 数组，每项含 tool/status/result）"
    )

    #创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="创建时间"
    )

    # 反向关联
    conversation = relationship(
        "Conversation",
        back_populates="messages"
    )