from __future__ import annotations

from pathlib import Path

import pandas as pd

from analyst.models import VisualizationRequest
from analyst.tools.data_loader import list_available_datasets, load_dataset
from analyst.tools.schema_inspector import inspect_correlations, inspect_schema
from analyst.tools.visualizer import create_visualization


def test_load_dataset_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("a,b\n1,2\n3,4\n")

    df = load_dataset(csv_path)

    assert list(df.columns) == ["a", "b"]
    assert len(df) == 2


def test_list_available_datasets(tmp_path: Path) -> None:
    (tmp_path / "one.csv").write_text("x\n1\n2\n")
    (tmp_path / "two.tsv").write_text("x\ty\n1\t2\n")
    (tmp_path / "ignore.txt").write_text("ignore")

    datasets = list_available_datasets(tmp_path)
    names = [item["name"] for item in datasets]

    assert "one.csv" in names
    assert "two.tsv" in names
    assert "ignore.txt" not in names


def test_schema_inspector_outputs_expected_sections() -> None:
    df = pd.DataFrame(
        {
            "region": ["north", "south", "north"],
            "revenue": [10.0, 20.5, 30.0],
        }
    )
    text = inspect_schema(df, "sales")

    assert "Dataset: sales" in text
    assert "Shape: 3 rows x 2 columns" in text
    assert "region" in text
    assert "revenue" in text


def test_correlation_inspector_handles_numeric_data() -> None:
    df = pd.DataFrame({"a": [1, 2, 3], "b": [2, 4, 6]})
    text = inspect_correlations(df)
    assert "Correlation matrix:" in text
    assert "a" in text and "b" in text


def test_visualizer_creates_chart_file(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "region": ["north", "south", "east"],
            "revenue": [100, 200, 150],
        }
    )
    request = VisualizationRequest(
        chart_type="bar",
        title="Revenue by Region",
        x_column="region",
        y_column="revenue",
        description="Check sales mix",
    )

    output = create_visualization(df, request, tmp_path)
    output_path = Path(output)

    assert output_path.exists()
    assert output_path.suffix == ".png"
