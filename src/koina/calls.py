from dataclasses import dataclass


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict[str, object]


@dataclass
class ToolResult:
    id: str
    # name is carried for adapters that format results by function name
    # (e.g. Gemini's functionResponse); the Anthropic adapter matches by id only.
    name: str
    content: str
    is_error: bool = False
