"""Statistics helper utilities tests for the word_counter package."""

from __future__ import annotations

from collections import Counter

from word_counter.models import TextStats, Token, TokenType
from word_counter.stats import (
    _count_line_breaks,
    _countable,
    _estimate_syllables,
    _last_whitespace_index,
    _ParagraphCounter,
    _reading_ease_grade,
    _record_character_distribution,
    _SentenceSegmenter,
    analyze_chunks,
    analyze_text,
    readability_scores,
)
from word_counter.tokenizers import SmartTokenizer


def test_last_whitespace_index() -> None:
    assert _last_whitespace_index("abc def") == 3
    assert _last_whitespace_index("node") == -1


def test_count_line_breaks_crlf_and_lf() -> None:
    assert _count_line_breaks("a\nb") == 1
    assert _count_line_breaks("a\r\nb") == 1
    assert _count_line_breaks("a\rb\nc") == 2


def test_estimate_syllables_basic() -> None:
    assert _estimate_syllables("hello") >= 1
    assert _estimate_syllables("the") >= 1
    assert _estimate_syllables("123!!!") == 1


def test_reading_ease_grade_branches() -> None:
    assert "Very easy" in _reading_ease_grade(95)
    assert "Easy" in _reading_ease_grade(85)
    assert "Fairly easy" in _reading_ease_grade(75)
    assert "Standard" in _reading_ease_grade(65)
    assert "Fairly difficult" in _reading_ease_grade(55)
    assert "Difficult" in _reading_ease_grade(40)
    assert "Very difficult" in _reading_ease_grade(10)


def test_countable_respects_wordish_types() -> None:
    assert _countable(Token("a", TokenType.WORD)) is True
    assert _countable(Token(" ", TokenType.WHITESPACE)) is False


def test_record_character_distribution() -> None:
    letters: Counter[str] = Counter()
    punct: Counter[str] = Counter()
    _record_character_distribution("Hi, x!", letters, punct)
    assert letters["h"] >= 1
    assert letters["i"] >= 1
    assert punct[","] >= 1 or punct["!"] >= 1


def test_paragraph_counter_counts_blank_separated_blocks() -> None:
    p = _ParagraphCounter()
    p.feed("First line\n")
    p.feed("\n")
    p.feed("Second para\n")
    p.finish()
    assert p.count == 2


def test_sentence_segmenter_invokes_callback() -> None:
    seen: list[str] = []

    def cb(sentence: str) -> None:
        seen.append(sentence.strip())

    seg = _SentenceSegmenter(cb)
    seg.feed("One. Two!")
    seg.finish()
    assert "One." in seen
    assert "Two!" in seen


def test_analyze_chunks_empty_yields_zero_words() -> None:
    stats = analyze_chunks([], tokenizer=SmartTokenizer())
    assert stats.word_count == 0


def test_analyze_text_empty_string() -> None:
    stats = analyze_text("")
    assert stats.word_count == 0


def test_readability_scores_when_no_words() -> None:
    stats = TextStats()
    scores = readability_scores(stats)
    assert len(scores) == 3
    assert all("No words" in s.grade_level for s in scores)
