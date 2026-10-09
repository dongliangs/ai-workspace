# 注册和登录的数据结构
from datetime import datetime
from pydantic import BaseModel,EmailStr
#注册接口接受的数据结构
#前端直接》
#post /api/auth/register
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str
    nickname: str | None = None
#登录接口接收的数据
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

#当前用户信息返回
#1.登录后返回 user
class UserResponse(BaseModel):
    id: int
    email: EmailStr
    nickname: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

#注册成功之后data返回的token
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# 登录成功后 data 里面的内容
class LoginData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# 公钥接口返回的数据结构
class PublicKeyResponse(BaseModel):
    public_key: str