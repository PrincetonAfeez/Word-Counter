"""Normalization utilities for the word_counter package."""

from __future__ import annotations

import re
import string
import unicodedata
from dataclasses import dataclass
from typing import Protocol


class Normalizer(Protocol):
    def normalize(self, text: str) -> str:
        """Return normalized text."""


@dataclass(frozen=True)
class CaseFolder:
    def normalize(self, text: str) -> str:
        return text.casefold()


@dataclass(frozen=True)
class DiacriticFolder:
    def normalize(self, text: str) -> str:
        decomposed = unicodedata.normalize("NFKD", text)
        return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


@dataclass(frozen=True)
class PunctuationStripper:
    preserve_sentence_boundaries: bool = True

    def normalize(self, text: str) -> str:
        punctuation = string.punctuation
        if self.preserve_sentence_boundaries:
            punctuation = punctuation.replace(".", "").replace("!", "").replace("?", "")
        return text.translate(str.maketrans(punctuation, " " * len(punctuation)))


@dataclass(frozen=True)
class NumberStripper:
    def normalize(self, text: str) -> str:
        return re.sub(r"\d+", " ", text)


@dataclass(frozen=True)
class NormalizationPipeline:
    normalizers: tuple[Normalizer, ...] = ()

    def normalize(self, text: str) -> str:
        for normalizer in self.normalizers:
            text = normalizer.normalize(text)
        return text
