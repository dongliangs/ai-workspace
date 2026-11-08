from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

import agent.executor as executor_module
from agent.executor import execute_tool
from agent.registry import ToolRegistry
from agent.schema import ToolDefinition
from agent.tools import analyze_excel as analyze_excel_module
from agent.tools import generate_chart as generate_chart_module


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeSession:
    def __init__(self, value):
        self.execute = AsyncMock(return_value=_FakeResult(value))


class _FakeSessionContext:
    def __init__(self, value):
        self.session = _FakeSession(value)

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, traceback):
        return False


def _compiled_sql(session):
    statement = session.execute.await_args.args[0]
    return str(statement.compile(compile_kwargs={"literal_binds": True}))


def _file_record(path, original_filename="sample.xlsx"):
    return SimpleNamespace(
        storage_path=str(path),
        original_filename=original_filename,
    )


@pytest.mark.asyncio
async def test_analyze_excel_filters_file_by_owner(tmp_path):
    file_path = tmp_path / "sample.xlsx"
    file_path.touch()
    context = _FakeSessionContext(_file_record(file_path))

    with patch.object(
        analyze_excel_module, "AsyncSessionLocal", return_value=context
    ), patch.object(
        analyze_excel_module,
        "load_excel",
        return_value=(pd.DataFrame({"amount": [1, 2]}), ["Sheet1"], "Sheet1"),
    ):
        result = await analyze_excel_module.analyze_excel_handler(
            file_id=7,
            user_id=42,
            analysis_type="overview",
        )

    assert result["row_count"] == 2
    sql = _compiled_sql(context.session)
    assert "file.id = 7" in sql
    assert "file.user_id = 42" in sql


@pytest.mark.asyncio
async def test_analyze_excel_rejects_file_owned_by_another_user():
    context = _FakeSessionContext(None)

    with patch.object(
        analyze_excel_module, "AsyncSessionLocal", return_value=context
    ), patch.object(analyze_excel_module, "load_excel") as load_excel:
        with pytest.raises(ValueError, match="file_id=7"):
            await analyze_excel_module.analyze_excel_handler(
                file_id=7,
                user_id=2,
            )

    load_excel.assert_not_called()
    sql = _compiled_sql(context.session)
    assert "file.id = 7" in sql
    assert "file.user_id = 2" in sql


@pytest.mark.asyncio
async def test_generate_chart_filters_file_by_owner(tmp_path):
    file_path = tmp_path / "sample.xlsx"
    file_path.touch()
    context = _FakeSessionContext(_file_record(file_path))
    dataframe = pd.DataFrame({"region": ["east", "west"], "amount": [10, 20]})

    with patch.object(
        generate_chart_module, "AsyncSessionLocal", return_value=context
    ), patch.object(
        generate_chart_module,
        "load_excel",
        return_value=(dataframe, ["Sheet1"], "Sheet1"),
    ):
        result = await generate_chart_module.generate_chart_handler(
            file_id=7,
            user_id=42,
            chart_type="bar",
            title="Revenue",
            category_column="region",
            value_column="amount",
        )

    assert result["chart_type"] == "bar"
    assert result["data_points"] == 2
    sql = _compiled_sql(context.session)
    assert "file.id = 7" in sql
    assert "file.user_id = 42" in sql


@pytest.mark.asyncio
async def test_generate_chart_rejects_file_owned_by_another_user():
    context = _FakeSessionContext(None)

    with patch.object(
        generate_chart_module, "AsyncSessionLocal", return_value=context
    ), patch.object(generate_chart_module, "load_excel") as load_excel:
        with pytest.raises(ValueError, match="file_id=7"):
            await generate_chart_module.generate_chart_handler(
                file_id=7,
                user_id=2,
                chart_type="bar",
                title="Revenue",
                category_column="region",
                value_column="amount",
            )

    load_excel.assert_not_called()
    sql = _compiled_sql(context.session)
    assert "file.id = 7" in sql
    assert "file.user_id = 2" in sql


@pytest.mark.asyncio
async def test_executor_injects_unforgeable_user_id():
    captured = {}

    async def handler(file_id: int, user_id: int):
        captured["file_id"] = file_id
        captured["user_id"] = user_id
        return captured

    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="capture_user",
            description="capture injected context",
            parameters={"type": "object", "properties": {}},
        ),
        handler,
    )

    with patch.object(executor_module, "registry", registry):
        result = await execute_tool(
            "capture_user",
            {"file_id": 7, "user_id": 999},
            context={"user_id": 42},
        )

    assert result.status == "success"
    assert result.data == {"file_id": 7, "user_id": 42}
