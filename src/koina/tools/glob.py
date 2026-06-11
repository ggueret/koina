from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .._ripgrep import run_rg
from ..context import ToolContext
from ..tool import Tool

GLOB_LIMIT = 100


class GlobInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pattern: str = Field(description="The glob pattern to match files against")
    path: str | None = Field(default=None, description="Directory to search in")


@dataclass
class GlobOutput:
    filenames: list[str]
    truncated: bool


class Glob(Tool[GlobInput, GlobOutput]):
    name = "Glob"
    description = "Find files matching a glob pattern, sorted by modification time."
    Input = GlobInput

    async def run(self, input: GlobInput, ctx: ToolContext) -> GlobOutput:
        base = Path(input.path) if input.path else ctx.cwd
        if not base.is_absolute():
            base = ctx.cwd / base
        _, stdout = await run_rg(
            ["--files", "--hidden", "--glob", input.pattern, "--sortr", "modified"],
            cwd=str(base),
        )
        names = [line for line in stdout.splitlines() if line]
        truncated = len(names) > GLOB_LIMIT
        return GlobOutput(filenames=names[:GLOB_LIMIT], truncated=truncated)

    def render_result(self, output: GlobOutput) -> str:
        if not output.filenames:
            return "No files found"
        content = "\n".join(output.filenames)
        if output.truncated:
            content += "\n(results truncated; use a more specific pattern)"
        return content
