import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "examples"))

import review_bash  # noqa: E402


def test_bash_registry_has_four_tools():
    names = {t.name for t in review_bash.bash_registry().tools()}
    assert names == {"Read", "Grep", "Glob", "Bash"}


def test_system_prompt_is_read_only_review():
    p = review_bash.SYSTEM_PROMPT.lower()
    assert "review" in p
    assert "read-only" in p
    assert "do not modify" in p
