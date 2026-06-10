import shutil

import pytest

from koina.context import ToolContext
from koina.tools.glob import Glob

pytestmark = pytest.mark.skipif(
    shutil.which("rg") is None, reason="ripgrep not installed"
)


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(cwd=tmp_path)


async def test_matches_pattern(tmp_path, ctx):
    (tmp_path / "a.py").write_text("x")
    (tmp_path / "b.py").write_text("x")
    (tmp_path / "c.txt").write_text("x")
    out = await Glob().run(Glob.Input(pattern="*.py"), ctx)
    assert sorted(out.filenames) == ["a.py", "b.py"]
    assert out.truncated is False


async def test_relative_paths(tmp_path, ctx):
    sub = tmp_path / "src"
    sub.mkdir()
    (sub / "m.py").write_text("x")
    out = await Glob().run(Glob.Input(pattern="**/*.py"), ctx)
    assert out.filenames == ["src/m.py"]


async def test_explicit_path(tmp_path, ctx):
    sub = tmp_path / "pkg"
    sub.mkdir()
    (sub / "z.py").write_text("x")
    out = await Glob().run(Glob.Input(pattern="*.py", path=str(sub)), ctx)
    assert out.filenames == ["z.py"]


def test_render_result_lists_files():
    from koina.tools.glob import GlobOutput

    assert (
        Glob().render_result(GlobOutput(filenames=["a.py", "b.py"], truncated=False))
        == "a.py\nb.py"
    )


def test_render_result_empty():
    from koina.tools.glob import GlobOutput

    assert (
        Glob().render_result(GlobOutput(filenames=[], truncated=False))
        == "No files found"
    )
