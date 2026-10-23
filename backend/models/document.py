from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.file import File


class DocumentStatus(str, Enum):
    """文档索引状态"""
    PENDING = "pending"        # 已上传，待处理
    PROCESSING = "processing" # 正在解析/向量化
    INDEXED = "indexed"        # 索引完成，可检索
    FAILED = "failed"          # 处理失败


class KnowledgeDocument(Base):
    """知识库文档表 —— 记录用户上传到知识库的文件及索引状态"""

    __tablename__ = "knowledge_document"

    # 文档 ID
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="文档ID",
    )
    # 所属知识库
    knowledge_base_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("knowledge_base.id"),
        nullable=False,
        index=True,
        comment="所属知识库ID",
    )
    # 所属用户（便于权限过滤）
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="所属用户ID",
    )
    # 关联现有 File 记录
    file_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("file.id"),
        nullable=False,
        comment="关联文件ID",
    )
    # 原始文件名快照
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="原始文件名",
    )
    # 文件类型
    file_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="文件类型: pdf/docx/txt",
    )
    # 索引状态
    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus),
        nullable=False,
        default=DocumentStatus.PENDING,
        comment="索引状态",
    )
    # 分块数量
    chunk_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="分块数量",
    )
    # 失败原因
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="处理失败原因",
    )
    # 上传时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="上传时间",
    )
    # 索引完成时间
    indexed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="索引完成时间",
    )
    # 关联文件记录（joined 预加载：异步会话下避免懒加载报错）
    file: Mapped[File] = relationship(File, lazy="joined")

    @property
    def size(self) -> int:
        """文件大小（字节），取自关联 File 记录"""
        return self.file.file_size
