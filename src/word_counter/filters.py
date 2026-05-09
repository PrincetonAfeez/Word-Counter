"""Filter utilities for the word_counter package."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from .models import Token, TokenType


class TokenPredicate(Protocol):
    def __call__(self, token: Token) -> bool:
        """Return True when the token should be counted."""


@dataclass(frozen=True)
class MinLength:
    length: int

    def __call__(self, token: Token) -> bool:
        return len(token.value) >= self.length


@dataclass(frozen=True)
class MaxLength:
    length: int

    def __call__(self, token: Token) -> bool:
        return len(token.value) <= self.length


@dataclass(frozen=True)
class OnlyAlpha:
    def __call__(self, token: Token) -> bool:
        stripped = token.value.replace("'", "").replace("-", "")
        return token.type == TokenType.WORD and stripped.isalpha()


@dataclass(frozen=True)
class RegexFilter:
    pattern: str
    _compiled: re.Pattern[str] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_compiled", re.compile(self.pattern))

    def __call__(self, token: Token) -> bool:
        return bool(self._compiled.search(token.value))


@dataclass(frozen=True)
class StopwordFilter:
    stopwords: frozenset[str]

    def __call__(self, token: Token) -> bool:
        return token.value.casefold() not in self.stopwords


def compose_predicates(predicates: tuple[TokenPredicate, ...]) -> TokenPredicate:
    def predicate(token: Token) -> bool:
        return all(check(token) for check in predicates)

    return predicate
