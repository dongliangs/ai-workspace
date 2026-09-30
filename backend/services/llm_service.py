# services/llm_service.py

from openai import AsyncOpenAI

from core.config import settings


# 创建 OpenAI 异步客户端
if settings.deepseek_base_url:
    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )
else:
    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
    )


async def chat_with_llm(messages: list[dict]) -> str:
    """
    调用 LLM，返回文本结果。

    messages 示例：

    [
        {
            "role": "user",
            "content": "你好"
        },
        {
            "role": "assistant",
            "content": "你好，有什么可以帮助你的？"
        }
    ]
    """

    response = await client.responses.create(
        model=settings.deepseek_model,
        input=messages,
    )

    return response.output_text


async def chat_with_llm_stream(messages: list[dict]):
    """
    调用 LLM，流式返回文本块（async generator，逐段 yield str 增量）。

    messages 示例同 chat_with_llm。
    """
    stream = await client.responses.create(
        model=settings.deepseek_model,
        input=messages,
        stream=True,
    )
    async for event in stream:
        # Responses API 流式增量事件
        if getattr(event, "type", None) == "response.output_text.delta":
            yield event.delta