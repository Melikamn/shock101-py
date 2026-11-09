# shock101-py — Echo Lite

A tiny tool-using Agent CLI implemented with the Python standard library. It includes a safe arithmetic parser, a word counter, a UTC clock tool, a deterministic `FakeModel`, and JSONL run logs.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv sync
```

## Run

```bash
uv run python -m echo_lite "what is 12*7 and the time in UTC?"
```

The deterministic fake model calls `calc` and `utc_now`, then prints a final answer containing `84` and the current UTC timestamp. Run logs are written to `runs/`.

## Test

```bash
uv run pytest
```

## Public API

```python
from echo_lite.tools import REGISTRY, tool, ToolError, dispatch
from echo_lite.agent import Message, run
```

`calc` supports numbers, `+`, `-`, `*`, `/`, parentheses, and unary signs. It uses tokenization and recursive descent; it never executes Python expressions.
