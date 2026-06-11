from pydantic import BaseModel, ConfigDict

from koina.tool import Tool


class _EchoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str


class _Echo(Tool[_EchoInput, str]):
    name = "Echo"
    description = "Echoes text."
    Input = _EchoInput

    async def run(self, input, ctx):
        return input.text

    def render_result(self, output):
        return output


def test_input_json_schema_shape():
    schema = _Echo.input_json_schema()
    assert schema["type"] == "object"
    assert "text" in schema["properties"]
    assert schema["additionalProperties"] is False


def test_observability_symbols_exported():
    import koina

    for name in [
        "EventSink",
        "NullSink",
        "JsonlSink",
        "ToolStart",
        "ToolEnd",
        "ModelResponse",
        "Thinking",
        "Usage",
    ]:
        assert name in koina.__all__
        assert hasattr(koina, name)
