"""Tokenizer utilities tests for the word_counter package."""

from __future__ import annotations

import pytest

from word_counter.exceptions import TokenizerError
from word_counter.models import TokenType
from word_counter.tokenizers import (
    NgramTokenizer,
    RegexTokenizer,
    SmartTokenizer,
    TokenizerRegistry,
    WhitespaceTokenizer,
    classify_token,
)


def words(tokenizer, text: str) -> list[str]:
    return [
        token.value
        for token in tokenizer.tokenize(text)
        if token.type in {TokenType.WORD, TokenType.NUMBER, TokenType.URL, TokenType.EMAIL}
    ]


def test_smart_tokenizer_preserves_contractions_urls_and_email() -> None:
    text = "Don't email me@example.com; visit https://example.com/a-b."
    assert words(SmartTokenizer(), text) == [
        "Don't",
        "email",
        "me@example.com",
        "visit",
        "https://example.com/a-b.",
    ]


def test_regex_tokenizer_handles_unicode_words() -> None:
    assert words(RegexTokenizer(), "Café déjà vu") == ["Café", "déjà", "vu"]


def test_whitespace_tokenizer_is_naive_baseline() -> None:
    assert words(WhitespaceTokenizer(), "hello, world") == ["hello,", "world"]


def test_ngram_tokenizer_wraps_inner_tokenizer() -> None:
    tokenizer = NgramTokenizer(SmartTokenizer(), n=2)
    assert words(tokenizer, "one two three") == ["one two", "two three"]


def test_classify_token_variants() -> None:
    assert classify_token("") is TokenType.WHITESPACE
    assert classify_token("   ") is TokenType.WHITESPACE
    assert classify_token("a@b.co") is TokenType.EMAIL
    assert classify_token("https://ex.com") is TokenType.URL
    assert classify_token("42") is TokenType.NUMBER
    assert classify_token("hello") is TokenType.WORD
    assert classify_token("!!!") is TokenType.PUNCTUATION


def test_tokenizer_registry_create_builtin_and_ngram() -> None:
    reg = TokenizerRegistry()
    assert isinstance(reg.create("smart"), SmartTokenizer)
    assert isinstance(reg.create("ngram:2:smart"), NgramTokenizer)
    assert isinstance(reg.create("NGRAM::regex"), NgramTokenizer)


def test_tokenizer_registry_unknown_raises() -> None:
    with pytest.raises(TokenizerError, match="Unknown tokenizer"):
        TokenizerRegistry().create("not-real")


def test_tokenizer_registry_invalid_ngram_spec_raises() -> None:
    with pytest.raises(ValueError):
        TokenizerRegistry().create("ngram:xyz")


def test_ngram_tokenizer_rejects_non_positive_n() -> None:
    with pytest.raises(TokenizerError, match="n-gram size"):
        NgramTokenizer(SmartTokenizer(), n=0)


def test_tokenizer_registry_names_property() -> None:
    names = TokenizerRegistry().names
    assert "smart" in names
    assert "ngram" in names
