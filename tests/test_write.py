import pytest

from koina.context import ToolContext
from koina.tools.write import Write


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(cwd=tmp_path)


async def test_creates_file(tmp_path, ctx):
    f = tmp_path / "new.txt"
    out = await Write().run(Write.Input(file_path=str(f), content="hello"), ctx)
    assert out.kind == "create"
    assert f.read_text() == "hello"


async def test_creates_parent_dirs(tmp_path, ctx):
    f = tmp_path / "deep" / "nested" / "n.txt"
    await Write().run(Write.Input(file_path=str(f), content="x"), ctx)
    assert f.read_text() == "x"


async def test_overwrite_reports_update(tmp_path, ctx):
    f = tmp_path / "u.txt"
    f.write_text("old")
    out = await Write().run(Write.Input(file_path=str(f), content="new"), ctx)
    assert out.kind == "update"
    assert f.read_text() == "new"


async def test_relative_path_uses_cwd(tmp_path, ctx):
    await Write().run(Write.Input(file_path="rel.txt", content="y"), ctx)
    assert (tmp_path / "rel.txt").read_text() == "y"


def test_render_result_create():
    from koina.tools.write import WriteOutput

    content = Write().render_result(WriteOutput(kind="create", file_path="/x"))
    assert content == "File created successfully at: /x"


async def test_normalizes_lone_cr(tmp_path, ctx):
    await Write().run(
        Write.Input(file_path=str(tmp_path / "m.txt"), content="a\rb"), ctx
    )
    assert (tmp_path / "m.txt").read_bytes() == b"a\nb"
