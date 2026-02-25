"""Schema Inspector Tool — lets the agent examine dataset structure.

This tool gives the agent the ability to "see" what's in a dataset
without needing to write code. It's the agent's first step when
encountering a new dataset.
"""

from __future__ import annotations

import pandas as pd


def inspect_schema(df: pd.DataFrame, dataset_name: str = "unknown") -> str:
    """Generate a detailed schema description of a DataFrame.

    Returns a formatted string that the LLM can read and understand.
    This is used as a tool response — the LLM sees this text.
    """
    lines = [
        f"Dataset: {dataset_name}",
        f"Shape: {df.shape[0]} rows x {df.shape[1]} columns",
        "",
        "Columns:",
    ]

    for col in df.columns:
        dtype = str(df[col].dtype)
        null_count = int(df[col].isna().sum())
        unique_count = df[col].nunique()

        # Get sample values (non-null, up to 5)
        samples = df[col].dropna().unique()[:5]
        sample_str = ", ".join(str(s) for s in samples)

        lines.append(f"  - {col} ({dtype})")
        lines.append(f"    Unique values: {unique_count}, Nulls: {null_count}")
        lines.append(f"    Samples: {sample_str}")

        # Numeric stats
        if pd.api.types.is_numeric_dtype(df[col]):
            lines.append(
                f"    Range: [{df[col].min()}, {df[col].max()}], "
                f"Mean: {df[col].mean():.2f}"
            )

    return "\n".join(lines)


def inspect_correlations(df: pd.DataFrame) -> str:
    """Generate a correlation matrix for numeric columns."""
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.empty:
        return "No numeric columns found for correlation analysis."

    corr = numeric_df.corr().round(3)
    return f"Correlation matrix:\n{corr.to_string()}"


def inspect_value_counts(df: pd.DataFrame, column: str, top_n: int = 10) -> str:
    """Get value counts for a categorical column."""
    if column not in df.columns:
        return f"Error: Column '{column}' not found. Available: {list(df.columns)}"

    counts = df[column].value_counts().head(top_n)
    return f"Value counts for '{column}':\n{counts.to_string()}"
