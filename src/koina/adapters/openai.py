import json
from typing import Any

from ..calls import ToolCall, ToolResult
from ..observability import Thinking, Usage
from ..registry import ToolRegistry


def tools_param(registry: ToolRegistry) -> list[dict[str, object]]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_json_schema(),
            },
        }
        for tool in registry.tools()
    ]


def parse_tool_calls(message: Any) -> list[ToolCall]:
    calls: list[ToolCall] = []
    for tc in getattr(message, "tool_calls", None) or []:
        fn = tc.function
        try:
            args = json.loads(fn.arguments or "{}")
        except (ValueError, TypeError):
            args = {}
        if not isinstance(args, dict):
            args = {}
        calls.append(ToolCall(id=tc.id, name=fn.name, input=args))
    return calls


def format_results(results: list[ToolResult]) -> list[dict[str, object]]:
    return [
        {"role": "tool", "tool_call_id": r.id, "content": r.content}
        for r in results
    ]


def usage_event(
    resp: Any, *, turn: int | None = None, parent_id: str | None = None
) -> Usage:
    u = resp.usage
    prompt_details = getattr(u, "prompt_tokens_details", None)
    completion_details = getattr(u, "completion_tokens_details", None)
    cached = getattr(prompt_details, "cached_tokens", 0) or 0
    reasoning = getattr(completion_details, "reasoning_tokens", 0) or 0
    return Usage(
        response_id=getattr(resp, "id", None),
        input_tokens=u.prompt_tokens,
        output_tokens=u.completion_tokens,
        cached_input_tokens=cached,
        reasoning_tokens=reasoning,
        turn=turn,
        parent_id=parent_id,
    )


def thinking_events(
    message: Any, *, turn: int | None = None, parent_id: str | None = None
) -> list[Thinking]:
    reasoning = getattr(message, "reasoning_content", None)
    if not reasoning:
        return []
    return [Thinking(thinking=reasoning, turn=turn, parent_id=parent_id)]
