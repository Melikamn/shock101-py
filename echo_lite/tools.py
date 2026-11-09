"""Safe, string-in/string-out tools for Echo Lite."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import wraps
from typing import Callable, TypeVar


class ToolError(Exception):
    """Raised when a tool is unknown or cannot process its input."""


Tool = Callable[[str], str]
F = TypeVar("F", bound=Tool)
REGISTRY: dict[str, Tool] = {}


def tool(fn: F) -> F:
    """Register a tool under its function name and return the function."""
    REGISTRY[fn.__name__] = fn
    return fn


class _CalcParser:
    """Recursive-descent parser for a deliberately small arithmetic grammar."""

    def __init__(self, source: str) -> None:
        self.tokens: list[str] = []
        self.position = 0
        self._tokenize(source)

    def _tokenize(self, source: str) -> None:
        index = 0
        while index < len(source):
            char = source[index]
            if char.isspace():
                index += 1
                continue
            if char in "+-*/()":
                self.tokens.append(char)
                index += 1
                continue
            if char.isdigit() or char == ".":
                start = index
                dots = 0
                while index < len(source) and (source[index].isdigit() or source[index] == "."):
                    if source[index] == ".":
                        dots += 1
                    index += 1
                token = source[start:index]
                if dots > 1 or token == ".":
                    raise ToolError("invalid number")
                self.tokens.append(token)
                continue
            raise ToolError("invalid character in expression")
        if not self.tokens:
            raise ToolError("empty expression")

    def _peek(self) -> str | None:
        if self.position >= len(self.tokens):
            return None
        return self.tokens[self.position]

    def _take(self) -> str:
        token = self._peek()
        if token is None:
            raise ToolError("unexpected end of expression")
        self.position += 1
        return token

    def parse(self) -> int | float:
        value = self._expr()
        if self._peek() is not None:
            raise ToolError("unexpected token")
        return value

    def _expr(self) -> int | float:
        value = self._term()
        while self._peek() in ("+", "-"):
            operator = self._take()
            right = self._term()
            value = value + right if operator == "+" else value - right
        return value

    def _term(self) -> int | float:
        value = self._factor()
        while self._peek() in ("*", "/"):
            operator = self._take()
            right = self._factor()
            if operator == "/" and right == 0:
                raise ToolError("division by zero")
            value = value * right if operator == "*" else value / right
        return value

    def _factor(self) -> int | float:
        token = self._peek()
        if token == "-":
            self._take()
            return -self._factor()
        if token == "+":
            self._take()
            return self._factor()
        if token == "(":
            self._take()
            value = self._expr()
            if self._take() != ")":
                raise ToolError("missing closing parenthesis")
            return value
        if token is None:
            raise ToolError("expected a number")
        self._take()
        try:
            return float(token) if "." in token else int(token)
        except ValueError as exc:
            raise ToolError("invalid number") from exc


@tool
def calc(expression: str) -> str:
    """Evaluate basic arithmetic without executing Python code."""
    try:
        result = _CalcParser(expression).parse()
    except (OverflowError, RecursionError) as exc:
        raise ToolError("expression is too complex") from exc
    if isinstance(result, float) and result.is_integer():
        return str(int(result))
    return str(result)


@tool
def word_count(text: str) -> str:
    """Return the number of whitespace-separated words."""
    return str(len(text.split()))


@tool
def utc_now(_: str) -> str:
    """Return the current UTC time in ISO-8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def dispatch(name: str, arg: str) -> str:
    """Run a registered tool and normalize failures to ToolError."""
    if name not in REGISTRY:
        raise ToolError(f"unknown tool: {name}")
    try:
        result = REGISTRY[name](arg)
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(f"tool {name} failed: {exc}") from exc
    if not isinstance(result, str):
        raise ToolError(f"tool {name} returned a non-string result")
    return result
