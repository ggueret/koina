import pytest

from koina.context import ReadLimits, ToolContext
from koina.tools.read import Read


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(cwd=tmp_path)


async def test_reads_with_line_numbers(tmp_path, ctx):
    f = tmp_path / "a.txt"
    f.write_text("alpha\nbeta\ngamma\n")
    out = await Read().run(Read.Input(file_path=str(f)), ctx)
    assert out.content == "1\talpha\n2\tbeta\n3\tgamma"
    assert out.start_line == 1
    assert out.num_lines == 3


async def test_offset_and_limit(tmp_path, ctx):
    f = tmp_path / "a.txt"
    f.write_text("l1\nl2\nl3\nl4\nl5\n")
    out = await Read().run(Read.Input(file_path=str(f), offset=2, limit=2), ctx)
    assert out.content == "2\tl2\n3\tl3"


async def test_relative_path_uses_cwd(tmp_path, ctx):
    (tmp_path / "r.txt").write_text("x\n")
    out = await Read().run(Read.Input(file_path="r.txt"), ctx)
    assert out.content == "1\tx"


async def test_missing_file_raises(ctx):
    from koina.tool import ToolError

    with pytest.raises(ToolError):
        await Read().run(Read.Input(file_path="/nope/missing.txt"), ctx)


async def test_offset_past_eof_notes(tmp_path, ctx):
    f = tmp_path / "a.txt"
    f.write_text("only\n")
    out = await Read().run(Read.Input(file_path=str(f), offset=10), ctx)
    assert "beyond" in out.content.lower()


async def test_byte_limit_truncates(tmp_path):
    f = tmp_path / "big.txt"
    f.write_text("x\n" * 1000)
    ctx = ToolContext(cwd=tmp_path, read_limits=ReadLimits(max_bytes=10))
    out = await Read().run(Read.Input(file_path=str(f)), ctx)
    assert out.truncated is True


def test_render_result():
    from koina.tools.read import ReadOutput

    content = Read().render_result(
        ReadOutput(content="1\tx", start_line=1, num_lines=1, truncated=False)
    )
    assert content == "1\tx"


async def test_token_limit_truncates(tmp_path):
    from koina.context import ReadLimits, ToolContext

    f = tmp_path / "big.txt"
    f.write_text("word " * 50000)
    ctx = ToolContext(cwd=tmp_path, read_limits=ReadLimits(max_tokens=100))
    out = await Read().run(Read.Input(file_path=str(f)), ctx)
    assert out.truncated is True


def test_invalid_limit_rejected():
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        Read.Input(file_path="/x", limit=0)


async def test_empty_file_notes(tmp_path, ctx):
    f = tmp_path / "e.txt"
    f.write_text("")
    out = await Read().run(Read.Input(file_path=str(f)), ctx)
    assert "empty" in out.content.lower()


async def test_rejects_non_regular_file(tmp_path, ctx):
    import asyncio
    import os
    import sys

    from koina.tool import ToolError

    if sys.platform == "win32":
        pytest.skip("no mkfifo on Windows")
    fifo = tmp_path / "pipe"
    os.mkfifo(fifo)
    # Without the regular-file guard, read_bytes() blocks forever on a
    # writer-less FIFO; the guard must raise instead of hanging the loop.
    with pytest.raises(ToolError):
        await asyncio.wait_for(
            Read().run(Read.Input(file_path=str(fifo)), ctx), timeout=2.0
        )


async def test_does_not_read_whole_file(tmp_path, monkeypatch):
    from pathlib import Path

    f = tmp_path / "big.txt"
    f.write_text("x\n" * 1000)
    ctx = ToolContext(cwd=tmp_path, read_limits=ReadLimits(max_bytes=10))

    def boom(self):
        raise AssertionError("read_bytes materializes the whole file")

    monkeypatch.setattr(Path, "read_bytes", boom)
    out = await Read().run(Read.Input(file_path=str(f)), ctx)
    assert out.truncated is True


def test_truncation_marker_rendered():
    from koina.tools.read import ReadOutput

    rendered = Read().render_result(
        ReadOutput(content="1\tx", start_line=1, num_lines=1, truncated=True)
    )
    assert "truncated" in rendered
