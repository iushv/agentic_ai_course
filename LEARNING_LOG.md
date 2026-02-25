# Learning Log

## Current State

- Core agent wiring exists with structured outputs and tool calling.
- Local subprocess code execution is implemented for iterative analysis.
- Docker sandbox and E2B adapter interfaces are present.
- Evaluation harness and tracing utilities are implemented.

## Key Concepts to Internalize

1. Agent = model + tools + state + loop constraints
2. Tool schemas are contracts, not hints
3. Sandboxing and safety checks are mandatory for generated code
4. Eval-first iteration is the only scalable way to improve reliability
5. Cost and latency are product constraints, not post-hoc metrics

## Practical Gaps to Keep Closing

- Add richer deterministic eval sets (`src/analyst/evaluation/datasets/`)
- Add API auth and tenant-aware quotas before any external deployment
- Expand regression tests around fallback and retry paths
- Integrate first-class Logfire/Langfuse exporters
