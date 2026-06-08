"""OpenAI Chat Completions agent loop for the review examples.

Mirrors _agent.run_agent but speaks the Chat Completions shape, so it works
against OpenAI or any OpenAI-compatible server (e.g. llama.cpp). The caller
passes an already-constructed client, so this module never imports `openai` at
top level (keeps the smoke tests importable without the SDK).
"""

import sys
from typing import Any

from koina import ModelResponse, ToolContext, ToolRegistry, dispatch
from koina.adapters import openai as adapter


async def run_agent_openai(
    client: Any,
    model: str,
    system: str,
    initial_user: str,
    registry: ToolRegistry,
    ctx: ToolContext,
    max_turns: int = 20,
) -> str:
    messages: list[dict[str, object]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": initial_user},
    ]
    for turn in range(max_turns):
        use_tools = turn < max_turns - 1
        kwargs: dict = {}
        if use_tools:
            kwargs["tools"] = adapter.tools_param(registry)
        resp = await client.chat.completions.create(
            model=model, messages=messages, **kwargs
        )
        message = resp.choices[0].message
        # Re-append the assistant turn (with any tool_calls) to the history.
        # Rebuilt explicitly so we don't echo reasoning_content back to servers
        # that reject it, and to stay SDK-version-agnostic.
        assistant: dict[str, object] = {"role": "assistant", "content": message.content}
        if getattr(message, "tool_calls", None):
            assistant["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]
        messages.append(assistant)
        calls = adapter.parse_tool_calls(message) if use_tools else []
        mr = ModelResponse(
            turn=turn,
            response_id=resp.id,
            model=resp.model,
            stop_reason=resp.choices[0].finish_reason,
            tool_call_ids=[c.id for c in calls],
        )
        ctx.events.emit(mr)
        ctx.events.emit(adapter.usage_event(resp, turn=turn, parent_id=mr.id))
        for ev in adapter.thinking_events(message, turn=turn, parent_id=mr.id):
            ctx.events.emit(ev)
        if not calls:
            return message.content or ""
        for c in calls:
            print(f"  [tool] {c.name} {c.input}", file=sys.stderr)
        results = [await dispatch(c, registry, ctx) for c in calls]
        messages.extend(adapter.format_results(results))
        if turn == max_turns - 2:
            # The next turn has no tools; tell the model to stop and report now,
            # otherwise it may just emit a transitional sentence when tools vanish.
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "You have reached the exploration limit. Stop using tools "
                        "and write your final report now, based on what you have "
                        "already seen."
                    ),
                }
            )
    return ""
