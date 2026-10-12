# agent/tools/analyze_excel.py
"""
Analyze Excel 工具 —— 读取并分析用户上传的 Excel 文件。
===========================================================================
适配三层架构：ToolDefinition (Schema) + analyze_excel_handler (Function)

三种分析能力：
    1. overview    数据概览：工作表、列名、行列数、数据类型、缺失值、样例数据
    2. statistics  统计分析：对指定数值列计算 sum/mean/max/min/count
    3. group_by   分组分析：按某列分组，对另一列聚合，如按地区分组求销售额

使用方式（在应用启动时注册）：
    from agent.tools.analyze_excel import analyze_excel_definition, analyze_excel_handler
    from agent.registry import registry
    registry.register(analyze_excel_definition, analyze_excel_handler)

安全设计：
    - handler 接收 file_id（不是文件路径），从数据库查 File 记录获取 storage_path
    - 只允许预定义的聚合操作，不执行任意表达式
    - 限制最大读取行数，防止大文件阻塞
===========================================================================
"""
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select

from agent.schema import ToolDefinition
from db.session import AsyncSessionLocal
from models.file import File

logger = logging.getLogger(__name__)

# 第一版限制最多读取 20,000 行，避免文件过大造成阻塞
MAX_ROWS = 20_000

# 只允许这些聚合操作，不能执行模型任意生成的表达式
ALLOWED_AGGREGATIONS = {"sum", "mean", "count", "min", "max"}


# ── 核心读取逻辑 ──────────────────────────────────────────────────────

def load_excel(
    file_path: Path,
    sheet_name: str | None = None,
) -> tuple[pd.DataFrame, list[str], str]:
    """
    读取工作表，返回 (DataFrame, 所有工作表名, 当前工作表名)。

    Args:
        file_path:   文件在磁盘上的路径
        sheet_name:  指定工作表名，None 则读取第一个
    """
    with pd.ExcelFile(file_path) as excel:
        sheet_names = excel.sheet_names

        if not sheet_names:
            raise ValueError("Excel 文件中没有可读取的工作表")

        selected_sheet = sheet_name or sheet_names[0]

        if selected_sheet not in sheet_names:
            raise ValueError(
                f"工作表不存在：{selected_sheet}。"
                f"可用工作表：{sheet_names}"
            )

        df = pd.read_excel(excel, sheet_name=selected_sheet, nrows=MAX_ROWS)

    # 统一列名格式，方便检查模型传入的字段
    df.columns = [str(col).strip() for col in df.columns]

    if df.empty:
        raise ValueError("当前工作表没有可分析的数据")

    return df, sheet_names, selected_sheet


def _json(obj: Any) -> Any:
    """通过 JSON 序列化/反序列化，消除 numpy/pandas 特有类型，确保返回纯 Python 类型。"""
    return json.loads(
        json.dumps(obj, ensure_ascii=False, default=str)
    )


# ── 三种分析类型 ──────────────────────────────────────────────────────

def _analyze_overview(df: pd.DataFrame, sheet_names: list[str], selected_sheet: str) -> dict:
    """数据概览：工作表、列名、行列数、数据类型、缺失值、样例数据。"""
    numeric_df = df.select_dtypes(include="number")
    numeric_summary = _json(numeric_df.describe().to_dict()) if not numeric_df.empty else {}

    columns = [
        {
            "name": str(col),
            "dtype": str(df[col].dtype),
            "missing_count": int(df[col].isna().sum()),
            "unique_count": int(df[col].nunique()),
        }
        for col in df.columns
    ]

    preview = _json(
        df.head(5).to_dict(orient="records")
    )

    return {
        "analysis_type": "overview",
        "sheet_name": selected_sheet,
        "available_sheets": sheet_names,
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": columns,
        "numeric_summary": numeric_summary,
        "preview": preview,
        "truncated": len(df) >= MAX_ROWS,
    }


def _analyze_statistics(df: pd.DataFrame, sheet_names: list[str], selected_sheet: str,
                        column: str) -> dict:
    """
    统计分析：对指定列计算 sum/mean/max/min/count。

    数值列返回完整统计；非数值列只返回 count。
    """
    if column not in df.columns:
        raise ValueError(f"字段不存在：{column}，可用字段：{list(df.columns)}")

    col_data = df[column]
    is_numeric = pd.api.types.is_numeric_dtype(col_data)
    non_null = col_data.dropna()

    stats: dict[str, Any] = {
        "count": int(non_null.shape[0]),
        "missing_count": int(col_data.isna().sum()),
    }

    if is_numeric:
        stats["sum"] = _json(float(non_null.sum()))
        stats["mean"] = _json(float(non_null.mean()))
        stats["max"] = _json(float(non_null.max()))
        stats["min"] = _json(float(non_null.min()))
        stats["std"] = _json(float(non_null.std()))
    else:
        stats["unique_count"] = int(non_null.nunique())
        stats["top_values"] = _json(non_null.value_counts().head(10).to_dict())

    return {
        "analysis_type": "statistics",
        "sheet_name": selected_sheet,
        "column": column,
        "dtype": str(col_data.dtype),
        "is_numeric": is_numeric,
        "statistics": stats,
    }


