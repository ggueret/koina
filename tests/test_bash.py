import pytest

from koina.context import ToolContext
from koina.tools.bash import Bash


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(cwd=tmp_path)


async def test_runs_command(tmp_path, ctx):
    out = await Bash().run(Bash.Input(command="echo hello"), ctx)
    assert out.stdout.strip() == "hello"
    assert out.exit_code == 0


async def test_captures_exit_code(tmp_path, ctx):
    out = await Bash().run(Bash.Input(command="exit 3"), ctx)
    assert out.exit_code == 3


async def test_cwd_persists_across_calls(tmp_path, ctx):
    (tmp_path / "sub").mkdir()
    await Bash().run(Bash.Input(command="cd sub"), ctx)
    out = await Bash().run(Bash.Input(command="pwd"), ctx)
    assert out.stdout.strip() == str(tmp_path / "sub")
    assert ctx.cwd == tmp_path / "sub"


async def test_timeout(tmp_path, ctx):
    out = await Bash().run(Bash.Input(command="sleep 5", timeout=100), ctx)
    assert out.timed_out is True


async def test_truncates_long_output(tmp_path, ctx):
    out = await Bash().run(Bash.Input(command="yes x | head -n 100000"), ctx)
    assert out.truncated is True
    assert len(out.stdout) <= 30_000 + 100


def test_render_result_includes_streams():
    from koina.tools.bash import BashOutput

    content = Bash().render_result(
        BashOutput(
            stdout="out", stderr="err", exit_code=0, timed_out=False, truncated=False
        )
    )
    assert "out" in content


async def test_truncates_combined_stdout_stderr(tmp_path, ctx):
    out = await Bash().run(
        Bash.Input(command="echo short; yes y | head -n 40000 >&2"), ctx
    )
    assert out.truncated is True
    assert len(out.stdout) + len(out.stderr) <= 30_000 + 200


def test_render_result_reports_nonzero_exit():
    from koina.tools.bash import BashOutput

    content = Bash().render_result(
        BashOutput(
            stdout="", stderr="oops", exit_code=2, timed_out=False, truncated=False
        )
    )
    assert "Exit code: 2" in content
