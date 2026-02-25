from __future__ import annotations

import pytest

from analyst.tools.sql_safety import ensure_read_only_query


def test_sql_safety_allows_select() -> None:
    ensure_read_only_query("SELECT region, SUM(revenue) FROM sample_sales GROUP BY region")


def test_sql_safety_blocks_mutation() -> None:
    with pytest.raises(ValueError, match="Only read-only|Forbidden SQL operation"):
        ensure_read_only_query("DELETE FROM sample_sales")


def test_sql_safety_blocks_multi_statement() -> None:
    with pytest.raises(ValueError, match="Multiple SQL statements"):
        ensure_read_only_query("SELECT 1; SELECT 2;")
