import asyncio
import os
import signal
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ..context import ToolContext
from ..tool import Tool

DEFAULT_TIMEOUT_MS = 120_000
MAX_TIMEOUT_MS = 600_000
MAX_OUTPUT_CHARS = 30_000
_MARKER = "__KOINA_CWD__:"


class BashInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command: str = Field(description="The command to execute")
    timeout: int | None = Field(default=None, description="Optional timeout in milliseconds")
    description: str | None = Field(default=None, description="Advisory description, no effect")


@dataclass
class BashOutput:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool
    truncated: bool


class Bash(Tool):
    name = "Bash"
    description = "Execute a bash command. The working directory persists between calls."
    Input = BashInput

    async def run(self, input: BashInput, ctx: ToolContext) -> BashOutput:
        timeout_ms = min(input.timeout or DEFAULT_TIMEOUT_MS, MAX_TIMEOUT_MS)
        script = f"{input.command}\n__rc=$?\nprintf '\\n{_MARKER}%s' \"$PWD\"\nexit $__rc"
        proc = await asyncio.create_subprocess_exec(
            "bash",
            "-c",
            script,
            cwd=str(ctx.cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=timeout_ms / 1000
            )
        except asyncio.TimeoutError:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()
            await proc.wait()
            return BashOutput(
                stdout="", stderr="", exit_code=124, timed_out=True, truncated=False
            )

        stdout = stdout_b.decode("utf-8", errors="replace")
        marker_index = stdout.rfind(_MARKER)
        if marker_index != -1:
            new_cwd = stdout[marker_index + len(_MARKER):].strip()
            stdout = stdout[:marker_index].rstrip("\n")
            if new_cwd:
                ctx.cwd = Path(new_cwd)

        stderr = stderr_b.decode("utf-8", errors="replace")
        truncated = len(stdout) + len(stderr) > MAX_OUTPUT_CHARS
        if truncated:
            if len(stdout) >= MAX_OUTPUT_CHARS:
                stdout = stdout[:MAX_OUTPUT_CHARS] + "\n(output truncated)"
                stderr = ""
            else:
                remaining = MAX_OUTPUT_CHARS - len(stdout)
                stderr = stderr[:remaining] + "\n(output truncated)"
        return BashOutput(
            stdout=stdout,
            stderr=stderr,
            exit_code=proc.returncode or 0,
            timed_out=False,
            truncated=truncated,
        )

    def render_result(self, output: BashOutput) -> str:
        if output.timed_out:
            return "Command timed out"
        parts = [output.stdout]
        if output.stderr.strip():
            parts.append(output.stderr)
        content = "\n".join(p for p in parts if p) or "(no output)"
        if output.exit_code != 0:
            content += f"\nExit code: {output.exit_code}"
        return content

