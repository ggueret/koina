from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .._ripgrep import run_rg
from ..context import ToolContext
from ..tool import Tool

DEFAULT_HEAD_LIMIT = 250
MAX_COLUMNS = 500


class GrepInput(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    pattern: str = Field(description="The regular expression to search for")
    path: str | None = Field(default=None, description="File or directory to search")
    glob: str | None = Field(default=None, description="Glob to filter files")
    output_mode: Literal["content", "files_with_matches", "count"] | None = Field(
        default=None, description="Output mode"
    )
    after: int | None = Field(default=None, alias="-A", description="Lines after match")
    before: int | None = Field(
        default=None, alias="-B", description="Lines before match"
    )
    context: int | None = Field(
        default=None, alias="-C", description="Lines around match"
    )
    line_numbers: bool | None = Field(
        default=None, alias="-n", description="Show line numbers"
    )
    ignore_case: bool | None = Field(
        default=None, alias="-i", description="Case insensitive"
    )
    type: str | None = Field(default=None, description="File type filter")
    head_limit: int | None = Field(default=None, description="Limit results")
    offset: int | None = Field(default=None, description="Skip the first N results")
    multiline: bool | None = Field(default=None, description="Multiline mode")


@dataclass
class GrepOutput:
    mode: str
    filenames: list[str]
    content: str


class Grep(Tool[GrepInput, GrepOutput]):
    name = "Grep"
    description = "Search file contents with ripgrep."
    Input = GrepInput

    async def run(self, input: GrepInput, ctx: ToolContext) -> GrepOutput:
        mode = input.output_mode or "files_with_matches"
        args: list[str] = []
        if input.ignore_case:
            args.append("-i")
        if input.multiline:
            args += ["-U", "--multiline-dotall"]
        if input.glob:
            args += ["--glob", input.glob]
        if input.type:
            args += ["--type", input.type]

        if mode == "files_with_matches":
            args.append("--files-with-matches")
        elif mode == "count":
            args.append("--count")
        else:
            args += [
                "--line-number"
                if input.line_numbers is not False
                else "--no-line-number"
            ]
            args += ["--max-columns", str(MAX_COLUMNS)]
            if input.context is not None:
                args += ["-C", str(input.context)]
            else:
                if input.after is not None:
                    args += ["-A", str(input.after)]
                if input.before is not None:
                    args += ["-B", str(input.before)]

        base = Path(input.path) if input.path else ctx.cwd
        if not base.is_absolute():
            base = ctx.cwd / base
        # Run with base as cwd so ripgrep reports paths relative to it (like
        # Glob), instead of basenames that collide across subdirectories.
        args += ["--", input.pattern]

        _, stdout = await run_rg(args, cwd=str(base))
        limit = DEFAULT_HEAD_LIMIT if input.head_limit is None else input.head_limit
        offset = input.offset or 0
        lines = [line for line in stdout.splitlines() if line]
        if offset > 0:
            lines = lines[offset:]
        if limit > 0:
            lines = lines[:limit]

        if mode == "files_with_matches":
            return GrepOutput(mode=mode, filenames=lines, content="\n".join(lines))
        return GrepOutput(mode=mode, filenames=[], content="\n".join(lines))

    def render_result(self, output: GrepOutput) -> str:
        return output.content or "No matches found"
