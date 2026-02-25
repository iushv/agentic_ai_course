# Google Colab Run Code for the `.ipynb` Learning Path

This guide gives copy-paste Colab cells so learners can execute and understand notebook-based agent workflows.

## What this enables

- Run notebooks in Colab with minimal setup
- Use a free/open-source local model server path
- Keep compatibility with `openai:local-model` in the notebooks

## 0) Open notebook in Colab

Use this pattern:

`https://colab.research.google.com/github/iushv/agentic_ai_course/blob/main/notebooks/<notebook-name>.ipynb`

Examples:

- `https://colab.research.google.com/github/iushv/agentic_ai_course/blob/main/notebooks/01_foundations.ipynb`
- `https://colab.research.google.com/github/iushv/agentic_ai_course/blob/main/notebooks/02_tool_calling.ipynb`
- `https://colab.research.google.com/github/iushv/agentic_ai_course/blob/main/notebooks/03_code_gen_exec.ipynb`

## 1) Colab setup cell (install packages)

Run this in the first cell of Colab:

```python
%%capture
!pip -q install -U pip
!pip -q install \
  pydantic-ai \
  pydantic-ai-litellm \
  pydantic \
  pandas matplotlib plotly duckdb \
  python-dotenv rich tabulate \
  jupyter nbconvert nest_asyncio \
  "llama-cpp-python[server]"
```

## 2) Clone repo in Colab

```python
!git clone https://github.com/iushv/agentic_ai_course.git /content/agentic_ai_course
%cd /content/agentic_ai_course
```

## 3) Start a free open-source local model server (OpenAI-compatible)

This uses a small GGUF model and exposes an OpenAI-compatible endpoint in Colab.

```python
import os
import time
import subprocess

MODEL_URL = "https://huggingface.co/bartowski/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/Qwen2.5-0.5B-Instruct-Q4_K_M.gguf"
MODEL_PATH = "/content/local-model.gguf"

if not os.path.exists(MODEL_PATH):
    !wget -q -O /content/local-model.gguf "$MODEL_URL"

server_process = subprocess.Popen(
    [
        "python", "-m", "llama_cpp.server",
        "--model", MODEL_PATH,
        "--model_alias", "local-model",
        "--host", "127.0.0.1",
        "--port", "8000",
        "--n_ctx", "4096",
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)

time.sleep(20)
print("Local OpenAI-compatible server started on http://127.0.0.1:8000/v1")
```

## 4) Configure environment variables for notebooks

```python
import os
import nest_asyncio

nest_asyncio.apply()

os.environ["OPENAI_BASE_URL"] = "http://127.0.0.1:8000/v1"
os.environ["OPENAI_API_KEY"] = "local-dev"
os.environ["LMSTUDIO_BASE_URL"] = "http://127.0.0.1:8000"
os.environ["LMSTUDIO_MODEL"] = "local-model"
os.environ["ANALYST_PRIMARY_MODEL"] = "openai:local-model"
os.environ["ANALYST_EXECUTION_BACKEND"] = "subprocess"
os.environ["ANALYST_ALLOW_UNSAFE_SUBPROCESS"] = "1"  # Colab-only learning mode

print("Colab env configured.")
```

## 5) Quick smoke test

```python
from pydantic_ai import Agent

agent = Agent(
    "openai:local-model",
    system_prompt="Reply with exactly 5 words.",
    retries=2,
)

result = agent.run_sync("Test connection")
print(result.output)
```

## 6) Execute a notebook end-to-end (optional)

```python
!jupyter nbconvert \
  --to notebook \
  --execute notebooks/01_foundations.ipynb \
  --output 01_foundations.executed.ipynb \
  --output-dir /content \
  --ExecutePreprocessor.timeout=1200
```

## 7) Troubleshooting

- If schema validation fails with tiny local model:
  - rerun the cell
  - reduce strictness in the lesson cell
  - use a stronger open model in the server
- If execution is slow:
  - switch Colab runtime to GPU
  - run one notebook at a time
- If `llama-cpp-python` build fails:
  - restart runtime and rerun install cell
  - or use a hosted OpenAI-compatible endpoint temporarily

## 8) Safety note

For Colab learning only, subprocess mode is enabled:

- `ANALYST_EXECUTION_BACKEND=subprocess`
- `ANALYST_ALLOW_UNSAFE_SUBPROCESS=1`

For production/shared environments, use isolated sandbox execution instead.

