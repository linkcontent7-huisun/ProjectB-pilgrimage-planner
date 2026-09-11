"""Small, transport-neutral event constructors for SSE consumers."""

from collections.abc import Callable
from typing import Any

Emit = Callable[[dict], None]


def status(stage: str, message: str) -> dict:
    return {"event": "status", "data": {"stage": stage, "message": message}}


def log_thinking(msg: str) -> dict:
    return {"event": "log", "data": {"kind": "thinking", "message": msg}}


def log_tool_call(tool: str, args: dict[str, Any]) -> dict:
    return {"event": "log", "data": {"kind": "tool_call", "tool": tool, "args": args}}


def log_tool_output(tool: str, summary: str) -> dict:
    return {"event": "log", "data": {"kind": "tool_output", "tool": tool, "summary": summary}}


def log_decision(msg: str) -> dict:
    return {"event": "log", "data": {"kind": "decision", "message": msg}}


def result(plan: dict) -> dict:
    return {"event": "result", "data": plan}


def error(msg: str) -> dict:
    return {"event": "error", "data": {"message": msg}}
