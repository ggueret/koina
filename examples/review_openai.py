"""Read-only code review against an OpenAI-compatible endpoint (e.g. llama.cpp).

The agent has Read/Grep/Glob only. Point --base-url at any OpenAI-compatible
server. For a Basic-auth-protected one (htpasswd), export LLAMA_BASIC="user:pass".
"""

import argparse
import asyncio
import base64
import os
import sys
from pathlib import Path

from _agent import compute_changed_files, compute_diff
from _agent_openai import run_agent_openai
from review_readonly import SYSTEM_PROMPT, read_only_registry

from koina import EventSink, JsonlSink, NullSink, ToolContext


def build_client(base_url: str) -> object:
    from openai import AsyncOpenAI

    headers: dict[str, str] = {}
    basic = os.environ.get("LLAMA_BASIC")
    if basic:
        token = base64.b64encode(basic.encode()).decode()
        headers["Authorization"] = f"Basic {token}"
    return AsyncOpenAI(base_url=base_url, api_key="unused", default_headers=headers)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only code review via an OpenAI-compatible endpoint."
    )
    parser.add_argument(
        "base", nargs="?", default="HEAD~1", help="Base git ref (default: HEAD~1)"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8080/v1",
        help="OpenAI-compatible endpoint (default: a local llama.cpp server)",
    )
    parser.add_argument("--model", default="local", help="Model id the server serves")
    parser.add_argument("--max-turns", type=int, default=20, help="Max agent turns")
    parser.add_argument(
        "--log", default=None, help="Write a JSONL event transcript to this path"
    )
    args = parser.parse_args()

    repo_root = Path.cwd()
    diff = compute_diff(args.base, repo_root)
    if not diff.strip():
        print(
            f"No changes between {args.base} and HEAD. Nothing to review.",
            file=sys.stderr,
        )
        return
    files_block = "\n".join(compute_changed_files(args.base, repo_root)) or "(none)"
    initial = (
        "Review the following change. All paths are relative to the repository root.\n\n"
        f"Changed files:\n{files_block}\n\n"
        f"Diff:\n```diff\n{diff}\n```"
    )

    client = build_client(args.base_url)
    events: EventSink = JsonlSink(args.log) if args.log else NullSink()
    ctx = ToolContext(cwd=repo_root, events=events)
    try:
        report = await run_agent_openai(
            client,
            args.model,
            SYSTEM_PROMPT,
            initial,
            read_only_registry(),
            ctx,
            args.max_turns,
        )
    finally:
        if isinstance(events, JsonlSink):
            events.close()
    print(report)


if __name__ == "__main__":
    asyncio.run(main())
