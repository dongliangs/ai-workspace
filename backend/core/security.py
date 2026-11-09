import base64
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.session import get_db
from models.user import User


# RSA 私钥不再由进程随机生成，而是由所有 worker 从同一个密钥文件加载。
# 模块导入时只声明状态，真正的加载和校验放在应用 lifespan 启动阶段。
_rsa_private_key: rsa.RSAPrivateKey | None = None
_rsa_public_key_pem: str | None = None


def load_rsa_private_key(
    key_path: str | Path,
    password: str | None = None,
) -> rsa.RSAPrivateKey:
    """读取 PEM 私钥并校验类型和最小长度。"""
    path = Path(key_path)
    if not path.is_file():
        raise RuntimeError(f"RSA private key file not found: {path}")

    try:
        private_key = serialization.load_pem_private_key(
            path.read_bytes(),
            password=password.encode("utf-8") if password else None,
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Unable to load RSA private key") from exc

    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise RuntimeError("Configured RSA key is not a private RSA key")
    if private_key.key_size < 2048:
        raise RuntimeError("RSA private key must be at least 2048 bits")
    return private_key


def initialize_rsa_keys() -> None:
    """在应用启动时加载固定私钥，并派生供前端使用的公钥。"""
    global _rsa_private_key, _rsa_public_key_pem

    password = (
        settings.rsa_private_key_password.get_secret_value()
        if settings.rsa_private_key_password is not None
        else None
    )
    private_key = load_rsa_private_key(
        settings.rsa_private_key_path,
        password=password,
    )

    _rsa_private_key = private_key
    _rsa_public_key_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def _require_private_key() -> rsa.RSAPrivateKey:
    if _rsa_private_key is None:
        raise RuntimeError("RSA keys are not initialized")
    return _rsa_private_key

#创建密码哈希工具
password_hash = PasswordHash.recommended()

# 获取公钥 PEM 字符串，供 /auth/public-key 接口返回给前端
def get_public_key_pem() -> str:
    """返回当前 RSA 公钥的 PEM 字符串（SPKI 格式）。"""
    if _rsa_public_key_pem is None:
        raise RuntimeError("RSA keys are not initialized")
    return _rsa_public_key_pem

# 解密
def decrypt_password(encrypted_password: str) -> str:
    """用 RSA 私钥解密前端公钥加密的密码，返回明文密码。"""
    try:
        ciphertext = base64.b64decode(encrypted_password, validate=True)
        plaintext = _require_private_key().decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return plaintext.decode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("密码密文格式无效") from exc

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
