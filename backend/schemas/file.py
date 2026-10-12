from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FileUploadResponse(BaseModel):
    """文件上传成功后返回给前端的数据"""

    id: int
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    status: str
    conversation_id: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
