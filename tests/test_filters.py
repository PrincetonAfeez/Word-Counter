"""Filter utilities tests for the word_counter package."""

from __future__ import annotations

from word_counter.filters import (
    MaxLength,
    MinLength,
    OnlyAlpha,
    RegexFilter,
    StopwordFilter,
    compose_predicates,
)
from word_counter.models import Token, TokenType


def _word(value: str) -> Token:
    return Token(value=value, type=TokenType.WORD)


def test_min_length_predicate() -> None:
    assert MinLength(3)(_word("ab")) is False
    assert MinLength(3)(_word("abc")) is True


def test_max_length_predicate() -> None:
    assert MaxLength(2)(_word("abc")) is False
    assert MaxLength(3)(_word("abc")) is True


def test_only_alpha_accepts_letters_apostrophe_hyphen() -> None:
    assert OnlyAlpha()(_word("don't")) is True
    assert OnlyAlpha()(_word("hello-world")) is True
    assert OnlyAlpha()(_word("x1")) is False


def test_regex_filter_matches_substring() -> None:
    assert RegexFilter(r"foo")(_word("foobar")) is True
    assert RegexFilter(r"foo")(_word("bar")) is False


def test_stopword_filter_excludes_list() -> None:
    pred = StopwordFilter(frozenset({"the", "a"}))
    assert pred(_word("the")) is False
    assert pred(_word("cat")) is True


def test_compose_predicates_empty_is_always_true() -> None:
    pred = compose_predicates(())
    assert pred(_word("anything")) is True


def test_compose_predicates_all_must_pass() -> None:
    pred = compose_predicates((MinLength(2), MaxLength(4)))
    assert pred(_word("hi")) is True
    assert pred(_word("h")) is False
    assert pred(_word("hello")) is False
