#DeclarativeBase 是SQLalchemy 2.x 推荐使用的声明式模型基类

#以后定义User、Task\ Workflow 等数据库模型
# 都会继承这个BAse
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass