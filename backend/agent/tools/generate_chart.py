# agent/tools/generate_chart.py
"""
Generate Chart 工具 —— 从 Excel 数据生成 ECharts 图表配置。
===========================================================================
第一版设计理念：
    后端只负责读取 Excel、聚合数据、整理横纵轴、返回 ECharts 配置 JSON。
    不生成 PNG 图片，不关心前端渲染。
    前端用 Vue + ECharts 接收配置后渲染。

支持的图表类型：
    1. bar     柱状图：按某列分组，对另一列聚合，如各地区销售额
    2. line    折线图：按某列排序（通常是时间），展示趋势
    3. pie     饼图：按某列分组，对另一列聚合，展示占比

返回的 ECharts option 结构（前端 setOption 直接用）：
    {
        "title":       {"text": "图表标题"},
        "tooltip":     {"trigger": "..."},
        "legend":      {"data": [...]},
        "xAxis":       {"type": "category", "data": [...]},
        "yAxis":       {"type": "value", "name": "..."},
        "series":      [{"name": "...", "type": "bar|line|pie", "data": [...]}]
    }

使用方式（在应用启动时注册）：
    from agent.tools.generate_chart import generate_chart_definition, generate_chart_handler
    from agent.registry import registry
    registry.register(generate_chart_definition, generate_chart_handler)
===========================================================================
"""
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select

from agent.schema import ToolDefinition
from agent.tools.analyze_excel import load_excel, _json
from db.session import AsyncSessionLocal
from models.file import File

logger = logging.getLogger(__name__)

# 只允许这些聚合操作
ALLOWED_AGGREGATIONS = {"sum", "mean", "count", "min", "max"}

# 支持的图表类型
SUPPORTED_CHART_TYPES = {"bar", "line", "pie"}


# ── 数据聚合 ─────────────────────────────────────────────────────────

def _aggregate_data(
    df: pd.DataFrame,
    category_column: str,
    value_column: str,
    aggregation: str,
    top_n: int,
    sort_by_value: bool = True,
) -> tuple[list, list]:
    """
    按 category_column 分组对 value_column 聚合，返回 (categories, values)。

    Args:
        df:               数据源
        category_column:  分类列（横轴 / 饼图标签）
        value_column:     数值列（纵轴 / 饼图值）
        aggregation:      聚合方式
        top_n:            最多返回多少条
        sort_by_value:    是否按值降序排列（pie/bar 通常 True，line 通常 False）
    """
    if aggregation not in ALLOWED_AGGREGATIONS:
        raise ValueError(
            f"不支持的聚合方式：{aggregation}，可用：{sorted(ALLOWED_AGGREGATIONS)}"
        )

    if category_column not in df.columns:
        raise ValueError(
            f"分类字段不存在：{category_column}，可用字段：{list(df.columns)}"
        )

    if value_column not in df.columns:
        raise ValueError(
            f"数值字段不存在：{value_column}，可用字段：{list(df.columns)}"
        )

    if aggregation != "count" and not pd.api.types.is_numeric_dtype(df[value_column]):
        raise ValueError(
            f"聚合 {aggregation} 要求数值字段，字段 {value_column} 不是数值类型"
        )

    grouped = (
        df.groupby(category_column, dropna=False, sort=False)[value_column]
        .agg(aggregation)
    )

    if sort_by_value:
        grouped = grouped.sort_values(ascending=False)
    else:
        # line 图通常按原始顺序或按 category 排序
        grouped = grouped.sort_index()

    grouped = grouped.head(max(1, min(top_n, 100)))

    categories = _json(grouped.index.tolist())
    values = _json(grouped.values.tolist())

    return categories, values


# ── ECharts 配置生成 ─────────────────────────────────────────────────

def _build_bar_option(
    title: str,
    category_column: str,
    value_column: str,
    aggregation: str,
    categories: list,
    values: list,
) -> dict[str, Any]:
    """生成柱状图 ECharts option。"""
    return {
        "title": {"text": title, "left": "center"},
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
        },
        "legend": {"data": [value_column], "top": "8%"},
        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
        "xAxis": {
            "type": "category",
            "data": categories,
            "axisLabel": {"interval": 0, "rotate": categories and len(categories) > 6 and 30 or 0},
        },
        "yAxis": {
            "type": "value",
            "name": f"{aggregation}({value_column})",
        },
        "series": [
            {
                "name": value_column,
                "type": "bar",
                "data": values,
                "itemStyle": {"borderRadius": [4, 4, 0, 0]},
            }
        ],
    }


def _build_line_option(
    title: str,
    category_column: str,
    value_column: str,
    aggregation: str,
    categories: list,
    values: list,
) -> dict[str, Any]:
    """生成折线图 ECharts option。"""
    return {
        "title": {"text": title, "left": "center"},
        "tooltip": {"trigger": "axis"},
        "legend": {"data": [value_column], "top": "8%"},
        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
        "xAxis": {
            "type": "category",
            "boundaryGap": False,
            "data": categories,
            "axisLabel": {"interval": 0, "rotate": categories and len(categories) > 6 and 30 or 0},
        },
        "yAxis": {
            "type": "value",
            "name": f"{aggregation}({value_column})",
        },
        "series": [
            {
                "name": value_column,
                "type": "line",
                "data": values,
                "smooth": True,
                "areaStyle": {"opacity": 0.3},
            }
        ],
    }


