from pydantic import BaseModel


class GenerationCancelResponse(BaseModel):
    """停止生成接口返回的数据。"""

    generation_id: str
    conversation_id: int
    status: str = "cancelling"
