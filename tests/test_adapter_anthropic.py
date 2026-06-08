from types import SimpleNamespace

from koina import default_registry
from koina.adapters import anthropic
from koina.calls import ToolResult


def test_tools_param_shape():
    params = anthropic.tools_param(default_registry())
    names = {p["name"] for p in params}
    assert names == {"Read", "Write", "Edit", "Bash", "Glob", "Grep"}
    read = next(p for p in params if p["name"] == "Read")
    assert "input_schema" in read
    assert read["input_schema"]["type"] == "object"


def test_parse_tool_calls_from_blocks():
    content = [
        SimpleNamespace(type="text", text="thinking"),
        SimpleNamespace(type="tool_use", id="c1", name="Read", input={"file_path": "/x"}),
    ]
    calls = anthropic.parse_tool_calls(content)
    assert len(calls) == 1
    assert calls[0].id == "c1"
    assert calls[0].name == "Read"
    assert calls[0].input == {"file_path": "/x"}


def test_format_results_builds_user_message():
    msg = anthropic.format_results(
        [
            ToolResult(id="c1", name="Read", content="ok"),
            ToolResult(id="c2", name="Bash", content="boom", is_error=True),
        ]
    )
    assert msg["role"] == "user"
    blocks = msg["content"]
    assert blocks[0] == {"type": "tool_result", "tool_use_id": "c1", "content": "ok"}
    assert blocks[1]["is_error"] is True
    assert blocks[1]["tool_use_id"] == "c2"


def test_usage_event_maps_to_neutral_fields():
    resp = SimpleNamespace(
        id="msg_1",
        usage=SimpleNamespace(
            input_tokens=100,
            output_tokens=20,
            cache_creation_input_tokens=10,
            cache_read_input_tokens=5,
        ),
    )
    ev = anthropic.usage_event(resp, turn=2)
    assert ev.type == "usage"
    assert ev.input_tokens == 100
    assert ev.output_tokens == 20
    assert ev.cached_input_tokens == 5
    assert ev.reasoning_tokens == 0
    assert ev.extra == {"cache_creation_input_tokens": 10}
    assert ev.response_id == "msg_1"
    assert ev.turn == 2


def test_usage_event_normalizes_missing_cache():
    resp = SimpleNamespace(
        id="msg_2",
        usage=SimpleNamespace(
            input_tokens=1,
            output_tokens=1,
            cache_creation_input_tokens=None,
            cache_read_input_tokens=None,
        ),
    )
    ev = anthropic.usage_event(resp)
    assert ev.cached_input_tokens == 0
    assert ev.extra == {}


def test_thinking_events_extracts_blocks():
    content = [
        SimpleNamespace(type="text", text="visible"),
        SimpleNamespace(type="thinking", thinking="reasoning", signature="sig"),
        SimpleNamespace(type="redacted_thinking", data="zzz"),
    ]
    evs = anthropic.thinking_events(content, turn=1, parent_id="p1")
    assert len(evs) == 2
    assert evs[0].thinking == "reasoning"
    assert evs[0].extra == {"signature": "sig"}
    assert evs[0].redacted is False
    assert evs[0].turn == 1 and evs[0].parent_id == "p1"
    assert evs[1].redacted is True
    assert evs[1].thinking == ""


def test_thinking_events_empty_when_no_thinking():
    assert anthropic.thinking_events([SimpleNamespace(type="text", text="hi")]) == []
