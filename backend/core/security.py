# datetime 计算JWT 什么时候过期
from datetime import datetime, timedelta, timezone


# 生成和解析JWT Token
import jwt
# from dns.dnssecalgs import algorithms

# 安全对用户密码进行哈希处理

from pwdlib import PasswordHash

# Depends 用于声明依赖
from fastapi import Depends, HTTPException, status

#HttpBearer 用于从请求头中获取
#Authorization: Bearer

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

#SQLAlchemy 异步 Session
from sqlalchemy.ext.asyncio import AsyncSession

#查询User

from sqlalchemy import select

# 数据库依赖
from db.session import get_db

# User 模型
from models.user import User
#获取项目配置。
from core.config import settings

#创建密码哈希工具
password_hash = PasswordHash.recommended()

#对用户密码进行哈希

def hash_password(password: str) -> str:
    return password_hash.hash(password)


#验证用户输入的密码是否正确

def verify_password(
    password: str,
    hashed_password: str
) -> bool:

    return password_hash.verify(
        password,
        hashed_password
    )

# 创建JWT Token
#user_id

def create_access_token(
    user_id: int
) -> str:

    #当前时间 +token有效时间
    #
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    #JWT payload
    #sub
    #subject, 表示这个token属于哪个用户

    #exp
    #expiration, 表示token 啥时候过期
    payload = {
        "sub": str(user_id),
        "exp": expire,
    }

    # 使用JWT SecretKey 对 Token 进行签名。

    #Hs256
    #JWT 使用签名算法
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm='HS256'
    )

# 获取Authorization Bearer Token

bearer_scheme = HTTPBearer()

#获取当前登录用户
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:

    """
    根据JWT Token 获取当前登录用户。
    """
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=["HS256"]
        )

        # 获取 user_id
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )

        user_id = int(user_id)

    except (jwt.InvalidTokenError, ValueError):
        # Token格式 错误， 签名错误，过期等情况
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或已过期的Token"
        )

    # 根据user_id 查询数据库
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )

    # 用户存在但是被禁用
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )

    return user
