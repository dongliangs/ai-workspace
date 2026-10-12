from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from db.session import get_db
from models.user import User
from schemas.common import ApiResponse
from schemas.file import FileUploadResponse
from services.file_service import save_upload_file

router = APIRouter(
    prefix="/files",
    tags=["file"],
)


@router.post(
    "/upload",
    response_model=ApiResponse[FileUploadResponse],
)
async def upload_file(
    file: UploadFile = File(...),
    conversation_id: int | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    上传文件。

    三种会话类型 (chat / agent / knowledge) 都支持文件上传，
    不同模式下上传的文件后续用途不同：
    - chat:    作为对话上下文附件
    - agent:   供 Agent 工具调用（如 analyze_excel）
    - knowledge: 作为知识库原始素材

    权限校验：
    - 用户必须已登录
    - 如果指定了 conversation_id，校验该会话属于当前用户

    参数：
    - file:         上传的文件 (multipart/form-data)
    - conversation_id: 可选，关联的会话 ID

    返回 file_id，前端在发送消息时通过 file_ids 携带。
    """
    file_record = await save_upload_file(
        upload_file=file,
        user_id=current_user.id,
        conversation_id=conversation_id,
        db=db,
    )

    return ApiResponse(
        code=0,
        data=FileUploadResponse.model_validate(file_record),
        message="文件上传成功",
    )
