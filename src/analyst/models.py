"""Pydantic models for the Data Analyst Agent.

These models define the exact structure of inputs and outputs
across the entire agent system. The LLM MUST conform to these schemas.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Agent output models — what the LLM returns
# ---------------------------------------------------------------------------


class AnalysisResult(BaseModel):
    """The result of a data analysis query."""

    answer: str = Field(description="Clear, concise answer to the user's question")
    code_used: str = Field(description="The Python/pandas code that produced this answer")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the answer. 1.0 = certain, 0.0 = guessing",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Any assumptions made during analysis",
    )


class DatasetSchema(BaseModel):
    """Schema description of a dataset."""

    name: str = Field(description="Dataset name or filename")
    row_count: int = Field(description="Number of rows")
    columns: list[ColumnInfo] = Field(description="Column descriptions")
    suggested_questions: list[str] = Field(
        description="3-5 interesting questions to ask about this data"
    )


class ColumnInfo(BaseModel):
    """Information about a single column."""

    name: str
    dtype: str = Field(description="Data type: numeric, categorical, datetime, text")
    description: str = Field(description="What this column represents")
    sample_values: list[str] = Field(description="3-5 example values")
    null_count: int = Field(default=0, description="Number of missing values")


# Rebuild DatasetSchema now that ColumnInfo is defined
DatasetSchema.model_rebuild()


class AnalysisPlan(BaseModel):
    """A multi-step plan for complex analysis."""

    question: str = Field(description="The original user question")
    steps: list[AnalysisStep] = Field(description="Ordered steps to answer the question")
    estimated_complexity: int = Field(
        ge=1, le=10, description="1=trivial, 10=very complex"
    )


class AnalysisStep(BaseModel):
    """A single step in an analysis plan."""

    step_number: int
    description: str = Field(description="What this step does")
    code_hint: str = Field(description="Pseudocode or approach for this step")
    depends_on: list[int] = Field(
        default_factory=list,
        description="Step numbers this depends on",
    )


# Rebuild AnalysisPlan now that AnalysisStep is defined
AnalysisPlan.model_rebuild()


class CodeExecutionResult(BaseModel):
    """Result of executing generated code in the sandbox."""

    success: bool
    stdout: str = Field(default="", description="Standard output from code execution")
    stderr: str = Field(default="", description="Standard error output")
    generated_files: list[str] = Field(
        default_factory=list,
        description="Paths to any files generated (charts, CSVs, etc.)",
    )
    execution_time_ms: float = Field(default=0.0)


class VisualizationRequest(BaseModel):
    """Request to create a visualization."""

    chart_type: str = Field(description="bar, line, scatter, pie, heatmap, histogram, box")
    title: str
    x_column: str = Field(description="Column for x-axis")
    y_column: str = Field(description="Column for y-axis")
    group_by: str | None = Field(default=None, description="Optional grouping column")
    description: str = Field(description="What insight this chart should show")
