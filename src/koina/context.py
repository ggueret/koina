import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from .observability import EventSink, NullSink


@dataclass
class ReadLimits:
    max_tokens: int = 25_000
    max_bytes: int = 256 * 1024


@dataclass
class ToolContext:
    cwd: Path
    cancel: asyncio.Event = field(default_factory=asyncio.Event)
    read_limits: ReadLimits = field(default_factory=ReadLimits)
    events: EventSink = field(default_factory=NullSink)
