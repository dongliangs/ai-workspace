from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
# from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import true
from contextlib import asynccontextmanager
#导入auth路由
#router就是在 auth.py 中创建的APIRouter
from schemas.common import ApiResponse
from api.auth import router as auth_router
from api.conversation import router as conversation_router
#导入数据库engine
from db.session import engine

#导入 SQLALCHEMY base
from models.base import Base
#导入user 模型
from models.user import User



#定义创建表的异步函数
async def create_tables():
    #建立数据库连接
    async with engine.begin() as conn:
        #创建对应的数据库表
        await conn.run_sync(Base.metadata.create_all)

#使用 lifespan 管理应用启动事件
@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield

app = FastAPI(lifespan=lifespan)

#把auth_router 注册到FastAPI. 加上前缀prefix="/api";
# 所有的auth接口签名自动加 /api
app.include_router(auth_router, prefix="/api")
app.include_router(conversation_router, prefix="/api")

#统一处理HttpException
@app.exception_handler(HTTPException)
async def http_exception_handler(
        request: Request, exc: HTTPException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(
            ApiResponse(
                code=exc.status_code,
                data=None,
                message=str(exc.detail),
            )
        ),
    )


# 统一处理请求参数校验错误
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(
            ApiResponse(
                code=422,
                data=exc.errors(),
                message="请求参数校验失败"
            )
        )
    )

#统一处理未捕获异常
#防止服务器发生位置错误时
@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception
):
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "data": None,
            "message": "服务器内部错误",
        }
    )

#配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 开发环境通配
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )