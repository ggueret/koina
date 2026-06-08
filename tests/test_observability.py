from pydantic import TypeAdapter

from koina.observability import (
    Event,
    JsonlSink,
    ModelResponse,
    NullSink,
    Thinking,
    ToolEnd,
    ToolStart,
    Usage,
)


class ListSink:
    """In-memory sink for assertions (reused by dispatch tests)."""

    def __init__(self):
        self.events = []

    def emit(self, event):
        self.events.append(event)


def test_event_has_auto_id_and_ts():
    a = ToolStart(tool="Read", tool_call_id="c1", input={})
    b = ToolStart(tool="Read", tool_call_id="c1", input={})
    assert a.id != b.id
    assert a.ts > 0
    assert a.turn is None and a.parent_id is None


def test_discriminated_roundtrip():
    adapter = TypeAdapter(Event)
    samples = [
        ToolStart(tool="Read", tool_call_id="c1", input={"x": 1}),
        ToolEnd(
            tool="Read",
            tool_call_id="c1",
            duration_ms=1.0,
            is_error=False,
            output_bytes=3,
        ),
        ModelResponse(response_id="m1", model="claude-opus-4-8"),
        Thinking(thinking="hmm"),
        Usage(input_tokens=10, output_tokens=5),
    ]
    for ev in samples:
        back = adapter.validate_json(ev.model_dump_json())
        assert type(back) is type(ev)
        assert back.id == ev.id


def test_null_sink_is_noop():
    assert NullSink().emit(Usage(input_tokens=1, output_tokens=1)) is None


def test_jsonl_sink_writes_lines(tmp_path):
    path = tmp_path / "log.jsonl"
    sink = JsonlSink(path)
    sink.emit(ToolStart(tool="Read", tool_call_id="c1", input={}))
    sink.emit(Usage(input_tokens=2, output_tokens=3))
    # line-buffered: readable before close
    lines = path.read_text().splitlines()
    assert len(lines) == 2
    sink.close()
    assert isinstance(TypeAdapter(Event).validate_json(lines[0]), ToolStart)


def test_jsonl_sink_emit_is_infallible_after_close(tmp_path):
    sink = JsonlSink(tmp_path / "log.jsonl")
    sink.close()
    sink.emit(Usage(input_tokens=1, output_tokens=1))  # must not raise


def test_tool_context_defaults_to_null_sink():
    from pathlib import Path

    from koina.context import ToolContext
    from koina.observability import NullSink

    ctx = ToolContext(cwd=Path.cwd())
    assert isinstance(ctx.events, NullSink)