def _build_pie_option(
    title: str,
    category_column: str,
    value_column: str,
    aggregation: str,
    categories: list,
    values: list,
) -> dict[str, Any]:
    """生成饼图 ECharts option。"""
    pie_data = [
        {"name": str(cat), "value": val}
        for cat, val in zip(categories, values)
    ]

    return {
        "title": {"text": title, "left": "center"},
        "tooltip": {"trigger": "item", "formatter": "{a} <br/>{b}: {c} ({d}%)"},
        "legend": {
            "orient": "vertical",
            "left": "left",
            "data": categories,
        },
        "series": [
            {
                "name": f"{aggregation}({value_column})",
                "type": "pie",
                "radius": "60%",
                "center": ["50%", "55%"],
                "data": pie_data,
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowOffsetX": 0,
                        "shadowColor": "rgba(0, 0, 0, 0.5)",
                    }
                },
            }
        ],
    }


# ── Tool Function (执行函数) ─────────────────────────────────────────

async def generate_chart_handler(
    file_id: int,
    chart_type: str,
    title: str,
    category_column: str,
    value_column: str,
    aggregation: str = "sum",
    sheet_name: str | None = None,
    top_n: int = 10,
) -> dict[str, Any]:
    """
    从 Excel 文件读取数据并生成 ECharts 图表配置。

    不生成图片，返回 ECharts option JSON，前端用 Vue + ECharts 渲染。

    Args:
        file_id:          文件 ID
        chart_type:       图表类型：bar=柱状图, line=折线图, pie=饼图
        title:            图表标题
        category_column:  分类列名（横轴 / 饼图标签）
        value_column:     数值列名（纵轴 / 饼图值）
        aggregation:      聚合方式：sum/mean/count/min/max
        sheet_name:       工作表名，不填则第一个
        top_n:            最多展示多少条数据

    Returns:
        {
            "chart_type": "bar",
            "title": "...",
            "echarts_option": { ... ECharts 配置 ... }
        }
    """
    # 1. 参数校验
    if chart_type not in SUPPORTED_CHART_TYPES:
        raise ValueError(
            f"暂不支持的图表类型：{chart_type}，可用：{sorted(SUPPORTED_CHART_TYPES)}"
        )

    if not title:
        raise ValueError("图表标题 title 不能为空")

    if not category_column:
        raise ValueError("分类字段 category_column 不能为空")

    if not value_column:
        raise ValueError("数值字段 value_column 不能为空")

    # 2. 从数据库查文件
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(File).where(File.id == file_id))
        file_record = result.scalar_one_or_none()

    if file_record is None:
        raise ValueError(f"文件不存在：file_id={file_id}")

    file_path = Path(file_record.storage_path)
    if not file_path.exists():
        raise ValueError(f"文件在磁盘上不存在：{file_record.original_filename}")

    # 3. 读取 Excel
    df, sheet_names, selected_sheet = load_excel(file_path, sheet_name)

    logger.info(
        "generate_chart: file_id=%s, chart_type=%s, sheet=%s, shape=%s, "
        "category=%s, value=%s, agg=%s",
        file_id, chart_type, selected_sheet, df.shape,
        category_column, value_column, aggregation,
    )

    # 4. 聚合数据
    #    bar/pie 按值降序排列（突出排名），line 按 category 原序排列（展示趋势）
    sort_by_value = chart_type in ("bar", "pie")
    categories, values = _aggregate_data(
        df, category_column, value_column, aggregation, top_n, sort_by_value
    )

    # 5. 生成 ECharts 配置
    if chart_type == "bar":
        option = _build_bar_option(
            title, category_column, value_column, aggregation, categories, values
        )
    elif chart_type == "line":
        option = _build_line_option(
            title, category_column, value_column, aggregation, categories, values
        )
    else:  # pie
        option = _build_pie_option(
            title, category_column, value_column, aggregation, categories, values
        )

    return {
        "chart_type": chart_type,
        "title": title,
        "sheet_name": selected_sheet,
        "category_column": category_column,
        "value_column": value_column,
        "aggregation": aggregation,
        "data_points": len(categories),
        "echarts_option": option,
    }


# ── Tool Schema (定义) ──────────────────────────────────────────────

generate_chart_definition = ToolDefinition(
    name="generate_chart",
    description=(
        "从用户上传的 Excel 文件读取数据，生成 ECharts 图表配置（不生成图片）。"
        "返回的 echarts_option 可直接用于前端 ECharts setOption 渲染。\n"
        "支持三种图表类型：\n"
        "1. bar（柱状图）：按某列分组对另一列聚合，适合排名对比，如各地区销售额\n"
        "2. line（折线图）：按某列排序展示趋势，适合时间序列，如月度销售趋势\n"
        "3. pie（饼图）：按某列分组对另一列聚合，适合占比分析，如产品销量占比\n"
        "调用时需传 file_id（从上下文消息中获取），并指定 category_column（分类/横轴）"
        "和 value_column（数值/纵轴）。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "file_id": {
                "type": "integer",
                "description": "要分析的文件 ID，从上下文消息中获取",
            },
            "chart_type": {
                "type": "string",
                "enum": ["bar", "line", "pie"],
                "description": "图表类型：bar=柱状图, line=折线图, pie=饼图",
            },
            "title": {
                "type": "string",
                "description": "图表标题，例如：各地区销售额排名",
            },
            "category_column": {
                "type": "string",
                "description": "分类列名，对应横轴或饼图标签，例如：地区",
            },
            "value_column": {
                "type": "string",
                "description": "数值列名，对应纵轴或饼图值，例如：销售额",
            },
            "aggregation": {
                "type": "string",
                "enum": ["sum", "mean", "count", "min", "max"],
                "description": "聚合方式，默认 sum",
            },
            "sheet_name": {
                "type": "string",
                "description": "工作表名称，不填则使用第一个工作表",
            },
            "top_n": {
                "type": "integer",
                "description": "最多展示多少条数据，默认 10",
            },
        },
        "required": ["file_id", "chart_type", "title", "category_column", "value_column"],
        "additionalProperties": False,
    },
)
