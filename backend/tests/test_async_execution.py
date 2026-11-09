import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from agent.tools import knowledge_search as knowledge_search_module
from core.async_execution import run_index_sync, run_retrieval_sync


@pytest.mark.asyncio
async def test_index_executor_keeps_event_loop_responsive():
    task = asyncio.create_task(
        run_index_sync(
            time.sleep,
            0.2,
            operation="test_index",
        )
    )

    await asyncio.sleep(0.02)
    assert task.done() is False

    await task


@pytest.mark.asyncio
async def test_retrieval_timeout_is_reported():
    with pytest.raises(TimeoutError, match="test_retrieval"):
        await run_retrieval_sync(
            time.sleep,
            0.1,
            timeout_seconds=0.01,
            operation="test_retrieval",
        )

    # The executor cannot forcibly stop a running Python thread.
    await asyncio.sleep(0.11)


@pytest.mark.asyncio
async def test_knowledge_search_uses_retrieval_executor():
    chunks = [
        {
            "content": "relevant content",
            "document_id": 10,
            "page_number": 1,
            "score": 0.9,
        }
    ]

    with patch.object(
        knowledge_search_module,
        "run_retrieval_sync",
        new=AsyncMock(return_value=chunks),
    ) as run_retrieval, patch.object(
        knowledge_search_module,
        "_fetch_document_filenames",
        new=AsyncMock(return_value={10: "source.txt"}),
    ):
        result = await knowledge_search_module.knowledge_search_handler(
            question="test question",
            user_id=42,
            kb_id=7,
        )

    assert result["found"] is True
    assert result["fragments"][0]["filename"] == "source.txt"
    assert run_retrieval.await_count == 1
    assert run_retrieval.await_args.args[0] is knowledge_search_module.retrieve
