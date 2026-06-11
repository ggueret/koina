from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel

from .context import ToolContext


class ToolError(Exception):
    """Raise inside `run()` to signal a user-facing tool failure.

    `dispatch` catches it and returns a `ToolResult(is_error=True)`; it never
    propagates out of `dispatch`.
    """


class Tool[I: BaseModel, O](ABC):
    """Base class for a tool.

    Parameterize it with the pydantic input model and the output type, e.g.
    ``class Read(Tool[ReadInput, ReadOutput])``, so that `run` and
    `render_result` are type-checked against each other. `name`, `description`
    and `Input` are required class attributes; `aliases` is optional.
    """

    name: ClassVar[str]
    aliases: ClassVar[tuple[str, ...]] = ()
    description: ClassVar[str]
    Input: ClassVar[type[BaseModel]]

    @abstractmethod
    async def run(self, input: I, ctx: ToolContext) -> O: ...

    @abstractmethod
    def render_result(self, output: O) -> str: ...

    @classmethod
    def input_json_schema(cls) -> dict[str, object]:
        return cls.Input.model_json_schema()
