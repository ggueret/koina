import pytest

from koina import ToolContext, default_registry, dispatch
from koina.calls import ToolCall


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(cwd=tmp_path)


def test_registry_has_six_tools():
    names = {t.name for t in default_registry().tools()}
    assert names == {"Read", "Write", "Edit", "Bash", "Glob", "Grep"}


async def test_dispatch_write_then_read(tmp_path, ctx):
    reg = default_registry()
    f = tmp_path / "x.txt"
    w = await dispatch(
        ToolCall(id="1", name="Write", input={"file_path": str(f), "content": "hi"}),
        reg,
        ctx,
    )
    assert w.is_error is False
    r = await dispatch(
        ToolCall(id="2", name="Read", input={"file_path": str(f)}), reg, ctx
    )
    assert r.content == "1\thi"
