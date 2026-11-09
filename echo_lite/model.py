"""Deterministic rule-based model used for offline demonstrations."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from echo_lite.agent import Message


class FakeModel:
    """A tiny scripted model that requests arithmetic and/or UTC tools."""

    def __call__(self, messages: list[Message]) -> str:
        task = messages[0].content if messages else ""
        tool_messages = [message.content for message in messages if message.role == "tool"]
        lower = task.lower()
        wants_calc = bool(re.search(r"\d\s*[+*/-]\s*\d|\([^)]*[+*/-][^)]*\)", task))
        wants_time = "utc" in lower or "time" in lower

        if wants_calc and len(tool_messages) == 0:
            return json.dumps({"tool": "calc", "arg": self._extract_expression(task)})
        if wants_time and len(tool_messages) == int(wants_calc):
            return json.dumps({"tool": "utc_now", "arg": ""})
        if wants_calc and wants_time:
            return json.dumps({"final": f"{self._extract_expression(task)} = {tool_messages[0]}; UTC time: {tool_messages[1]}"})
        if wants_calc:
            return json.dumps({"final": f"{self._extract_expression(task)} = {tool_messages[0]}"})
        if wants_time:
            return json.dumps({"final": f"UTC time: {tool_messages[0]}"})
        return json.dumps({"final": "I can help with arithmetic or the current UTC time."})

    @staticmethod
    def _extract_expression(task: str) -> str:
        match = re.search(r"(?<![\w.])\(?\s*-?\d+(?:\.\d+)?(?:\s*[+*/-]\s*-?\d+(?:\.\d+)?|\s*\([^)]*\))*\s*\)?", task)
        if match is None:
            raise ValueError("no arithmetic expression found")
        return match.group(0).strip()
