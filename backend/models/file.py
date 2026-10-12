from datetime import datetime
from enum import Enum

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class FileStatus(str, Enum):
    """文件状态"""

    READY = "ready"            # 上传完成，可用
    PROCESSING = "processing"  # 正在被 Agent 处理
    FAILED = "failed"          # 上传或处理失败


class File(Base):
    """文件表 —— 统一管理用户上传的文件，三种会话类型 (chat/agent/knowledge) 共用。"""

    __tablename__ = "file"

    # 文件 id
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="文件id",
    )
    # 上传用户 id
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="上传用户id",
    )
    # 所属会话 id（上传时可指定，也可在发送消息时关联）
    conversation_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("conversation.id"),
        nullable=True,
        index=True,
        comment="会话id",
    )
    # 关联消息 id（发送消息携带 file_ids 时回写）
    message_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("message.id"),
        nullable=True,
        index=True,
        comment="关联消息id",
    )
    # 存储文件名（UUID 生成，避免冲突）
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="存储文件名",
    )
    # 原始文件名
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="原始文件名",
    )
    # 文件实际存储路径
    storage_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="文件存储路径",
    )
    # 文件 MIME 类型
    file_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="文件MIME类型",
    )
    # 文件大小（字节）
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="文件大小(字节)",
    )
    # 文件状态
    status: Mapped[FileStatus] = mapped_column(
        SQLEnum(FileStatus),
        nullable=False,
        default=FileStatus.READY,
        comment="文件状态",
    )
    # 上传时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="上传时间",
    )
    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="更新时间",
    )
