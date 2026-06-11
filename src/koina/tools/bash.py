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
_READ_CHUNK = 65_536
# Bytes kept from the end of stdout so the trailing CWD marker survives truncation.
_TAIL_BYTES = 8_192


async def _drain_capped(
    stream: asyncio.StreamReader, cap: int, keep_tail: bool
) -> tuple[bytes, bytes, bool]:
    """Read a stream to EOF while bounding memory.

    Keeps at most ``cap`` bytes from the head and, when ``keep_tail``, the last
    ``_TAIL_BYTES`` bytes. Returns ``(head, tail, overflowed)``. Peak memory is
    ``cap + _TAIL_BYTES`` regardless of how much the command emits.
    """
    head = bytearray()
    tail = bytearray()
    overflowed = False
    while True:
        chunk = await stream.read(_READ_CHUNK)
        if not chunk:
            break
        room = cap - len(head)
        if room > 0:
            head += chunk[:room]
        if len(chunk) > room:
            overflowed = True
        if keep_tail:
            tail += chunk
            if len(tail) > _TAIL_BYTES:
                del tail[: len(tail) - _TAIL_BYTES]
    return bytes(head), bytes(tail), overflowed


def _strip_marker_prefix(text: str) -> str:
    """Drop a partial ``_MARKER`` prefix left at the end of a truncated head."""
    for k in range(min(len(_MARKER), len(text)), 0, -1):
        if text.endswith(_MARKER[:k]):
            return text[:-k]
    return text


class BashInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command: str = Field(description="The command to execute")
    timeout: int | None = Field(
        default=None, description="Optional timeout in milliseconds"
    )
    description: str | None = Field(
        default=None, description="Advisory description, no effect"
    )


@dataclass
class BashOutput:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool
    truncated: bool


class Bash(Tool):
    name = "Bash"
    description = (
        "Execute a bash command. The working directory persists between calls."
    )
    Input = BashInput

    async def run(self, input: BashInput, ctx: ToolContext) -> BashOutput:
        timeout_ms = min(input.timeout or DEFAULT_TIMEOUT_MS, MAX_TIMEOUT_MS)
        script = (
            f"{input.command}\n__rc=$?\nprintf '\\n{_MARKER}%s' \"$PWD\"\nexit $__rc"
        )
        proc = await asyncio.create_subprocess_exec(
            "bash",
            "-c",
            script,
            cwd=str(ctx.cwd),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
        assert proc.stdout is not None and proc.stderr is not None
        try:
            (
                (out_head, out_tail, out_over),
                (err_head, _, err_over),
            ) = await asyncio.wait_for(
                asyncio.gather(
                    _drain_capped(proc.stdout, MAX_OUTPUT_CHARS, keep_tail=True),
                    _drain_capped(proc.stderr, MAX_OUTPUT_CHARS, keep_tail=False),
                ),
                timeout=timeout_ms / 1000,
            )
            await proc.wait()
        except asyncio.TimeoutError:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()
            await proc.wait()
            return BashOutput(
                stdout="", stderr="", exit_code=124, timed_out=True, truncated=False
            )

        # The CWD marker is printed last. If stdout overflowed the cap it lives in
        # the tail; otherwise the whole output (marker included) is in the head.
        marker_blob = (out_tail if out_over else out_head).decode(
            "utf-8", errors="replace"
        )
        marker_index = marker_blob.rfind(_MARKER)
        if marker_index != -1:
            new_cwd = marker_blob[marker_index + len(_MARKER) :].strip()
            if new_cwd:
                ctx.cwd = Path(new_cwd)

        stdout = out_head.decode("utf-8", errors="replace")
        if out_over:
            stdout = _strip_marker_prefix(stdout).rstrip("\n") + "\n(output truncated)"
        elif marker_index != -1:
            stdout = stdout[: stdout.rfind(_MARKER)].rstrip("\n")

        stderr = err_head.decode("utf-8", errors="replace")
        if err_over:
            stderr = stderr.rstrip("\n") + "\n(output truncated)"

        return BashOutput(
            stdout=stdout,
            stderr=stderr,
            exit_code=proc.returncode or 0,
            timed_out=False,
            truncated=out_over or err_over,
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
