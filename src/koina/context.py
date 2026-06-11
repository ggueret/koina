from dataclasses import dataclass, field
from pathlib import Path

from .observability import EventSink, NullSink


@dataclass
class ReadLimits:
    """Caps applied by `Read`: it keeps at most
    ``min(max_bytes, max_tokens * 4)`` bytes of a file."""

    max_tokens: int = 25_000
    max_bytes: int = 256 * 1024


@dataclass
class ToolContext:
    """State shared across tool calls, passed to every `run()`.

    Attributes:
        cwd: Working directory used to resolve relative paths. `Bash` updates it,
            so a ``cd`` persists across calls.
        read_limits: Byte/token caps applied by `Read`.
        events: Observability sink; defaults to `NullSink` (no-op).
    """

    cwd: Path
    read_limits: ReadLimits = field(default_factory=ReadLimits)
    events: EventSink = field(default_factory=NullSink)
