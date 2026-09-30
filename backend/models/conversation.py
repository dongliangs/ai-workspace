from datetime import datetime
from enum import Enum
from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, String

from sqlalchemy.orm import Mapped, mapped_column,relationship
from models.base import Base


#会话类型
class ConversationType(str,Enum):
    CHAT="chat",
    FILE="file",
    KNOWLEDGE="knowledge",
    AGENT="agent"

#创建ai 对话消息表
class Conversation(Base):
    # 指定数据库表名
    __tablename__ = 'conversation'

    # 会话id
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        # MySql自动递增
        autoincrement=True,
        comment="会话id"
    )
    # 用户id
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        autoincrement=True,
        comment="用户id"
    )
    #会话标题
    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="会话标题"
    )
    #会话类型
    type: Mapped[ConversationType] = mapped_column(
        SQLEnum(ConversationType),
        nullable=False,
        default=ConversationType.CHAT,
        comment="会话类型"
        # 四种类型 chat / file / knowledge / agent
    )
    #创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="创建时间"
    )
    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="更新时间"
    )

    #一个会话对应多条消息
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all,delete-orphan",
    )