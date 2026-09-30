from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String

from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base
#对应数据库中的users 表
class User(Base):
    #指定数据库表名
    __tablename__ = "users"
    # 用户ID
    #primary_key主键，
    id: Mapped[int] = mapped_column(
        primary_key=True,
        #MySql自动递增
        autoincrement=True
    )
    # 用户邮箱
    email: Mapped[str] = mapped_column(
        String(255),
        #一个邮箱只能注册一个账号
        unique=True,
        #给email建索引
        index=True,
        #不能为空
        nullable=False
    )
    # 用户密码
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    #昵称
    nickname: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )
    # 用户是否处于正常状态
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
