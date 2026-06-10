from typing import Any

from ..calls import ToolCall, ToolResult
from ..observability import Thinking, Usage
from ..registry import ToolRegistry


def tools_param(registry: ToolRegistry) -> list[dict[str, object]]:
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_json_schema(),
        }
        for tool in registry.tools()
    ]


def parse_tool_calls(content: Any) -> list[ToolCall]:
    calls: list[ToolCall] = []
    for block in content:
        if getattr(block, "type", None) == "tool_use":
            calls.append(
                ToolCall(id=block.id, name=block.name, input=dict(block.input))
            )
    return calls


def format_results(results: list[ToolResult]) -> dict[str, object]:
    blocks: list[dict[str, object]] = []
    for r in results:
        block: dict[str, object] = {
            "type": "tool_result",
            "tool_use_id": r.id,
            "content": r.content,
        }
        if r.is_error:
            block["is_error"] = True
        blocks.append(block)
    return {"role": "user", "content": blocks}


def usage_event(
    resp: Any, *, turn: int | None = None, parent_id: str | None = None
) -> Usage:
    u = resp.usage
    cache_read = getattr(u, "cache_read_input_tokens", 0) or 0
    cache_creation = getattr(u, "cache_creation_input_tokens", 0) or 0
    extra: dict[str, int] = {}
    if cache_creation:
        # Anthropic-only counter (cache-write premium); kept out of the neutral
        # fields so the schema does not bias toward one provider.
        extra["cache_creation_input_tokens"] = cache_creation
    return Usage(
        response_id=getattr(resp, "id", None),
        input_tokens=u.input_tokens,
        output_tokens=u.output_tokens,
        cached_input_tokens=cache_read,
        reasoning_tokens=0,  # Anthropic folds thinking into output_tokens
        extra=extra,
        turn=turn,
        parent_id=parent_id,
    )


def thinking_events(
    content: Any, *, turn: int | None = None, parent_id: str | None = None
) -> list[Thinking]:
    events: list[Thinking] = []
    for block in content:
        btype = getattr(block, "type", None)
        if btype == "thinking":
            signature = getattr(block, "signature", None)
            extra: dict[str, object] = {}
            if signature is not None:
                # Anthropic-only thinking-block signature; out of the neutral core.
                extra["signature"] = signature
            events.append(
                Thinking(
                    thinking=getattr(block, "thinking", ""),
                    extra=extra,
                    turn=turn,
                    parent_id=parent_id,
                )
            )
        elif btype == "redacted_thinking":
            events.append(
                Thinking(thinking="", redacted=True, turn=turn, parent_id=parent_id)
            )
    return events
