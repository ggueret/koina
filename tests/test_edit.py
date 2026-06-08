import pytest

from koina.context import ToolContext
from koina.tool import ToolError
from koina.tools.edit import Edit


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(cwd=tmp_path)


async def test_replaces_single(tmp_path, ctx):
    f = tmp_path / "a.txt"
    f.write_text("foo bar foo")
    await Edit().run(
        Edit.Input(file_path=str(f), old_string="bar", new_string="baz"), ctx
    )
    assert f.read_text() == "foo baz foo"


async def test_multiple_matches_without_replace_all_raises(tmp_path, ctx):
    f = tmp_path / "a.txt"
    f.write_text("x x x")
    with pytest.raises(ToolError):
        await Edit().run(
            Edit.Input(file_path=str(f), old_string="x", new_string="y"), ctx
        )


async def test_replace_all(tmp_path, ctx):
    f = tmp_path / "a.txt"
    f.write_text("x x x")
    out = await Edit().run(
        Edit.Input(file_path=str(f), old_string="x", new_string="y", replace_all=True),
        ctx,
    )
    assert f.read_text() == "y y y"
    assert out.replace_all is True


async def test_create_with_empty_old_string(tmp_path, ctx):
    f = tmp_path / "new.txt"
    await Edit().run(
        Edit.Input(file_path=str(f), old_string="", new_string="hello"), ctx
    )
    assert f.read_text() == "hello"


async def test_string_not_found_raises(tmp_path, ctx):
    f = tmp_path / "a.txt"
    f.write_text("abc")
    with pytest.raises(ToolError):
        await Edit().run(
            Edit.Input(file_path=str(f), old_string="zzz", new_string="q"), ctx
        )


async def test_rejects_notebook(tmp_path, ctx):
    f = tmp_path / "n.ipynb"
    f.write_text("{}")
    with pytest.raises(ToolError):
        await Edit().run(
            Edit.Input(file_path=str(f), old_string="{}", new_string="[]"), ctx
        )


async def test_empty_old_string_on_existing_raises(tmp_path, ctx):
    f = tmp_path / "a.txt"
    f.write_text("data")
    with pytest.raises(ToolError):
        await Edit().run(
            Edit.Input(file_path=str(f), old_string="", new_string="x"), ctx
        )


def test_render_result_created():
    from koina.tools.edit import EditOutput

    content = Edit().render_result(EditOutput(file_path="/x", replace_all=False, was_created=True))
    assert "created" in content.lower()
