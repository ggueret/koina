from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel

from .context import ToolContext


class ToolError(Exception):
    """Raised inside run() to signal a user-facing error -> tool_result is_error."""


class Tool(ABC):
    name: ClassVar[str]
    aliases: ClassVar[tuple[str, ...]] = ()
    description: ClassVar[str]
    Input: ClassVar[type[BaseModel]]
    is_read_only: ClassVar[bool] = False
    is_concurrency_safe: ClassVar[bool] = False

    @abstractmethod
    async def run(self, input: Any, ctx: ToolContext) -> Any: ...

    @abstractmethod
    def render_result(self, output: Any) -> str: ...

    @classmethod
    def input_json_schema(cls) -> dict[str, object]:
        return cls.Input.model_json_schema()
