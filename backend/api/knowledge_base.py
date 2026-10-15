"""
知识库 API 路由 —— CRUD + 分页。
===========================================================================
路径前缀: /knowledge-bases
所有操作通过 get_current_user 校验 JWT，并验证资源归属。
===========================================================================
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from db.session import get_db
from models.user import User
from schemas.common import ApiResponse
from schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    KnowledgeBaseDetailResponse,
)
from schemas.document import DocumentResponse
from schemas.conversation import PageResponse
from services.knowledge_service import (
    create_knowledge_base,
    get_knowledge_bases_paginated,
    get_knowledge_base,
    update_knowledge_base,
    delete_knowledge_base,
    count_documents,
)

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-base"])


@router.post("", response_model=ApiResponse[KnowledgeBaseResponse])
async def create_kb(
    data: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建知识库"""
    kb = await create_knowledge_base(
        db, user_id=current_user.id, name=data.name, description=data.description
    )
    return ApiResponse(
        code=0,
        data=KnowledgeBaseResponse.model_validate(kb),
        message="创建知识库成功",
    )


@router.get("", response_model=ApiResponse[PageResponse[KnowledgeBaseResponse]])
async def list_kbs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    """分页获取知识库列表"""
    items, total = await get_knowledge_bases_paginated(
        db, user_id=current_user.id, page=page, page_size=page_size
    )
    return ApiResponse(
        code=0,
        data=PageResponse(
            items=[KnowledgeBaseResponse.model_validate(kb) for kb in items],
            total=total,
            page=page,
            page_size=page_size,
        ),
        message="获取知识库列表成功",
    )


@router.get("/{kb_id}", response_model=ApiResponse[KnowledgeBaseDetailResponse])
async def get_kb_detail(
    kb_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取知识库详情（含文档数量）"""
    kb = await get_knowledge_base(db, kb_id, current_user.id)
    if kb is None:
        raise HTTPException(status_code=404, detail="知识库不存在")

    doc_count = await count_documents(db, kb_id)
    resp = KnowledgeBaseDetailResponse.model_validate(kb)
    resp.document_count = doc_count

    return ApiResponse(code=0, data=resp, message="获取知识库详情成功")


@router.patch("/{kb_id}", response_model=ApiResponse[KnowledgeBaseResponse])
async def update_kb(
    kb_id: int,
    data: KnowledgeBaseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改知识库信息"""
    kb = await update_knowledge_base(
        db, kb_id, current_user.id, name=data.name, description=data.description
    )
    if kb is None:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return ApiResponse(
        code=0,
        data=KnowledgeBaseResponse.model_validate(kb),
        message="修改知识库成功",
    )


@router.delete("/{kb_id}", response_model=ApiResponse[None])
async def delete_kb(
    kb_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除知识库（级联清理文档和向量）"""
    ok = await delete_knowledge_base(db, kb_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return ApiResponse(code=0, data=None, message="删除知识库成功")
