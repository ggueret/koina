from types import SimpleNamespace

from koina import default_registry
from koina.adapters import openai
from koina.calls import ToolResult


def _tc(id, name, arguments):
    return SimpleNamespace(
        id=id,
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def test_tools_param_openai_shape():
    params = openai.tools_param(default_registry())
    names = {p["function"]["name"] for p in params}
    assert names == {"Read", "Write", "Edit", "Bash", "Glob", "Grep"}
    read = next(p for p in params if p["function"]["name"] == "Read")
    assert read["type"] == "function"
    assert read["function"]["parameters"]["type"] == "object"


def test_parse_tool_calls_decodes_json_arguments():
    message = SimpleNamespace(tool_calls=[_tc("call_1", "add", '{"a": 12, "b": 30}')])
    calls = openai.parse_tool_calls(message)
    assert len(calls) == 1
    assert calls[0].id == "call_1"
    assert calls[0].name == "add"
    assert calls[0].input == {"a": 12, "b": 30}


def test_parse_tool_calls_empty_when_no_tool_calls():
    assert openai.parse_tool_calls(SimpleNamespace(content="hi", tool_calls=None)) == []


def test_parse_tool_calls_survives_malformed_arguments():
    calls = openai.parse_tool_calls(
        SimpleNamespace(tool_calls=[_tc("c", "add", "{not json")])
    )
    assert calls[0].input == {}


def test_format_results_builds_tool_messages():
    msgs = openai.format_results(
        [
            ToolResult(id="c1", name="Read", content="ok"),
            ToolResult(id="c2", name="Bash", content="boom", is_error=True),
        ]
    )
    assert msgs == [
        {"role": "tool", "tool_call_id": "c1", "content": "ok"},
        {"role": "tool", "tool_call_id": "c2", "content": "boom"},
    ]


def test_usage_event_maps_openai_usage_without_details():
    # Shape from a real llama.cpp probe: only prompt/completion/total.
    resp = SimpleNamespace(
        id="chatcmpl-1",
        usage=SimpleNamespace(
            prompt_tokens=174, completion_tokens=64, total_tokens=238
        ),
    )
    ev = openai.usage_event(resp, turn=0)
    assert ev.type == "usage"
    assert ev.input_tokens == 174
    assert ev.output_tokens == 64
    assert ev.cached_input_tokens == 0
    assert ev.reasoning_tokens == 0
    assert ev.extra == {}
    assert ev.response_id == "chatcmpl-1"
    assert ev.turn == 0


def test_usage_event_reads_details_when_present():
    resp = SimpleNamespace(
        id="r",
        usage=SimpleNamespace(
            prompt_tokens=100,
            completion_tokens=50,
            prompt_tokens_details=SimpleNamespace(cached_tokens=30),
            completion_tokens_details=SimpleNamespace(reasoning_tokens=20),
        ),
    )
    ev = openai.usage_event(resp)
    assert ev.cached_input_tokens == 30
    assert ev.reasoning_tokens == 20


def test_thinking_events_from_reasoning_content():
    message = SimpleNamespace(
        reasoning_content="The user is asking me to add 12 and 30."
    )
    evs = openai.thinking_events(message, turn=1, parent_id="p1")
    assert len(evs) == 1
    assert evs[0].thinking == "The user is asking me to add 12 and 30."
    assert evs[0].redacted is False
    assert evs[0].extra == {}
    assert evs[0].turn == 1 and evs[0].parent_id == "p1"


def test_thinking_events_empty_when_no_reasoning():
    assert (
        openai.thinking_events(SimpleNamespace(content="hi", reasoning_content=None))
        == []
    )
    assert (
        openai.thinking_events(SimpleNamespace(content="hi", reasoning_content=""))
        == []
    )
