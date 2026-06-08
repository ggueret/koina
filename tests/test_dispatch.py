from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict

from koina.calls import ToolCall
from koina.context import ToolContext
from koina.registry import ToolRegistry, dispatch
from koina.tool import Tool, ToolError


class _AddInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    a: int
    b: int


class _Add(Tool):
    name = "Add"
    aliases = ("Sum",)
    description = "Adds two ints."
    Input = _AddInput

    async def run(self, input, ctx):
        if input.a < 0:
            raise ToolError("a must be non-negative")
        return input.a + input.b

    def render_result(self, output):
        return str(output)


def _call(name, inp, id="t1"):
    return ToolCall(id=id, name=name, input=inp)


@pytest.fixture
def ctx():
    return ToolContext(cwd=Path.cwd())


@pytest.fixture
def reg():
    return ToolRegistry([_Add()])


async def test_success(reg, ctx):
    r = await dispatch(_call("Add", {"a": 2, "b": 3}), reg, ctx)
    assert r.content == "5"
    assert r.is_error is False
    assert r.id == "t1"
    assert r.name == "Add"


async def test_alias_lookup(reg, ctx):
    r = await dispatch(_call("Sum", {"a": 1, "b": 1}), reg, ctx)
    assert r.content == "2"
    assert r.name == "Sum"


async def test_unknown_tool(reg, ctx):
    r = await dispatch(_call("Nope", {}), reg, ctx)
    assert r.is_error is True
    assert "No such tool available: Nope" in r.content
    assert r.name == "Nope"


async def test_validation_error(reg, ctx):
    r = await dispatch(_call("Add", {"a": "x", "b": 3}), reg, ctx)
    assert r.is_error is True
    assert "InputValidationError" in r.content


async def test_tool_error(reg, ctx):
    r = await dispatch(_call("Add", {"a": -1, "b": 3}), reg, ctx)
    assert r.is_error is True
    assert "a must be non-negative" in r.content


def test_registry_tools_dedupes_aliases(reg):
    assert [t.name for t in reg.tools()] == ["Add"]


class _ListSink:
    def __init__(self):
        self.events = []

    def emit(self, event):
        self.events.append(event)


async def test_dispatch_emits_start_then_end(reg):
    sink = _ListSink()
    ctx = ToolContext(cwd=Path.cwd(), events=sink)
    await dispatch(_call("Add", {"a": 2, "b": 3}), reg, ctx)
    assert [e.type for e in sink.events] == ["tool_start", "tool_end"]
    start, end = sink.events
    assert start.tool == "Add"
    assert start.tool_call_id == "t1"
    assert start.input == {"a": 2, "b": 3}
    assert end.is_error is False
    assert end.output_bytes == len(b"5")
    assert end.parent_id == start.id
    assert end.duration_ms >= 0


async def test_dispatch_emits_end_error_for_unknown_tool(reg):
    sink = _ListSink()
    ctx = ToolContext(cwd=Path.cwd(), events=sink)
    await dispatch(_call("Nope", {}), reg, ctx)
    assert [e.type for e in sink.events] == ["tool_start", "tool_end"]
    assert sink.events[1].is_error is True


class _RaisingSink:
    def emit(self, event):
        raise RuntimeError("sink is broken")


async def test_dispatch_survives_a_raising_sink(reg):
    # A third-party sink that raises must not break the never-raise guarantee.
    ctx = ToolContext(cwd=Path.cwd(), events=_RaisingSink())
    r = await dispatch(_call("Add", {"a": 1, "b": 1}), reg, ctx)
    assert r.content == "2"
    assert r.is_error is False
