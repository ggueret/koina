import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "examples"))

import review_multi


def test_default_dimensions():
    assert set(review_multi.DIMENSIONS) == {"correctness", "performance", "security"}


def test_dimension_prompt_includes_focus_and_read_only():
    prompt = review_multi.dimension_prompt("Focus ONLY on security: injection.")
    assert "Focus ONLY on security: injection." in prompt
    assert "read-only review" in prompt.lower()


def test_registry_is_read_only():
    names = {t.name for t in review_multi.read_only_registry().tools()}
    assert names == {"Read", "Grep", "Glob"}


def test_synthesis_prompt_merges():
    p = review_multi.SYNTHESIS_PROMPT.lower()
    assert "merge" in p
    assert "deduplicate" in p
