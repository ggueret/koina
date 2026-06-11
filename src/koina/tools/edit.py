from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ..context import ToolContext
from ..tool import Tool, ToolError


class EditInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file_path: str = Field(description="The absolute path to the file to modify")
    old_string: str = Field(description="The text to replace")
    new_string: str = Field(description="The text to replace it with")
    replace_all: bool = Field(default=False, description="Replace all occurrences")


@dataclass
class EditOutput:
    file_path: str
    replace_all: bool
    was_created: bool = False


class Edit(Tool[EditInput, EditOutput]):
    name = "Edit"
    description = "Perform an exact string replacement in a file."
    Input = EditInput

    async def run(self, input: EditInput, ctx: ToolContext) -> EditOutput:
        path = Path(input.file_path)
        if not path.is_absolute():
            path = ctx.cwd / path
        if path.suffix == ".ipynb":
            raise ToolError("Use a notebook editor for .ipynb files")

        if input.old_string == "" and not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(input.new_string, encoding="utf-8", newline="\n")
            return EditOutput(
                file_path=str(path), replace_all=input.replace_all, was_created=True
            )

        if input.old_string == "" and path.exists():
            raise ToolError(
                f"File already exists: {input.file_path}; provide a non-empty old_string to edit it"
            )

        if not path.exists():
            raise ToolError(f"File does not exist: {input.file_path}")

        text = path.read_text(encoding="utf-8")
        count = text.count(input.old_string)
        if count == 0:
            raise ToolError(f"old_string not found in {input.file_path}")
        if count > 1 and not input.replace_all:
            raise ToolError(
                f"Found {count} matches but replace_all is false; make old_string unique"
            )

        new_text = text.replace(
            input.old_string, input.new_string, -1 if input.replace_all else 1
        )
        path.write_text(new_text, encoding="utf-8", newline="\n")
        return EditOutput(file_path=str(path), replace_all=input.replace_all)

    def render_result(self, output: EditOutput) -> str:
        if output.was_created:
            return f"File created: {output.file_path}"
        suffix = " (all occurrences replaced)" if output.replace_all else ""
        return f"File updated: {output.file_path}{suffix}"
