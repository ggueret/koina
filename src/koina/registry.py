import time

from pydantic import ValidationError

from .calls import ToolCall, ToolResult
from .context import ToolContext
from .observability import Event, ToolEnd, ToolStart
from .tool import Tool, ToolError


class ToolRegistry:
    def __init__(self, tools: tuple[Tool, ...] | list[Tool] = ()) -> None:
        self._by_name: dict[str, Tool] = {}
        for tool in tools:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        self._by_name[tool.name] = tool
        for alias in tool.aliases:
            self._by_name[alias] = tool

    def get(self, name: str) -> Tool | None:
        return self._by_name.get(name)

    def tools(self) -> list[Tool]:
        unique: dict[str, Tool] = {}
        for tool in self._by_name.values():
            unique[tool.name] = tool
        return list(unique.values())


def _error(call: ToolCall, message: str) -> ToolResult:
    return ToolResult(
        id=call.id,
        name=call.name,
        content=f"<tool_use_error>{message}</tool_use_error>",
        is_error=True,
    )


async def _execute(
    call: ToolCall, registry: ToolRegistry, ctx: ToolContext
) -> ToolResult:
    tool = registry.get(call.name)
    if tool is None:
        return _error(call, f"No such tool available: {call.name}")
    try:
        parsed = tool.Input.model_validate(call.input)
    except ValidationError as exc:
        return _error(call, f"InputValidationError: {exc}")
    try:
        output = await tool.run(parsed, ctx)
        return ToolResult(
            id=call.id, name=call.name, content=tool.render_result(output)
        )
    except ToolError as exc:
        return _error(call, str(exc))
    except Exception as exc:  # noqa: BLE001 - dispatch must never raise
        return _error(call, f"{type(exc).__name__}: {exc}")


def _safe_emit(ctx: ToolContext, event: Event) -> None:
    try:
        ctx.events.emit(event)
    except Exception:  # noqa: BLE001 - logging is best-effort; never break dispatch
        pass


async def dispatch(
    call: ToolCall, registry: ToolRegistry, ctx: ToolContext
) -> ToolResult:
    start = ToolStart(tool=call.name, tool_call_id=call.id, input=call.input)
    _safe_emit(ctx, start)
    t0 = time.monotonic()
    result = await _execute(call, registry, ctx)
    _safe_emit(
        ctx,
        ToolEnd(
            tool=call.name,
            tool_call_id=call.id,
            duration_ms=(time.monotonic() - t0) * 1000,
            is_error=result.is_error,
            output_bytes=len(result.content.encode("utf-8")),
            parent_id=start.id,
        ),
    )
    return result


def default_registry() -> ToolRegistry:
    from .tools.bash import Bash
    from .tools.edit import Edit
    from .tools.glob import Glob
    from .tools.grep import Grep
    from .tools.read import Read
    from .tools.write import Write

    return ToolRegistry([Read(), Write(), Edit(), Bash(), Glob(), Grep()])
