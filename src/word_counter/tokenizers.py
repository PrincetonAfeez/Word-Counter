"""Tokenizer utilities for the word_counter package."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Protocol

from .exceptions import TokenizerError
from .models import Token, TokenType

WORDISH_TYPES = {TokenType.WORD, TokenType.NUMBER, TokenType.URL, TokenType.EMAIL}


class Tokenizer(Protocol):
    @property
    def name(self) -> str:
        """Human-readable tokenizer name."""

    def tokenize(self, text: str) -> Iterator[Token]:
        """Yield tokens from text."""


def classify_token(value: str) -> TokenType:
    if not value:
        return TokenType.WHITESPACE
    if value.isspace():
        return TokenType.WHITESPACE
    if _EMAIL_RE.fullmatch(value):
        return TokenType.EMAIL
    if _URL_RE.fullmatch(value):
        return TokenType.URL
    if value.isnumeric():
        return TokenType.NUMBER
    if _EMOJI_RE.fullmatch(value):
        return TokenType.EMOJI
    if any(ch.isalpha() for ch in value):
        return TokenType.WORD
    return TokenType.PUNCTUATION


@dataclass(frozen=True)
class WhitespaceTokenizer:
    name: str = "whitespace"

    def tokenize(self, text: str) -> Iterator[Token]:
        for match in re.finditer(r"\S+|\s+", text, flags=re.UNICODE):
            value = match.group(0)
            yield Token(
                value=value,
                type=classify_token(value),
                start=match.start(),
                end=match.end(),
            )


@dataclass(frozen=True)
class RegexTokenizer:
    name: str = "regex"

    def tokenize(self, text: str) -> Iterator[Token]:
        for match in re.finditer(r"\w+|[^\w\s]+|\s+", text, flags=re.UNICODE):
            value = match.group(0)
            yield Token(
                value=value,
                type=classify_token(value),
                start=match.start(),
                end=match.end(),
            )


@dataclass(frozen=True)
class SmartTokenizer:
    name: str = "smart"

    def tokenize(self, text: str) -> Iterator[Token]:
        for match in _SMART_RE.finditer(text):
            group = match.lastgroup or "punctuation"
            value = match.group(0)
            token_type = _SMART_GROUP_TYPES[group]
            yield Token(value=value, type=token_type, start=match.start(), end=match.end())


@dataclass(frozen=True)
class NgramTokenizer:
    inner: Tokenizer
    n: int = 2
    name: str = "ngram"

    def __post_init__(self) -> None:
        if self.n < 1:
            msg = "n-gram size must be at least 1"
            raise TokenizerError(msg)

    def tokenize(self, text: str) -> Iterator[Token]:
        words = [token for token in self.inner.tokenize(text) if token.type in WORDISH_TYPES]
        if self.n == 1:
            yield from words
            return
        for index in range(0, max(0, len(words) - self.n + 1)):
            window = words[index : index + self.n]
            yield Token(
                value=" ".join(token.value for token in window),
                type=TokenType.WORD,
                start=window[0].start,
                end=window[-1].end,
            )


class TokenizerRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, Callable[[], Tokenizer]] = {
            "whitespace": WhitespaceTokenizer,
            "regex": RegexTokenizer,
            "smart": SmartTokenizer,
        }

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted((*self._factories.keys(), "ngram")))

    def create(self, name: str) -> Tokenizer:
        normalized = name.casefold()
        if normalized.startswith("ngram"):
            parts = normalized.split(":")
            n = int(parts[1]) if len(parts) > 1 and parts[1] else 2
            inner_name = parts[2] if len(parts) > 2 and parts[2] else "smart"
            return NgramTokenizer(inner=self.create(inner_name), n=n)
        try:
            return self._factories[normalized]()
        except KeyError as exc:
            msg = f"Unknown tokenizer '{name}'. Available: {', '.join(self.names)}"
            raise TokenizerError(msg) from exc
        except ValueError as exc:
            msg = f"Invalid tokenizer specification '{name}'"
            raise TokenizerError(msg) from exc


_URL_RE = re.compile(r"https?://[^\s]+|www\.[^\s]+", flags=re.IGNORECASE)
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF]+")
_SMART_RE = re.compile(
    r"(?P<url>https?://[^\s]+|www\.[^\s]+)"
    r"|(?P<email>[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})"
    r"|(?P<word>[^\W\d_]+(?:['\u2019-][^\W\d_]+)*)"
    r"|(?P<number>\d+(?:[.,]\d+)*)"
    r"|(?P<emoji>[\U0001F300-\U0001FAFF]+)"
    r"|(?P<whitespace>\s+)"
    r"|(?P<punctuation>[^\w\s])",
    flags=re.UNICODE | re.IGNORECASE,
)
_SMART_GROUP_TYPES = {
    "url": TokenType.URL,
    "email": TokenType.EMAIL,
    "word": TokenType.WORD,
    "number": TokenType.NUMBER,
    "emoji": TokenType.EMOJI,
    "whitespace": TokenType.WHITESPACE,
    "punctuation": TokenType.PUNCTUATION,
}
