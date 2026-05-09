"""Package tests for the word_counter package."""

from __future__ import annotations

import word_counter


def test_package_version_is_semantic_string() -> None:
    assert isinstance(word_counter.__version__, str)
    assert word_counter.__version__


def test_public_exports_match_documented_api() -> None:
    names = {
        "ReadabilityScore",
        "TextStats",
        "Token",
        "TokenType",
        "WordFrequency",
        "analyze_chunks",
        "analyze_text",
        "readability_scores",
    }
    assert set(word_counter.__all__) == names
    for name in names:
        assert hasattr(word_counter, name)
