"""Safety checks for SQL queries used by the agent."""

from __future__ import annotations

import re


READONLY_STARTERS = ("select", "with")
FORBIDDEN_KEYWORDS = (
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "truncate",
    "attach",
    "detach",
    "copy",
    "call",
    "grant",
    "revoke",
)


def ensure_read_only_query(query: str) -> None:
    text = query.strip().lower()
    if not text:
        raise ValueError("SQL query cannot be empty")
    if not text.startswith(READONLY_STARTERS):
        raise ValueError("Only read-only SELECT/WITH queries are allowed")

    normalized = re.sub(r"\s+", " ", text)
    if ";" in normalized.rstrip(";"):
        raise ValueError("Multiple SQL statements are not allowed")

    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", normalized):
            raise ValueError(f"Forbidden SQL operation detected: {keyword}")
