import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "examples"))

import review_openai


def test_review_openai_registry_is_read_only():
    names = {t.name for t in review_openai.read_only_registry().tools()}
    assert names == {"Read", "Grep", "Glob"}


def test_review_openai_registers_log_and_base_url_flags():
    import inspect

    src = inspect.getsource(review_openai.main)
    assert "--log" in src
    assert "--base-url" in src
