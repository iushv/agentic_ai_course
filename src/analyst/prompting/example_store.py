"""Dynamic few-shot example retrieval for prompt grounding."""

from __future__ import annotations

import json
from pathlib import Path
import re


def load_examples(path: str | Path) -> list[dict]:
    payload = json.loads(Path(path).read_text())
    if not isinstance(payload, list):
        raise ValueError("Examples file must be a JSON list")
    return payload


def retrieve_examples(question: str, examples: list[dict], k: int = 2) -> list[dict]:
    """Retrieve top-k examples by token-overlap score."""
    q_tokens = _tokens(question)
    if not q_tokens:
        return examples[:k]

    scored = []
    for item in examples:
        source = f"{item.get('question', '')} {item.get('answer', '')}"
        tokens = _tokens(source)
        overlap = len(q_tokens.intersection(tokens))
        scored.append((overlap, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for score, item in scored if score > 0][:k] or examples[:k]


def format_examples_for_prompt(examples: list[dict]) -> str:
    if not examples:
        return ""
    lines = ["Reference examples (style + approach):"]
    for i, ex in enumerate(examples, 1):
        lines.append(f"Example {i} question: {ex.get('question', '')}")
        lines.append(f"Example {i} answer: {ex.get('answer', '')}")
        lines.append(f"Example {i} code: {ex.get('code_used', '')}")
        lines.append("")
    return "\n".join(lines).strip()


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if len(t) > 2}
