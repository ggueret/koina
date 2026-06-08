import shutil

import pytest

from koina.context import ToolContext
from koina.tools.grep import Grep

pytestmark = pytest.mark.skipif(shutil.which("rg") is None, reason="ripgrep not installed")


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(cwd=tmp_path)


def _seed(tmp_path):
    (tmp_path / "a.py").write_text("import os\nx = 1\n")
    (tmp_path / "b.py").write_text("y = 2\nimport sys\n")


async def test_files_with_matches_default(tmp_path, ctx):
    _seed(tmp_path)
    out = await Grep().run(Grep.Input(pattern="import"), ctx)
    assert sorted(out.filenames) == ["a.py", "b.py"]
    assert out.mode == "files_with_matches"


async def test_content_mode(tmp_path, ctx):
    _seed(tmp_path)
    out = await Grep().run(Grep.Input(pattern="import os", output_mode="content"), ctx)
    assert "import os" in out.content


async def test_count_mode(tmp_path, ctx):
    _seed(tmp_path)
    out = await Grep().run(Grep.Input(pattern="import", output_mode="count"), ctx)
    assert out.mode == "count"
    assert "a.py" in out.content


async def test_case_insensitive_alias(tmp_path, ctx):
    (tmp_path / "c.py").write_text("IMPORT this\n")
    out = await Grep().run(
        Grep.Input.model_validate({"pattern": "import", "-i": True, "output_mode": "content"}),
        ctx,
    )
    assert "IMPORT this" in out.content


def test_schema_emits_dash_keys():
    props = Grep.input_json_schema()["properties"]
    assert "-A" in props and "-i" in props and "-n" in props


async def test_offset_skips_results(tmp_path, ctx):
    for i in range(5):
        (tmp_path / f"f{i}.py").write_text("import x\n")
    out = await Grep().run(Grep.Input(pattern="import", offset=2), ctx)
    assert len(out.filenames) == 3
