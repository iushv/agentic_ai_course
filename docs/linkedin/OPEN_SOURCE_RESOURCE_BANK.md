# Open-Source and Free Resource Bank (SOTA Agentic AI)

This list is curated for learners who want to build modern agent systems with free setup paths.

## 1) Core Agent Frameworks

- PydanticAI (typed agent framework): https://ai.pydantic.dev/
- LangGraph (graph-based orchestration): https://docs.langchain.com/oss/python/langgraph/
- AutoGen (multi-agent workflows): https://github.com/microsoft/autogen
- CrewAI (agent crews and tasks): https://docs.crewai.com/
- smolagents (lightweight code agents): https://huggingface.co/docs/smolagents/main/en/index
- DSPy (programming LM pipelines): https://dspy.ai/

## 2) Local and Open Model Runtimes

- LM Studio (local OpenAI-compatible runtime): https://lmstudio.ai/
- Ollama (local model serving): https://ollama.com/
- vLLM (high-throughput open inference server): https://github.com/vllm-project/vllm
- Hugging Face Transformers: https://huggingface.co/docs/transformers/index

## 3) Evaluation and Benchmarking

- promptfoo (open-source eval and red-team): https://github.com/promptfoo/promptfoo
- Langfuse (open-source tracing + eval): https://github.com/langfuse/langfuse
- OpenAI agent eval guide (free docs): https://platform.openai.com/docs/guides/agent-evals
- HELM Lite concept papers and benchmarks: https://crfm.stanford.edu/helm/

## 4) Observability and Debugging

- OpenTelemetry Python: https://opentelemetry.io/docs/languages/python/
- Phoenix OSS (LLM observability): https://phoenix.arize.com/
- Langfuse docs: https://langfuse.com/docs

## 5) Safety and Security

- OWASP Top 10 for LLM Applications: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- Anthropic guardrail guidance: https://docs.anthropic.com/en/docs/test-and-evaluate/strengthen-guardrails/mitigate-jailbreaks
- Python subprocess docs (safe execution concerns): https://docs.python.org/3/library/subprocess.html

## 6) Free Data and Practice Datasets

- Kaggle datasets: https://www.kaggle.com/datasets
- UCI Machine Learning Repository: https://archive.ics.uci.edu/
- data.gov datasets: https://www.data.gov/
- Awesome public datasets: https://github.com/awesomedata/awesome-public-datasets

## 7) Free Hosting and Publishing

- GitHub Pages: https://docs.github.com/pages
- Jupyter in Colab: https://colab.research.google.com/
- Quarto + GitHub Pages (free docs publishing): https://quarto.org/docs/publishing/github-pages.html

## 8) Recommended Learning Order

1. Start with `PydanticAI` or `LangGraph` for control and tracing.
2. Add local model runtime (`LM Studio` or `Ollama`).
3. Build tool calling and structured outputs.
4. Add sandboxed execution.
5. Add eval harness (`promptfoo` + deterministic tests).
6. Add observability (`OpenTelemetry` + `Langfuse`/`Phoenix`).
7. Publish learnings via GitHub Pages.

