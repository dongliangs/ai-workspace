
#api 路由
from fastapi import APIRouter,Depends,HTTPException, status

from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db

from core.security import get_current_user
#User
from models.user import User

from schemas.common import ApiResponse

from schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    LoginData,
    UserResponse
)

from core.security import (
    create_access_token,
    hash_password,
    verify_password
)

#创建Auth 路由
router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)

# 用户注册

@router.post(
    "/register",
    response_model=ApiResponse[TokenResponse],
)
async def register(
    data: RegisterRequest,
    # 获取数据库Session
    db: AsyncSession = Depends(get_db),
):
    #检查两次密码是否一致
    if data.password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="两次输入的密码不一致",
        )
    #检查邮箱是否已经注册
    result = await db.execute(
        select(User).where(User.email == data.email)
    )

    #从查询结果中获取一个User.

    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已经注册",
        )
    #2.创建user
    #需要把密码
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        nickname=data.nickname,
    )

    # 把user 对象加入当前Session.
    # 告诉sqlalchemy 要新增一个user
    db.add(user)
    #3.提交到sql保存
    await db.commit()

    # 4.刷新User
    #refresh() 会重新从数据库获取这个User,这样就可以拿到数据库生成的id
    await db.refresh(user)

    #5.生成JWT

    access_token = create_access_token(user.id)

    #6.返回给前端

    return ApiResponse(
        code=0,
        data=TokenResponse(
            access_token=access_token
        ),
        message="注册成功"
    )

# =========================
# 用户登录
# =========================

@router.post(
    "/login",

    # 登录成功之后返回 TokenResponse。
    response_model=ApiResponse[LoginData],
)
async def login(
    data: LoginRequest,
    # 获取数据库 Session。
    db: AsyncSession = Depends(get_db),
):
    # 1. 根据邮箱查询用户
    # SQL：
    # SELECT *
    # FROM users
    # WHERE email = data.email
    result = await db.execute(
        select(User).where(User.email == data.email)
    )

    # 获取 User。
    user = result.scalar_one_or_none()


    # =========================
    # 2. 用户不存在
    # =========================

    if not user:

        # 注意这里不告诉用户：
        # “这个邮箱不存在”
        # 而统一返回：
        #
        # “邮箱或密码错误”
        # 这样可以减少攻击者通过接口判断
        # 某个邮箱是否注册过。
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
        )

    # =========================
    # 3. 验证密码
    # =========================

    # data.password：
    # 用户刚刚输入的密码。
    #
    # user.password_hash：
    # 数据库保存的密码哈希。
    #
    # verify_password() 会验证两者是否匹配。
    if not verify_password(
        data.password,
        user.password_hash
    ):

        # 密码错误。
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱或密码错误",
        )


    # =========================
    # 4. 生成 JWT
    # =========================

    # 邮箱和密码验证成功。
    #
    # 创建属于这个用户的 JWT。
    access_token = create_access_token(user.id)


    # =========================
    # 5. 返回 Token
    # =========================

    return ApiResponse(
        code=0,
        data=LoginData(
            access_token=access_token,
            user=user
        ),
        message="登录成功"
    )

@router.get(
    "/me",
    response_model=ApiResponse[UserResponse],
)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    return ApiResponse(
        code=0,
        data=current_user,
        message="获取用户信息成功"
    )