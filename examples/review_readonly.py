"""Single-agent, read-only code-review script.

The diff is computed by this script (via subprocess); the agent only has access
to Read, Grep, and Glob tools, so it cannot modify anything.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from _agent import compute_changed_files, compute_diff, run_agent

from koina import EventSink, JsonlSink, NullSink, ToolContext, ToolRegistry
from koina.tools.glob import Glob
from koina.tools.grep import Grep
from koina.tools.read import Read

SYSTEM_PROMPT = """You are a meticulous code reviewer. You are given a git diff to review.

All file paths are relative to the repository root.

Use the tools to read each changed file in full and to search the codebase for related code (callers, definitions, similar patterns) before drawing conclusions. The diff alone is not enough context.

Focus, in order:
1. Correctness bugs and edge cases the change introduces or misses.
2. Then code quality (clarity, naming, error handling).

Apply confidence filtering: only report a finding if you are confident it is real. Prefer a few high-signal findings over many speculative ones.

When done, output a report with:
- A one-paragraph summary.
- Issues grouped Critical / Important / Minor, each with file:line and a concrete suggested fix.
- An Assessment: ready as-is, or the must-fix items.

This is a read-only review. You cannot and must not modify any files."""


def read_only_registry() -> ToolRegistry:
    return ToolRegistry([Read(), Grep(), Glob()])


async def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only code review of a git diff.")
    parser.add_argument(
        "base", nargs="?", default="HEAD~1", help="Base git ref (default: HEAD~1)"
    )
    parser.add_argument("--model", default="claude-opus-4-8", help="Anthropic model id")
    parser.add_argument(
        "--max-turns",
        type=int,
        default=20,
        help="Max agent turns before forcing a report",
    )
    parser.add_argument(
        "--log", default=None, help="Write a JSONL event transcript to this path"
    )
    parser.add_argument(
        "--thinking",
        action="store_true",
        help="Enable adaptive thinking (summarized) so reasoning is captured in --log",
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
    changed_files = compute_changed_files(args.base, repo_root)
    files_block = "\n".join(changed_files) or "(none)"
    initial = (
        "Review the following change. All paths are relative to the repository root.\n\n"
        f"Changed files:\n{files_block}\n\n"
        f"Diff:\n```diff\n{diff}\n```"
    )

    from anthropic import AsyncAnthropic

    client = AsyncAnthropic()
    events: EventSink = JsonlSink(args.log) if args.log else NullSink()
    ctx = ToolContext(cwd=repo_root, events=events)
    try:
        report = await run_agent(
            client,
            args.model,
            SYSTEM_PROMPT,
            initial,
            read_only_registry(),
            ctx,
            args.max_turns,
            thinking=args.thinking,
        )
    finally:
        if isinstance(events, JsonlSink):
            events.close()
    print(report)


if __name__ == "__main__":
    asyncio.run(main())
