"""Model utilities tests for the word_counter package."""

from __future__ import annotations

from collections import Counter

import pytest

from word_counter.models import (
    ReadabilityScore,
    TextStats,
    Token,
    TokenType,
    WordFrequency,
)


def test_token_dataclass_fields() -> None:
    t = Token(value="hi", type=TokenType.WORD, start=0, end=2)
    assert t.value == "hi" and t.type is TokenType.WORD


def test_word_frequency_fields() -> None:
    wf = WordFrequency(word="a", count=1, rank=1, percentage=10.0)
    assert wf.rank == 1 and wf.percentage == 10.0


def test_readability_score_fields() -> None:
    rs = ReadabilityScore(10.0, "Easy", "Test")
    assert rs.score == 10.0 and rs.algorithm_name == "Test"


def test_textstats_format_compact_default() -> None:
    stats = TextStats(word_count=2, character_count=10, line_count=1)
    assert "2 words" in format(stats, "")
    assert "2 words" in format(stats, "compact")


def test_textstats_format_full_and_table() -> None:
    stats = TextStats(word_count=1, character_count=5, line_count=1)
    full = format(stats, "full")
    assert "Words" in full
    table = format(stats, "table")
    assert "Words" in table


def test_textstats_format_unknown_raises() -> None:
    stats = TextStats()
    with pytest.raises(ValueError, match="Unknown TextStats format"):
        format(stats, "nope")


def test_textstats_properties_and_top_bottom_words() -> None:
    stats = TextStats(
        word_count=4,
        sentence_count=1,
        word_frequencies=Counter({"a": 2, "b": 1, "c": 1}),
        word_length_frequencies=Counter({1: 4}),
        sentence_word_count_frequencies=Counter({2: 1}),
    )
    assert stats.unique_word_count == 3
    assert stats.hapax_count == 2
    assert stats.type_token_ratio == 0.75
    assert 0 < stats.hapax_ratio <= 1
    assert stats.average_word_length == 1.0
    assert stats.median_word_length == 1.0
    assert stats.mode_word_length == 1
    assert stats.stdev_word_length == 0.0
    assert stats.average_words_per_sentence == 2.0
    assert stats.longest_sentence_words == 2
    assert stats.shortest_sentence_words == 2

    top = stats.top_words(limit=2, min_count=2)
    assert len(top) == 1 and top[0].word == "a"

    bottom = stats.bottom_words(limit=10, min_count=1)
    assert bottom[0].count <= bottom[-1].count or len(bottom) == 1


def test_textstats_summary_rows_and_to_dict() -> None:
    stats = TextStats(word_count=1, word_frequencies=Counter({"x": 1}))
    rows = stats.summary_rows()
    assert any(label == "Words" for label, _ in rows)
    d_all = stats.to_dict(include_frequencies=True)
    assert "word_frequencies" in d_all
    d_no = stats.to_dict(include_frequencies=False)
    assert "word_frequencies" not in d_no


def test_textstats_empty_derived_metrics() -> None:
    stats = TextStats()
    assert stats.unique_word_count == 0
    assert stats.hapax_count == 0
    assert stats.type_token_ratio == 0.0
    assert stats.hapax_ratio == 0.0
    assert stats.average_word_length == 0.0
    assert stats.median_word_length == 0.0
    assert stats.mode_word_length == 0
    assert stats.stdev_word_length == 0.0
    assert stats.average_words_per_sentence == 0.0
    assert stats.longest_sentence_words == 0
    assert stats.shortest_sentence_words == 0


def test_textstats_add_merges_counters_without_raw_text() -> None:
    a = TextStats(
        character_count=2,
        word_count=1,
        line_count=1,
        sentence_count=1,
        paragraph_count=1,
        byte_count=2,
        word_frequencies=Counter({"a": 1}),
    )
    b = TextStats(
        character_count=3,
        word_count=1,
        line_count=1,
        sentence_count=1,
        paragraph_count=1,
        byte_count=3,
        word_frequencies=Counter({"b": 1}),
    )
    c = a + b
    assert c.word_count == 2
    assert c.word_frequencies["a"] == 1 and c.word_frequencies["b"] == 1


def test_textstats_add_with_non_textstats_returns_notimplemented() -> None:
    assert TextStats().__add__(1) is NotImplemented


def test_textstats_add_raises_typeerror_for_bad_operand() -> None:
    with pytest.raises(TypeError):
        _ = TextStats() + 1
