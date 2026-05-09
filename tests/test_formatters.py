"""Formatting utilities tests for the word_counter package."""

from __future__ import annotations

from collections import Counter

import pytest

from word_counter.formatters import (
    ascii_bar_chart,
    create_formatter,
    format_diff,
    format_many,
    format_readability,
    format_word_frequencies,
)
from word_counter.models import ReadabilityScore, TextStats, WordFrequency


def _stats(words: dict[str, int] | None = None) -> TextStats:
    wc = Counter(words or {})
    total = sum(wc.values())
    return TextStats(
        character_count=max(10, total),
        word_count=total,
        line_count=1,
        sentence_count=1,
        paragraph_count=1,
        word_frequencies=wc,
    )


def test_create_formatter_plain_table_json_csv_markdown() -> None:
    stats = _stats({"a": 1})
    for name in ("plain", "PLAIN", "table", "json", "csv", "markdown", "md"):
        out = create_formatter(name).format_stats(stats)
        assert isinstance(out, str)
        assert len(out) > 0


def test_create_formatter_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown output format"):
        create_formatter("xml")


def test_plain_formatter_respects_no_color() -> None:
    stats = _stats({"hello": 2, "world": 1})
    out = create_formatter("plain", no_color=True).format_stats(stats)
    assert "\033[" not in out


def test_format_many_json_csv_plain_markdown() -> None:
    items = {"one": _stats({"x": 1}), "two": _stats({"y": 2})}
    assert "one" in format_many(items, output_format="json")
    assert "source" in format_many(items, output_format="csv")
    assert "Comparison" in format_many(items, output_format="plain")
    assert "| Source |" in format_many(items, output_format="markdown")


def test_format_word_frequencies_outputs() -> None:
    freqs = [
        WordFrequency(word="a", count=2, rank=1, percentage=50.0),
        WordFrequency(word="b", count=2, rank=2, percentage=50.0),
    ]
    assert "a" in format_word_frequencies(freqs, output_format="plain")
    assert '"word"' in format_word_frequencies(freqs, output_format="json")
    assert "rank" in format_word_frequencies(freqs, output_format="csv")
    assert "| Word |" in format_word_frequencies(freqs, output_format="markdown")


def test_format_readability_outputs() -> None:
    scores = [
        ReadabilityScore(80.0, "Easy", "Flesch Reading Ease"),
        ReadabilityScore(5.0, "Grade 5.0", "Flesch-Kincaid Grade"),
    ]
    assert "Flesch" in format_readability(scores, output_format="plain")
    assert "algorithm" in format_readability(scores, output_format="csv")
    assert "Flesch" in format_readability(scores, output_format="markdown")
    assert "grade_level" in format_readability(scores, output_format="json")


def test_ascii_bar_chart_empty_returns_empty_string() -> None:
    assert ascii_bar_chart([]) == ""


def test_ascii_bar_chart_non_empty_has_ranks(monkeypatch) -> None:
    freqs = [WordFrequency(word="hi", count=3, rank=1, percentage=100.0)]
    monkeypatch.setattr("word_counter.formatters._bar_character", lambda: "#")
    chart = ascii_bar_chart(freqs, width=8)
    assert "hi" in chart
    assert "3" in chart
    assert "#" in chart


def test_format_diff_json_markdown_plain() -> None:
    left = _stats({"a": 1})
    right = _stats({"a": 1, "b": 1})
    assert "delta" in format_diff("L", left, "R", right, output_format="json")
    assert "| Delta |" in format_diff("L", left, "R", right, output_format="markdown")
    assert "words" in format_diff("L", left, "R", right, output_format="plain")
