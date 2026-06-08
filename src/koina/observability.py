import time
import uuid
from pathlib import Path
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, Field


class _Event(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    ts: float = Field(default_factory=time.time)
    turn: int | None = None
    parent_id: str | None = None


class ToolStart(_Event):
    type: Literal["tool_start"] = "tool_start"
    tool: str
    tool_call_id: str
    input: dict[str, object]


class ToolEnd(_Event):
    type: Literal["tool_end"] = "tool_end"
    tool: str
    tool_call_id: str
    duration_ms: float
    is_error: bool
    output_bytes: int


class ModelResponse(_Event):
    type: Literal["model_response"] = "model_response"
    response_id: str
    model: str
    stop_reason: str | None = None
    tool_call_ids: list[str] = Field(default_factory=list)


class Thinking(_Event):
    type: Literal["thinking"] = "thinking"
    thinking: str
    redacted: bool = False
    extra: dict[str, object] = Field(default_factory=dict)  # provider-specific


class Usage(_Event):
    type: Literal["usage"] = "usage"
    response_id: str | None = None
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0  # cache read, present in every provider
    reasoning_tokens: int = 0  # OpenAI/Gemini; 0 on Anthropic (folded in output)
    extra: dict[str, int] = Field(default_factory=dict)  # provider-specific


Event = Annotated[
    ToolStart | ToolEnd | ModelResponse | Thinking | Usage,
    Field(discriminator="type"),
]


class EventSink(Protocol):
    def emit(self, event: Event) -> None: ...


class NullSink:
    def emit(self, event: Event) -> None:
        return None


class JsonlSink:
    def __init__(self, path: str | Path) -> None:
        # buffering=1 -> line-buffered: each emit flushes one terminated line.
        self._fh = open(path, "a", encoding="utf-8", buffering=1)

    def emit(self, event: Event) -> None:
        try:
            self._fh.write(event.model_dump_json() + "\n")
        except Exception:
            pass  # emit must never raise; logging is best-effort

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> "JsonlSink":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
