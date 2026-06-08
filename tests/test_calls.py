from koina.calls import ToolCall, ToolResult


def test_tool_call_fields():
    c = ToolCall(id="t1", name="Read", input={"file_path": "/x"})
    assert c.id == "t1"
    assert c.name == "Read"
    assert c.input == {"file_path": "/x"}


def test_tool_result_defaults_not_error():
    r = ToolResult(id="t1", name="Read", content="ok")
    assert r.is_error is False


def test_tool_result_error_flag():
    r = ToolResult(id="t1", name="Read", content="boom", is_error=True)
    assert r.is_error is True
