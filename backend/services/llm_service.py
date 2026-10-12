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


async def chat_with_tools(messages: list[dict], tools: list[dict]):
    """
    调用 LLM（Chat Completions API），携带工具定义，返回完整响应。

    用于 Agent Loop：模型可以返回文本，也可以返回 tool_calls。
    响应格式（OpenAI Chat Completions）：
        response.choices[0].message.content      → 文本内容（可能为 None）
        response.choices[0].message.tool_calls    → 工具调用列表（可能为 None）

    Args:
        messages: 完整对话上下文（system + history + user + tool results）
        tools:    OpenAI tools 格式的工具定义列表

    Returns:
        ChatCompletion 响应对象
    """
    response = await client.chat.completions.create(
        model=settings.deepseek_model,
        messages=messages,
        tools=tools if tools else None,
    )
    return response


# async def chat_with_llm_stream(messages: list[dict]):
#
#     response = await client.responses.create(
#         model=settings.deepseek_model,
#         input=messages,
#     )
#
#     return response.output_text


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