import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "examples"))

import _agent
import review_readonly


def test_read_only_registry_has_only_read_tools():
    names = {t.name for t in review_readonly.read_only_registry().tools()}
    assert names == {"Read", "Grep", "Glob"}


def test_system_prompt_mentions_review():
    assert "review" in review_readonly.SYSTEM_PROMPT.lower()
    assert "read-only" in review_readonly.SYSTEM_PROMPT.lower()


def test_system_prompt_mentions_relative_paths():
    assert "relative to the repository root" in review_readonly.SYSTEM_PROMPT.lower()


def _make_repo(tmp_path):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    (tmp_path / "f.txt").write_text("one\n")
    git("add", "f.txt")
    git("commit", "-m", "first")
    (tmp_path / "f.txt").write_text("two\n")
    git("add", "f.txt")
    git("commit", "-m", "second")


def test_compute_diff_returns_changes(tmp_path):
    _make_repo(tmp_path)
    assert "two" in _agent.compute_diff("HEAD~1", tmp_path)


def test_compute_changed_files(tmp_path):
    _make_repo(tmp_path)
    assert "f.txt" in _agent.compute_changed_files("HEAD~1", tmp_path)


def test_review_readonly_accepts_log_and_thinking_flags():
    import inspect

    # main() must register both --log and --thinking arguments
    src = inspect.getsource(review_readonly.main)
    assert "--log" in src
    assert "--thinking" in src
