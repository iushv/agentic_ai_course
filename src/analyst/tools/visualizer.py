"""Visualization tool helpers.

This module provides deterministic chart generation utilities that can be
called by the agent or by tests without relying on a notebook runtime.
"""

from __future__ import annotations

from pathlib import Path
import re

import matplotlib.pyplot as plt
import pandas as pd

from analyst.models import VisualizationRequest


SUPPORTED_CHART_TYPES = {
    "bar",
    "line",
    "scatter",
    "pie",
    "heatmap",
    "histogram",
    "box",
}


def create_visualization(
    df: pd.DataFrame,
    request: VisualizationRequest,
    output_dir: str | Path,
) -> str:
    """Create a chart from a dataframe and save it as a PNG file."""
    _validate_request(df, request)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    filename = f"{_slugify(request.title)}_{request.chart_type}.png"
    save_path = output_path / filename

    chart_type = request.chart_type.lower()
    plt.figure(figsize=(10, 6))

    if chart_type == "bar":
        _bar_chart(df, request)
    elif chart_type == "line":
        _line_chart(df, request)
    elif chart_type == "scatter":
        _scatter_chart(df, request)
    elif chart_type == "pie":
        _pie_chart(df, request)
    elif chart_type == "heatmap":
        _heatmap(df)
    elif chart_type == "histogram":
        _histogram(df, request)
    elif chart_type == "box":
        _box(df, request)
    else:
        raise ValueError(
            f"Unsupported chart type '{request.chart_type}'. "
            f"Supported: {sorted(SUPPORTED_CHART_TYPES)}"
        )

    plt.title(request.title)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    return str(save_path)


def _validate_request(df: pd.DataFrame, request: VisualizationRequest) -> None:
    if request.chart_type.lower() not in SUPPORTED_CHART_TYPES:
        raise ValueError(
            f"Unsupported chart type '{request.chart_type}'. "
            f"Supported: {sorted(SUPPORTED_CHART_TYPES)}"
        )

    if request.chart_type.lower() == "heatmap":
        return

    for column in (request.x_column, request.y_column):
        if column and column not in df.columns:
            raise ValueError(f"Column '{column}' not found in dataset")

    if request.group_by and request.group_by not in df.columns:
        raise ValueError(f"group_by column '{request.group_by}' not found in dataset")


def _bar_chart(df: pd.DataFrame, request: VisualizationRequest) -> None:
    if request.group_by:
        grouped = (
            df.groupby([request.x_column, request.group_by], dropna=False)[request.y_column]
            .sum()
            .unstack(fill_value=0)
        )
        grouped.plot(kind="bar")
        plt.xlabel(request.x_column)
        plt.ylabel(request.y_column)
        return

    grouped = df.groupby(request.x_column, dropna=False)[request.y_column].sum().sort_values(ascending=False)
    grouped.plot(kind="bar")
    plt.xlabel(request.x_column)
    plt.ylabel(f"sum({request.y_column})")


def _line_chart(df: pd.DataFrame, request: VisualizationRequest) -> None:
    line_df = df.sort_values(request.x_column)
    if request.group_by:
        for key, gdf in line_df.groupby(request.group_by):
            plt.plot(gdf[request.x_column], gdf[request.y_column], marker="o", label=str(key))
        plt.legend(title=request.group_by)
    else:
        plt.plot(line_df[request.x_column], line_df[request.y_column], marker="o")
    plt.xlabel(request.x_column)
    plt.ylabel(request.y_column)


def _scatter_chart(df: pd.DataFrame, request: VisualizationRequest) -> None:
    if request.group_by:
        for key, gdf in df.groupby(request.group_by):
            plt.scatter(gdf[request.x_column], gdf[request.y_column], label=str(key), alpha=0.7)
        plt.legend(title=request.group_by)
    else:
        plt.scatter(df[request.x_column], df[request.y_column], alpha=0.7)
    plt.xlabel(request.x_column)
    plt.ylabel(request.y_column)


def _pie_chart(df: pd.DataFrame, request: VisualizationRequest) -> None:
    pie_df = df.groupby(request.x_column, dropna=False)[request.y_column].sum()
    plt.pie(pie_df.values, labels=pie_df.index.astype(str), autopct="%1.1f%%")


def _heatmap(df: pd.DataFrame) -> None:
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.empty:
        raise ValueError("Heatmap requires at least one numeric column")

    corr = numeric_df.corr()
    plt.imshow(corr, cmap="coolwarm", interpolation="nearest")
    plt.xticks(range(len(corr.columns)), corr.columns, rotation=45, ha="right")
    plt.yticks(range(len(corr.columns)), corr.columns)
    plt.colorbar(label="Correlation")


def _histogram(df: pd.DataFrame, request: VisualizationRequest) -> None:
    plt.hist(df[request.x_column].dropna(), bins=20)
    plt.xlabel(request.x_column)
    plt.ylabel("Count")


def _box(df: pd.DataFrame, request: VisualizationRequest) -> None:
    if request.group_by:
        groups = [g[request.y_column].dropna().values for _, g in df.groupby(request.group_by)]
        labels = [str(label) for label, _ in df.groupby(request.group_by)]
        plt.boxplot(groups, labels=labels)
        plt.xlabel(request.group_by)
    else:
        plt.boxplot(df[request.y_column].dropna())
    plt.ylabel(request.y_column)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return slug or "chart"
