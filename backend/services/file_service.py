import os
import uuid
from pathlib import Path

import aiofiles
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.conversation import Conversation
from models.file import File, FileStatus


def _get_allowed_extensions() -> set[str]:
    """从配置中解析允许的文件扩展名集合。"""
    return {
        ext.strip().lower()
        for ext in settings.allowed_file_extensions.split(",")
        if ext.strip()
    }


def validate_file_extension(filename: str) -> None:
    """校验文件扩展名是否在允许列表中。"""
    allowed = _get_allowed_extensions()
    ext = Path(filename).suffix.lstrip(".").lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: .{ext}，允许的类型: {', '.join(sorted(allowed))}",
        )


def validate_file_size(file_size: int) -> None:
    """校验文件大小是否超过限制。"""
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制，最大允许 {settings.max_file_size_mb}MB",
        )


async def verify_conversation_ownership(
    conversation_id: int,
    user_id: int,
    db: AsyncSession,
) -> Conversation:
    """验证会话是否属于当前用户，返回会话对象。"""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在",
        )
    return conversation


async def save_upload_file(
    upload_file: UploadFile,
    user_id: int,
    conversation_id: int | None,
    db: AsyncSession,
) -> File:
    """
    保存上传文件到磁盘并创建 File 数据库记录。

    流程：
    1. 校验扩展名和大小
    2. 如果提供了 conversation_id，校验会话归属
    3. 生成 UUID 文件名，按用户分目录存储
    4. 异步写入磁盘
    5. 创建 File 记录并返回
    """
    # 1. 校验扩展名
    validate_file_extension(upload_file.filename or "")

    # 2. 读取文件内容并校验大小
    content = await upload_file.read()
    validate_file_size(len(content))

    # 3. 校验会话归属（如果指定了会话）
    if conversation_id is not None:
        await verify_conversation_ownership(conversation_id, user_id, db)

    # 4. 生成存储路径: uploads/{user_id}/{uuid_filename}
    ext = Path(upload_file.filename or "").suffix.lower()
    stored_filename = f"{uuid.uuid4().hex}{ext}"
    user_dir = Path(settings.upload_dir) / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    storage_path = user_dir / stored_filename

    # 5. 异步写入磁盘
    async with aiofiles.open(str(storage_path), "wb") as f:
        await f.write(content)

    # 6. 创建数据库记录
    file_record = File(
        user_id=user_id,
        conversation_id=conversation_id,
        message_id=None,
        filename=stored_filename,
        original_filename=upload_file.filename or stored_filename,
        storage_path=str(storage_path),
        file_type=upload_file.content_type or "application/octet-stream",
        file_size=len(content),
        status=FileStatus.READY,
    )
    db.add(file_record)
    await db.commit()
    await db.refresh(file_record)

    return file_record


async def verify_file_ownership(
    file_id: int,
    user_id: int,
    db: AsyncSession,
) -> File:
    """
    校验文件是否属于当前用户。
    在发送消息携带 file_ids 时，逐个校验文件归属。
    """
    result = await db.execute(
        select(File).where(
            File.id == file_id,
            File.user_id == user_id,
        )
    )
    file_record = result.scalar_one_or_none()
    if file_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文件不存在或无权访问: file_id={file_id}",
        )
    return file_record


async def associate_files_with_message(
    file_ids: list[int],
    message_id: int,
    conversation_id: int,
    user_id: int,
    db: AsyncSession,
) -> list[File]:
    """
    将文件关联到消息：
    1. 逐个校验文件属于当前用户
    2. 更新 file 记录的 message_id 和 conversation_id
    3. 返回关联的 File 列表
    """
    if not file_ids:
        return []

    files: list[File] = []
    for fid in file_ids:
        file_record = await verify_file_ownership(fid, user_id, db)
        files.append(file_record)

    # 批量更新关联关系
    await db.execute(
        update(File)
        .where(File.id.in_(file_ids))
        .values(message_id=message_id, conversation_id=conversation_id)
    )
    await db.commit()

    return files
