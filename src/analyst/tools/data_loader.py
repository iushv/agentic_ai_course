"""Data Loader Tool — loads datasets from files into DataFrames.

Supports CSV, JSON, and Parquet formats. This tool handles the
data ingestion layer — converting files into pandas DataFrames
that the agent can then query.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


SUPPORTED_FORMATS = {".csv", ".json", ".jsonl", ".parquet", ".xlsx", ".tsv"}


def load_dataset(file_path: str | Path) -> pd.DataFrame:
    """Load a dataset from a file path.

    Automatically detects format from file extension.
    Raises ValueError for unsupported formats.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    suffix = path.suffix.lower()

    if suffix not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported format '{suffix}'. Supported: {SUPPORTED_FORMATS}"
        )

    loaders = {
        ".csv": lambda p: pd.read_csv(p),
        ".tsv": lambda p: pd.read_csv(p, sep="\t"),
        ".json": lambda p: pd.read_json(p),
        ".jsonl": lambda p: pd.read_json(p, lines=True),
        ".parquet": lambda p: pd.read_parquet(p),
        ".xlsx": lambda p: pd.read_excel(p),
    }

    df = loaders[suffix](path)
    return df


def list_available_datasets(data_dir: str | Path) -> list[dict]:
    """List all loadable datasets in a directory."""
    data_path = Path(data_dir)
    if not data_path.is_dir():
        return []

    datasets = []
    for f in sorted(data_path.iterdir()):
        if f.suffix.lower() in SUPPORTED_FORMATS:
            try:
                df = load_dataset(f)
                datasets.append({
                    "name": f.name,
                    "path": str(f),
                    "rows": len(df),
                    "columns": len(df.columns),
                    "size_kb": round(f.stat().st_size / 1024, 1),
                })
            except Exception as e:
                datasets.append({
                    "name": f.name,
                    "path": str(f),
                    "error": str(e),
                })

    return datasets
