"""Multi-agent code review: parallel dimension reviewers plus a synthesis pass.

Each dimension (correctness, performance, security) is a read-only single-agent
review with a focused system prompt; they run in parallel. A final synthesis call
(no tools) merges them into one consolidated report.
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

from _agent import compute_changed_files, compute_diff, run_agent

from koina import ToolContext, ToolRegistry
from koina.tools.glob import Glob
from koina.tools.grep import Grep
from koina.tools.read import Read

DIMENSIONS = {
    "correctness": "Focus ONLY on correctness: bugs, broken logic, edge cases the change introduces or misses, and wrong or missing error handling.",
    "performance": "Focus ONLY on performance: inefficient algorithms or data structures, unnecessary work, N+1 patterns, blocking calls, and resource leaks.",
    "security": "Focus ONLY on security: injection, unsafe input handling, path traversal, secrets in code, unsafe deserialization, and missing validation or authorization.",
}

SYNTHESIS_PROMPT = """You are the lead reviewer. You are given several specialist reviews of the same change (correctness, performance, security). Merge them into a single consolidated report: deduplicate overlapping findings, drop anything speculative or low-signal, and prioritize. Output:
- A one-paragraph summary.
- Issues grouped Critical / Important / Minor, each with file:line and a concrete suggested fix.
- An Assessment: ready as-is, or the must-fix items."""


def read_only_registry() -> ToolRegistry:
    return ToolRegistry([Read(), Grep(), Glob()])


def dimension_prompt(focus: str) -> str:
    return f"""You are a code reviewer with a single specialty for this review.

{focus}

You are given a git diff. Use the read tools (Read, Grep, Glob) to read changed files in full and search for related code before concluding. All file paths are relative to the repository root. This is a read-only review.

Report only findings within your specialty that you are confident are real. For each: file:line, the issue, and a concrete fix. If you find nothing in your specialty, say so in one line."""


async def run_dimension(
    client: Any,
    model: str,
    diff: str,
    changed_files: list[str],
    repo_root: Path,
    focus: str,
    max_turns: int,
) -> str:
    files_block = "\n".join(changed_files) or "(none)"
    initial = (
        "Review the following change within your specialty. All paths are relative to the repository root.\n\n"
        f"Changed files:\n{files_block}\n\n"
        f"Diff:\n```diff\n{diff}\n```"
    )
    return await run_agent(
        client,
        model,
        dimension_prompt(focus),
        initial,
        read_only_registry(),
        ToolContext(cwd=repo_root),
        max_turns,
    )


async def synthesize(client: Any, model: str, reports: dict[str, str]) -> str:
    sections = "\n\n".join(
        f"## {name} review\n{report}" for name, report in reports.items()
    )
    resp = await client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYNTHESIS_PROMPT,
        messages=[{"role": "user", "content": f"Specialist reviews:\n\n{sections}"}],
    )
    return "\n".join(b.text for b in resp.content if b.type == "text")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Multi-agent dimension code review of a git diff."
    )
    parser.add_argument(
        "base", nargs="?", default="HEAD~1", help="Base git ref (default: HEAD~1)"
    )
    parser.add_argument("--model", default="claude-opus-4-8", help="Anthropic model id")
    parser.add_argument(
        "--max-turns", type=int, default=20, help="Max agent turns per dimension"
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

    from anthropic import AsyncAnthropic

    client = AsyncAnthropic()
    names = list(DIMENSIONS)
    print(
        f"Running {len(names)} dimension reviews in parallel: {', '.join(names)}",
        file=sys.stderr,
    )
    results = await asyncio.gather(
        *(
            run_dimension(
                client,
                args.model,
                diff,
                changed_files,
                repo_root,
                DIMENSIONS[name],
                args.max_turns,
            )
            for name in names
        )
    )
    reports = dict(zip(names, results, strict=True))
    print("Synthesizing...", file=sys.stderr)
    final = await synthesize(client, args.model, reports)
    print(final)


if __name__ == "__main__":
    asyncio.run(main())
