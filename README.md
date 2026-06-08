<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/brand/wordmark-dark.svg">
    <img src="assets/brand/wordmark.svg" alt="koina" width="240">
  </picture>
</p>

<p align="center"><em>An agentic toolset.</em></p>

<p align="center">
  Reusable, provider-neutral building blocks for agents on low-level LLM SDKs:
  the six core file/shell tools (Read, Write, Edit, Bash, Glob, Grep), a
  never-raising <code>dispatch</code>, structured JSONL logging, and a thin
  adapter per provider. koina gives you the tools and the dispatch; the agentic
  loop stays in your code.
</p>

## Requirements

- Python 3.12+
- ripgrep (`rg`) on PATH (for Glob and Grep)

## Install

```bash
uv add koina
```

The library depends only on `pydantic`. Provider SDKs (`anthropic`, `openai`)
are the caller's dependency, used in your loop, not by koina.

## Usage

`dispatch` and the tools are provider-neutral; an adapter translates a provider's
wire format to and from the neutral `ToolCall`/`ToolResult`. With the Anthropic
adapter:

```python
from pathlib import Path
from anthropic import AsyncAnthropic
from koina import default_registry, dispatch, ToolContext
from koina.adapters import anthropic as adapter

client = AsyncAnthropic()
reg = default_registry()
ctx = ToolContext(cwd=Path.cwd())
msgs = [{"role": "user", "content": "List the Python files."}]

while True:
    resp = await client.messages.create(
        model="claude-opus-4-8", max_tokens=4096,
        messages=msgs, tools=adapter.tools_param(reg),
    )
    msgs.append({"role": "assistant", "content": resp.content})
    calls = adapter.parse_tool_calls(resp.content)
    if not calls:
        break
    results = [await dispatch(c, reg, ctx) for c in calls]
    msgs.append(adapter.format_results(results))
```

Swap `koina.adapters.anthropic` for `koina.adapters.openai` to run the same tools
against the OpenAI Chat Completions API (or any OpenAI-compatible server, e.g.
llama.cpp). See `examples/` for runnable read-only code-review scripts on both.

## What's in the box

- **Six core tools** (Read, Write, Edit, Bash, Glob, Grep), faithful to Claude
  Code's observable behavior, headless (no permissions or hooks).
- **`dispatch` never raises**: it always returns a `ToolResult` (errors set
  `is_error=True`).
- **Provider-neutral core** (`ToolCall`, `ToolResult`) with per-provider adapters
  (`koina.adapters.anthropic`, `koina.adapters.openai`). The library never imports
  a provider SDK at runtime.
- **Structured logging**: typed events (tool calls, model calls, token usage,
  reasoning) emitted to a pluggable `EventSink` (`JsonlSink`/`NullSink`), so a run
  reconstructs from a JSONL transcript. Off by default, zero cost when inactive.

Permissions, web tools, and concurrency orchestration are out of scope.
