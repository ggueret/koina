from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..context import ToolContext
from ..tool import Tool


class WriteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file_path: str = Field(description="The absolute path to the file to write")
    content: str = Field(description="The content to write to the file")


@dataclass
class WriteOutput:
    kind: Literal["create", "update"]
    file_path: str


class Write(Tool):
    name = "Write"
    description = "Write a file to the local filesystem, overwriting if it exists."
    Input = WriteInput

    async def run(self, input: WriteInput, ctx: ToolContext) -> WriteOutput:
        path = Path(input.file_path)
        if not path.is_absolute():
            path = ctx.cwd / path
        kind: Literal["create", "update"] = "update" if path.exists() else "create"
        path.parent.mkdir(parents=True, exist_ok=True)
        normalized = input.content.replace("\r\n", "\n").replace("\r", "\n")
        path.write_text(normalized, encoding="utf-8", newline="\n")
        return WriteOutput(kind=kind, file_path=str(path))

    def render_result(self, output: WriteOutput) -> str:
        verb = "created successfully at:" if output.kind == "create" else "updated:"
        return f"File {verb} {output.file_path}"

