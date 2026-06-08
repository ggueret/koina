import asyncio


async def run_rg(args: list[str], cwd: str) -> tuple[int, str]:
    """Run ripgrep, returning (returncode, stdout). rg exits 1 when no matches."""
    proc = await asyncio.create_subprocess_exec(
        "rg",
        *args,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode not in (0, 1):
        raise RuntimeError(stderr.decode("utf-8", errors="replace").strip() or "rg failed")
    return proc.returncode or 0, stdout.decode("utf-8", errors="replace")
