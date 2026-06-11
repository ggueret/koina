from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ..context import ToolContext
from ..tool import Tool, ToolError


class ReadInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file_path: str = Field(description="The absolute path to the file to read")
    offset: int | None = Field(default=None, ge=1, description="1-based start line")
    limit: int | None = Field(default=None, ge=1, description="Number of lines to read")


@dataclass
class ReadOutput:
    content: str
    start_line: int
    num_lines: int
    truncated: bool


class Read(Tool):
    name = "Read"
    description = (
        "Read a text file from the local filesystem. Lines are returned numbered."
    )
    Input = ReadInput
    is_read_only = True
    is_concurrency_safe = True

    async def run(self, input: ReadInput, ctx: ToolContext) -> ReadOutput:
        path = Path(input.file_path)
        if not path.is_absolute():
            path = ctx.cwd / path
        if not path.exists():
            raise ToolError(f"File does not exist: {input.file_path}")
        if not path.is_file():
            raise ToolError(f"Not a regular file: {input.file_path}")

        byte_budget = min(ctx.read_limits.max_bytes, ctx.read_limits.max_tokens * 4)
        with path.open("rb") as fh:
            data = fh.read(byte_budget + 1)
        truncated = len(data) > byte_budget
        if truncated:
            data = data[:byte_budget]

        text = data.decode("utf-8", errors="replace")
        lines = text.split("\n")
        if lines and lines[-1] == "":
            lines = lines[:-1]

        if len(lines) == 0:
            return ReadOutput(
                content="(file is empty)",
                start_line=1,
                num_lines=0,
                truncated=truncated,
            )

        start = input.offset if input.offset and input.offset > 0 else 1
        if start > len(lines):
            return ReadOutput(
                content=f"(offset {start} is beyond end of file: {len(lines)} lines)",
                start_line=start,
                num_lines=0,
                truncated=truncated,
            )

        end = (
            len(lines)
            if input.limit is None
            else min(len(lines), start - 1 + input.limit)
        )
        selected = lines[start - 1 : end]
        numbered = "\n".join(f"{start + i}\t{line}" for i, line in enumerate(selected))
        return ReadOutput(
            content=numbered,
            start_line=start,
            num_lines=len(selected),
            truncated=truncated,
        )

    def render_result(self, output: ReadOutput) -> str:
        content = output.content
        if output.truncated:
            content += "\n(file truncated: exceeded max_bytes)"
        return content
