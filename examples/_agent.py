"""Shared helpers for the review examples: git diff plus the agent loop.

The loop is Anthropic-specific (it uses the Anthropic adapter and client). The
caller passes an already-constructed client so this module never imports anthropic
at top level, which keeps the smoke tests importable without the SDK.
"""

import subprocess
import sys
from pathlib import Path
from typing import Any

from koina import ModelResponse, ToolContext, ToolRegistry, dispatch
from koina.adapters import anthropic as adapter


def compute_diff(base: str, cwd: Path) -> str:
    result = subprocess.run(
        ["git", "diff", f"{base}...HEAD"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def compute_changed_files(base: str, cwd: Path) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


async def run_agent(
    client: Any,
    model: str,
    system: str,
    initial_user: str,
    registry: ToolRegistry,
    ctx: ToolContext,
    max_turns: int = 20,
    thinking: bool = False,
) -> str:
    messages: list[dict[str, object]] = [{"role": "user", "content": initial_user}]
    for turn in range(max_turns):
        use_tools = turn < max_turns - 1
        create_kwargs: dict = {}
        if use_tools:
            create_kwargs["tools"] = adapter.tools_param(registry)
        if thinking:
            # Opus 4.8/4.7: adaptive + summarized so reasoning text is produced
            # and surfaced as Thinking events; default-off keeps cost unchanged.
            create_kwargs["thinking"] = {"type": "adaptive", "display": "summarized"}
        resp = await client.messages.create(
            model=model,
            max_tokens=8192,
            system=system,
            messages=messages,
            **create_kwargs,
        )
        messages.append({"role": "assistant", "content": resp.content})
        calls = adapter.parse_tool_calls(resp.content) if use_tools else []
        mr = ModelResponse(
            turn=turn,
            response_id=resp.id,
            model=resp.model,
            stop_reason=resp.stop_reason,
            tool_call_ids=[c.id for c in calls],
        )
        ctx.events.emit(mr)
        ctx.events.emit(adapter.usage_event(resp, turn=turn, parent_id=mr.id))
        for ev in adapter.thinking_events(resp.content, turn=turn, parent_id=mr.id):
            ctx.events.emit(ev)
        if not calls:
            return "\n".join(b.text for b in resp.content if b.type == "text")
        for c in calls:
            print(f"  [tool] {c.name} {c.input}", file=sys.stderr)
        results = [await dispatch(c, registry, ctx) for c in calls]
        results_msg = adapter.format_results(results)
        if turn == max_turns - 2:
            # The next turn has no tools; tell the model to stop and report now,
            # otherwise it may just emit a transitional sentence when tools vanish.
            blocks = results_msg["content"]
            if isinstance(blocks, list):
                blocks.append(
                    {
                        "type": "text",
                        "text": (
                            "You have reached the exploration limit. Stop using tools and "
                            "write your final report now, based on what you have already seen."
                        ),
                    }
                )
        messages.append(results_msg)
    return ""
