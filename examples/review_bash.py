"""Single-agent code-review where the agent drives git itself via Bash.

Unlike review_readonly.py, the diff is NOT pre-computed: the agent runs
`git diff`/`git log` through the Bash tool. Bash is not read-only, so the system
prompt strictly instructs a read-only review; there is no permission layer here.
"""

import argparse
import asyncio
from pathlib import Path

from _agent import run_agent

from koina import ToolContext, ToolRegistry
from koina.tools.bash import Bash
from koina.tools.glob import Glob
from koina.tools.grep import Grep
from koina.tools.read import Read

SYSTEM_PROMPT = """You are a meticulous code reviewer working inside a git repository.

You have a Bash tool plus read tools (Read, Grep, Glob). Use Bash to inspect the change yourself (for example `git diff`, `git log`, `git show`) and the read tools to read changed files in full and search for related code. All file paths are relative to the repository root.

This is a READ-ONLY review. Do not modify, create, or delete any files, and do not run any command that changes the working tree or the repository (no commits, checkouts, resets, or edits). Only inspect.

Focus, in order:
1. Correctness bugs and edge cases the change introduces or misses.
2. Then code quality (clarity, naming, error handling).

Apply confidence filtering: only report a finding if you are confident it is real.

When done, output a report with:
- A one-paragraph summary.
- Issues grouped Critical / Important / Minor, each with file:line and a concrete suggested fix.
- An Assessment: ready as-is, or the must-fix items."""


def bash_registry() -> ToolRegistry:
    return ToolRegistry([Read(), Grep(), Glob(), Bash()])


async def main() -> None:
    parser = argparse.ArgumentParser(description="Code review where the agent runs git via Bash.")
    parser.add_argument("base", nargs="?", default="HEAD~1", help="Base git ref (default: HEAD~1)")
    parser.add_argument("--model", default="claude-opus-4-8", help="Anthropic model id")
    parser.add_argument("--max-turns", type=int, default=20, help="Max agent turns before forcing a report")
    args = parser.parse_args()

    repo_root = Path.cwd()
    initial = (
        f"Review the code changes between `{args.base}` and HEAD in this git repository.\n\n"
        f"Start by running `git diff {args.base}...HEAD` and `git log --oneline {args.base}..HEAD` "
        "via Bash, then read the changed files in full and search for related code."
    )

    from anthropic import AsyncAnthropic

    client = AsyncAnthropic()
    report = await run_agent(
        client, args.model, SYSTEM_PROMPT, initial, bash_registry(), ToolContext(cwd=repo_root), args.max_turns
    )
    print(report)


if __name__ == "__main__":
    asyncio.run(main())
