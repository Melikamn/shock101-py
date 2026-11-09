"""Tests for the public Echo Lite API."""

import json
from pathlib import Path

import pytest

from echo_lite.agent import Message, run
from echo_lite.tools import REGISTRY, ToolError, calc, dispatch, tool, utc_now, word_count


@pytest.mark.parametrize(
    ("expression", "expected"),
    [("2+3*4", "14"), ("10/4", "2.5"), ("8/4", "2"), ("-(2+3)", "-5"), ("(2+3)*4", "20")],
)
def test_calc(expression: str, expected: str) -> None:
    assert REGISTRY["calc"](expression) == expected


@pytest.mark.parametrize(("text", "expected"), [("سلام دنیا hello", "3"), ("", "0"), ("one\ntwo  three", "3")])
def test_word_count(text: str, expected: str) -> None:
    assert REGISTRY["word_count"](text) == expected


def test_utc_now_format() -> None:
    value = utc_now("")
    assert value.endswith("Z")
    assert len(value) == 20


@pytest.mark.parametrize("expression", ["1/0", "__import__('os')", "2+", "1..2", "abc"])
def test_calc_rejects_invalid_input(expression: str) -> None:
    with pytest.raises(ToolError):
        calc(expression)


def test_dispatch_unknown_tool() -> None:
    with pytest.raises(ToolError):
        dispatch("missing", "x")


def test_tool_decorator_registers_and_returns_function() -> None:
    @tool
    def sample_tool(value: str) -> str:
        return value.upper()

    assert REGISTRY["sample_tool"] is sample_tool
    assert dispatch("sample_tool", "hello") == "HELLO"
    REGISTRY.pop("sample_tool")


class ScriptedModel:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.seen: list[list[Message]] = []

    def __call__(self, messages: list[Message]) -> str:
        self.seen.append(list(messages))
        return self.responses.pop(0)


@pytest.fixture
def scripted_model() -> ScriptedModel:
    return ScriptedModel([json.dumps({"tool": "calc", "arg": "12*7"}), json.dumps({"final": "84"})])


def test_run_tool_flow_and_message_contract(tmp_path: Path, scripted_model: ScriptedModel) -> None:
    assert run("calculate 12*7", model=scripted_model, log_dir=tmp_path) == "84"
    assert scripted_model.seen[0][0] == Message("user", "calculate 12*7")
    assert scripted_model.seen[1][-1] == Message("tool", "84")


def test_run_fake_model_calculation_and_utc(tmp_path: Path) -> None:
    answer = run("what is 12*7 and the time in UTC?", log_dir=tmp_path)
    assert "84" in answer
    assert "UTC time:" in answer


def test_run_creates_fresh_jsonl_log(tmp_path: Path) -> None:
    run("hello", log_dir=tmp_path)
    run("hello again", log_dir=tmp_path)
    logs = sorted(tmp_path.glob("*.jsonl"))
    assert len(logs) == 2
    rows = [json.loads(line) for line in logs[0].read_text(encoding="utf-8").splitlines()]
    assert rows
    assert all("step" in row and "type" in row for row in rows)


def test_run_invalid_json_raises_tool_error(tmp_path: Path) -> None:
    with pytest.raises(ToolError):
        run("task", model=ScriptedModel(["not json"]), log_dir=tmp_path)


def test_run_max_steps_raises_tool_error(tmp_path: Path) -> None:
    model = ScriptedModel([json.dumps({"tool": "calc", "arg": "1+1"})])
    with pytest.raises(ToolError):
        run("task", model=model, max_steps=1, log_dir=tmp_path)
