# 定义泛型类型

from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):

    """
    后端API的统一响应格式
    """
    # 业务状态码
    #0：成功，非0： 失败
    code:int
    data:T | None = None
    message: str