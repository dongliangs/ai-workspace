from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class KnowledgeBaseStatus(str, Enum):
    """知识库状态"""
    ACTIVE = "active"        # 正常使用
    DELETING = "deleting"    # 正在删除（级联清理中）


class KnowledgeBase(Base):
    """知识库表"""

    __tablename__ = "knowledge_base"

    # 知识库 ID
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="知识库ID",
    )
    # 所属用户
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="所属用户ID",
    )
    # 知识库名称
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="知识库名称",
    )
    # 描述（可选）
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="知识库描述",
    )
    # 状态
    status: Mapped[KnowledgeBaseStatus] = mapped_column(
        SQLEnum(KnowledgeBaseStatus),
        nullable=False,
        default=KnowledgeBaseStatus.ACTIVE,
        comment="知识库状态",
    )
    # 绑定的会话 ID（可选，知识库问答会话关联）
    conversation_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("conversation.id"),
        nullable=True,
        index=True,
        comment="绑定的会话ID",
    )
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="创建时间",
    )
    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="更新时间",
    )
