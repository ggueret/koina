from dataclasses import dataclass


@dataclass
class ToolCall:
    """A request to run a tool, decoded from a provider response.

    `input` is the raw argument mapping; `dispatch` validates it against the
    tool's `Input` model.
    """

    id: str
    name: str
    input: dict[str, object]


@dataclass
class ToolResult:
    """The outcome of a tool call, ready to be formatted back for a provider.

    `content` is the rendered, provider-neutral text; `is_error` marks a failure
    (an adapter may decorate error content for its provider).
    """

    id: str
    # name is carried for adapters that format results by function name
    # (e.g. Gemini's functionResponse); the Anthropic adapter matches by id only.
    name: str
    content: str
    is_error: bool = False
