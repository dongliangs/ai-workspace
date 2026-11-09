from fastapi import APIRouter, Depends, HTTPException, status

from core.security import get_current_user
from models.user import User
from schemas.common import ApiResponse
from schemas.generation import GenerationCancelResponse
from services.generation_manager import cancel_generation

router = APIRouter(
    prefix="/generations",
    tags=["generation"],
)


@router.post(
    "/{generation_id}/cancel",
    response_model=ApiResponse[GenerationCancelResponse],
)
async def cancel_generation_request(
    generation_id: str,
    current_user: User = Depends(get_current_user),
):
    """请求停止当前用户正在执行的生成任务。"""
    handle = cancel_generation(generation_id, current_user.id)
    if handle is None:
        # 不区分“任务不存在”和“无权访问”，避免泄露其他用户的生成 ID。
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="生成任务不存在或已经结束",
        )

    return ApiResponse(
        code=0,
        data=GenerationCancelResponse(
            generation_id=handle.generation_id,
            conversation_id=handle.conversation_id,
        ),
        message="已发送停止生成请求",
    )
