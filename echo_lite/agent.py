"""Agent loop, message type, and JSONL execution logs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from echo_lite.tools import ToolError, dispatch


@dataclass
class Message:
    role: str
    content: str


Model = Callable[[list[Message]], str]


def _new_log_path(log_dir: str | Path) -> Path:
    directory = Path(log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    path = directory / f"{stamp}.jsonl"
    suffix = 1
    while path.exists():
        suffix += 1
    path.touch(exist_ok=False)
    return path


def _write_log(path: Path, step: int, event_type: str, **details: str) -> None:
    record: dict[str, object] = {"step": step, "type": event_type, **details}
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def run(
    task: str,
    model: Model | None = None,
    max_steps: int = 5,
    log_dir: str | Path = "runs",
) -> str:
    """Run a tool-calling model for at most ``max_steps`` model calls."""
    if max_steps < 1:
        raise ToolError("max_steps must be at least 1")
    if model is None:
        from echo_lite.model import FakeModel

        model = FakeModel()

    messages = [Message("user", task)]
    log_path = _new_log_path(log_dir)
    for step in range(1, max_steps + 1):
        try:
            raw_response = model(messages)
            _write_log(log_path, step, "model", response=raw_response)
            payload = json.loads(raw_response)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            _write_log(log_path, step, "error", message="invalid model JSON")
            raise ToolError("model returned invalid JSON") from exc
        except Exception as exc:
            _write_log(log_path, step, "error", message="model call failed")
            raise ToolError(f"model call failed: {exc}") from exc

        if not isinstance(payload, dict):
            _write_log(log_path, step, "error", message="response must be a JSON object")
            raise ToolError("model response must be a JSON object")

        if set(payload) == {"final"} and isinstance(payload["final"], str):
            _write_log(log_path, step, "final", content=payload["final"])
            return payload["final"]

        if set(payload) == {"tool", "arg"} and isinstance(payload["tool"], str) and isinstance(payload["arg"], str):
            name = payload["tool"]
            try:
                result = dispatch(name, payload["arg"])
                event_type = "tool"
            except ToolError as exc:
                result = f"ERROR: {exc}"
                event_type = "error"
            _write_log(log_path, step, event_type, tool=name, result=result)
            messages.append(Message("tool", result))
            continue

        _write_log(log_path, step, "error", message="invalid response shape")
        raise ToolError("model response must contain either final or tool and arg")

    _write_log(log_path, max_steps, "error", message="maximum model steps reached")
    raise ToolError("model did not return a final answer within max_steps")
        path = directory / f"{stamp}_{suffix}.jsonl"