def _analyze_group_by(df: pd.DataFrame, sheet_names: list[str], selected_sheet: str,
                      group_by_column: str, value_column: str,
                      aggregation: str, top_n: int) -> dict:
    """分组分析：按某列分组，对另一列聚合。"""
    if aggregation not in ALLOWED_AGGREGATIONS:
        raise ValueError(f"不支持的统计操作：{aggregation}，可用：{sorted(ALLOWED_AGGREGATIONS)}")

    if group_by_column not in df.columns:
        raise ValueError(f"分组字段不存在：{group_by_column}，可用字段：{list(df.columns)}")

    if value_column not in df.columns:
        raise ValueError(f"统计字段不存在：{value_column}，可用字段：{list(df.columns)}")

    if aggregation != "count" and not pd.api.types.is_numeric_dtype(df[value_column]):
        raise ValueError(f"求和、平均值等操作要求数值字段，字段 {value_column} 不是数值类型")

    result = (
        df.groupby(group_by_column, dropna=False, sort=False)[value_column]
        .agg(aggregation)
        .sort_values(ascending=False)
        .head(max(1, min(top_n, 50)))
        .rename("result")
        .reset_index()
    )

    return {
        "analysis_type": "group_by",
        "sheet_name": selected_sheet,
        "group_by_column": group_by_column,
        "value_column": value_column,
        "aggregation": aggregation,
        "data": _json(result.to_dict(orient="records")),
    }


# ── Tool Function (执行函数) ─────────────────────────────────────────

async def analyze_excel_handler(
    file_id: int,
    analysis_type: str = "overview",
    sheet_name: str | None = None,
    column: str | None = None,
    group_by_column: str | None = None,
    value_column: str | None = None,
    aggregation: str = "sum",
    top_n: int = 10,
) -> dict[str, Any]:
    """
    分析 Excel 文件，返回结构化数据供 Agent 使用。

    Args:
        file_id:          文件 ID（从上下文中获取，对应 File 表主键）
        analysis_type:    分析类型：overview | statistics | group_by
        sheet_name:       工作表名称，不填则使用第一个
        column:           statistics 模式下要统计的列名
        group_by_column:  group_by 模式下的分组列名
        value_column:     group_by 模式下的聚合列名
        aggregation:      group_by 模式下的聚合方式：sum/mean/count/min/max
        top_n:            group_by 模式下最多返回多少条结果

    Returns:
        结构化分析结果 dict
    """
    # 1. 从数据库查文件记录
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(File).where(File.id == file_id))
        file_record = result.scalar_one_or_none()

    if file_record is None:
        raise ValueError(f"文件不存在：file_id={file_id}")

    file_path = Path(file_record.storage_path)
    if not file_path.exists():
        raise ValueError(f"文件在磁盘上不存在：{file_record.original_filename}")

    # 2. 读取 Excel
    df, sheet_names, selected_sheet = load_excel(file_path, sheet_name)

    logger.info(
        "analyze_excel: file_id=%s, sheet=%s, analysis=%s, shape=%s",
        file_id, selected_sheet, analysis_type, df.shape,
    )

    # 3. 执行对应分析
    if analysis_type == "overview":
        return _analyze_overview(df, sheet_names, selected_sheet)

    if analysis_type == "statistics":
        if not column:
            raise ValueError("statistics 分析需要指定 column 参数")
        return _analyze_statistics(df, sheet_names, selected_sheet, column)

    if analysis_type == "group_by":
        if not group_by_column or not value_column:
            raise ValueError("group_by 分析需要指定 group_by_column 和 value_column 参数")
        return _analyze_group_by(
            df, sheet_names, selected_sheet,
            group_by_column, value_column, aggregation, top_n,
        )

    raise ValueError(
        f"暂不支持的分析类型：{analysis_type}，可用：overview / statistics / group_by"
    )


# ── Tool Schema (定义) ──────────────────────────────────────────────

analyze_excel_definition = ToolDefinition(
    name="analyze_excel",
    description=(
        "分析用户上传的 Excel 文件。支持三种分析类型：\n"
        "1. overview（数据概览）：读取工作表、列名、行列数、数据类型、缺失值、样例数据。"
        "首次分析未知表格时使用。\n"
        "2. statistics（统计分析）：对指定列计算 sum/mean/max/min/count。"
        "了解字段后，对单个数值列做统计时使用。\n"
        "3. group_by（分组分析）：按某列分组对另一列聚合，如按地区分组求销售额排名。"
        "需要指定 group_by_column、value_column 和 aggregation。\n"
        "调用时需传 file_id（从上下文消息中获取）。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "file_id": {
                "type": "integer",
                "description": "要分析的文件 ID，从上下文消息中获取",
            },
            "analysis_type": {
                "type": "string",
                "enum": ["overview", "statistics", "group_by"],
                "description": "分析类型：overview=数据概览, statistics=单列统计, group_by=分组聚合",
            },
            "sheet_name": {
                "type": "string",
                "description": "工作表名称，不填则使用第一个工作表",
            },
            "column": {
                "type": "string",
                "description": "statistics 模式下要统计的列名",
            },
            "group_by_column": {
                "type": "string",
                "description": "group_by 模式下的分组列名，例如：地区",
            },
            "value_column": {
                "type": "string",
                "description": "group_by 模式下的聚合列名，例如：销售额",
            },
            "aggregation": {
                "type": "string",
                "enum": ["sum", "mean", "count", "min", "max"],
                "description": "group_by 模式下的聚合方式，默认 sum",
            },
            "top_n": {
                "type": "integer",
                "description": "group_by 模式下最多返回多少条分组结果，默认 10",
            },
        },
        "required": ["file_id", "analysis_type"],
        "additionalProperties": False,
    },
)
