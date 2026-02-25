from __future__ import annotations

from analyst.prompting.example_store import (
    format_examples_for_prompt,
    load_examples,
    retrieve_examples,
)
from analyst.agent import DataAnalystAgent


def test_load_examples_from_repo() -> None:
    examples = load_examples("src/analyst/prompting/examples.json")
    assert len(examples) >= 3


def test_retrieve_examples_prefers_overlap() -> None:
    examples = [
        {"question": "revenue by region", "answer": "a", "code_used": "x"},
        {"question": "salary by department", "answer": "b", "code_used": "y"},
    ]
    selected = retrieve_examples("show revenue trends", examples, k=1)
    assert selected[0]["question"] == "revenue by region"


def test_format_examples_for_prompt() -> None:
    text = format_examples_for_prompt(
        [{"question": "q1", "answer": "a1", "code_used": "c1"}]
    )
    assert "Reference examples" in text
    assert "q1" in text


def test_agent_prompt_uses_structured_sections() -> None:
    agent = DataAnalystAgent(data_dir="data", model_candidates=["mock:model"])
    prompt = agent._build_prompt("What is total revenue?")
    assert "<prompt_meta>" in prompt
    assert "<current_question>" in prompt
