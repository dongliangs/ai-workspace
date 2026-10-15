"""
文档 API 路由 —— 上传/列表/详情/删除。
===========================================================================
路径前缀: /knowledge-bases/{kb_id}/documents 和 /documents/{doc_id}
文件上传复用现有 save_upload_file，索引构建由 document_service 负责。
===========================================================================
"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import get_current_user
from db.session import get_db
from models.user import User
from schemas.common import ApiResponse
from schemas.conversation import PageResponse
from schemas.document import DocumentResponse
from services.document_service import (
    create_and_index,
    get_documents_paginated,
    get_document,
    delete_document,
)
from services.knowledge_service import get_knowledge_base
from services.file_service import save_upload_file, validate_file_extension, validate_file_size

router = APIRouter(tags=["document"])

# 知识库支持的文件类型
KB_ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}


@router.post(
    "/knowledge-bases/{kb_id}/documents",
    response_model=ApiResponse[DocumentResponse],
)
async def upload_document(
    kb_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    上传文档到知识库并构建索引。

    支持 PDF / DOCX / TXT，索引构建同步执行（V0.3 首版）。
    """
    # 1. 校验知识库归属
    kb = await get_knowledge_base(db, kb_id, current_user.id)
    if kb is None:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 2. 校验文件类型
    ext = Path(file.filename or "").suffix.lstrip(".").lower()
    if ext not in KB_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"知识库仅支持 {', '.join(sorted(KB_ALLOWED_EXTENSIONS))} 类型",
        )

    # 3. 校验文件大小
    content = await file.read()
    validate_file_size(len(content))

    # 4. 保存文件（复用 File Service）
    #    save_upload_file 需要 UploadFile 对象，重新包装
    file.file.seek(0)
    file_record = await save_upload_file(
        upload_file=file,
        user_id=current_user.id,
        conversation_id=None,
        db=db,
    )

    # 5. 创建文档记录 + 构建索引
    doc = await create_and_index(
        db=db,
        kb_id=kb_id,
        user_id=current_user.id,
        file_record=file_record,
        filename=file_record.original_filename,
        file_type=ext,
    )

    return ApiResponse(
        code=0,
        data=DocumentResponse.model_validate(doc),
        message="文档上传成功" if doc.status.value == "indexed" else "文档处理失败",
    )


@router.get(
    "/knowledge-bases/{kb_id}/documents",
    response_model=ApiResponse[PageResponse[DocumentResponse]],
)
async def list_documents(
    kb_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """获取知识库文档列表"""
    # 校验知识库归属
    kb = await get_knowledge_base(db, kb_id, current_user.id)
    if kb is None:
        raise HTTPException(status_code=404, detail="知识库不存在")

    items, total = await get_documents_paginated(db, kb_id, page, page_size)
    return ApiResponse(
        code=0,
        data=PageResponse(
            items=[DocumentResponse.model_validate(d) for d in items],
            total=total,
            page=page,
            page_size=page_size,
        ),
        message="获取文档列表成功",
    )


@router.get("/documents/{doc_id}", response_model=ApiResponse[DocumentResponse])
async def get_document_detail(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查看文档索引状态"""
    doc = await get_document(db, doc_id, current_user.id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    return ApiResponse(
        code=0,
        data=DocumentResponse.model_validate(doc),
        message="获取文档详情成功",
    )


@router.delete("/documents/{doc_id}", response_model=ApiResponse[None])
async def delete_document_route(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除文档（同步清理向量）"""
    ok = await delete_document(db, doc_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="文档不存在")
    return ApiResponse(code=0, data=None, message="删除文档成功")
