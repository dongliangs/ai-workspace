from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)
from core.config import settings
from sqlalchemy.orm import sessionmaker


#创建异步数据库Engine .
engine = create_async_engine(
    settings.database_url,
    #开发阶段打开SQL日志
    echo=True,
)
#创建 session 工厂
## AsyncSessionLocal()
#
# → 创建一个 AsyncSession
#
# 以后每一个 API 请求，
# 都可以通过这个工厂创建自己的数据库 Session。
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

# FastAPi 的数据库依赖
async def get_db():
    #async with的好处是：
    #使用结束之后会自动关闭Session
    async with AsyncSessionLocal() as session:
        yield session