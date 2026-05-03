"""Model utilities for the word_counter package."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from statistics import median, stdev


class TokenType(Enum):
    WORD = auto()
    NUMBER = auto()
    PUNCTUATION = auto()
    WHITESPACE = auto()
    EMOJI = auto()
    URL = auto()
    EMAIL = auto()


@dataclass(frozen=True)
class Token:
    value: str
    type: TokenType
    start: int = 0
    end: int = 0


@dataclass(frozen=True)
class WordFrequency:
    word: str
    count: int
    rank: int
    percentage: float


@dataclass(frozen=True)
class ReadabilityScore:
    score: float
    grade_level: str
    algorithm_name: str


@dataclass(frozen=True)
class TextStats:
    character_count: int = 0
    character_count_no_whitespace: int = 0
    word_count: int = 0
    line_count: int = 0
    sentence_count: int = 0
    paragraph_count: int = 0
    byte_count: int = 0
    word_frequencies: Counter[str] = field(default_factory=Counter)
    word_length_frequencies: Counter[int] = field(default_factory=Counter)
    sentence_word_count_frequencies: Counter[int] = field(default_factory=Counter)
    letter_frequencies: Counter[str] = field(default_factory=Counter)
    punctuation_frequencies: Counter[str] = field(default_factory=Counter)
    _raw_text: str | None = field(default=None, repr=False, compare=False)
    _rebuild_from_text: Callable[[str], TextStats] | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    def __add__(self, other: object) -> TextStats:
        if not isinstance(other, TextStats):
            return NotImplemented
        if self._raw_text is not None and other._raw_text is not None and self._rebuild_from_text:
            return self._rebuild_from_text(self._raw_text + other._raw_text)
        return TextStats(
            character_count=self.character_count + other.character_count,
            character_count_no_whitespace=(
                self.character_count_no_whitespace + other.character_count_no_whitespace
            ),
            word_count=self.word_count + other.word_count,
            line_count=self.line_count + other.line_count,
            sentence_count=self.sentence_count + other.sentence_count,
            paragraph_count=self.paragraph_count + other.paragraph_count,
            byte_count=self.byte_count + other.byte_count,
            word_frequencies=Counter(self.word_frequencies) + Counter(other.word_frequencies),
            word_length_frequencies=(
                Counter(self.word_length_frequencies) + Counter(other.word_length_frequencies)
            ),
            sentence_word_count_frequencies=(
                Counter(self.sentence_word_count_frequencies)
                + Counter(other.sentence_word_count_frequencies)
            ),
            letter_frequencies=Counter(self.letter_frequencies) + Counter(other.letter_frequencies),
            punctuation_frequencies=(
                Counter(self.punctuation_frequencies) + Counter(other.punctuation_frequencies)
            ),
        )

    def __format__(self, spec: str) -> str:
        spec = spec or "compact"
        if spec == "compact":
            return (
                f"{self.word_count} words, {self.character_count} characters, "
                f"{self.line_count} lines"
            )
        if spec == "full":
            return "\n".join(f"{label}: {value}" for label, value in self.summary_rows())
        if spec == "table":
            rows = self.summary_rows()
            width = max(len(label) for label, _ in rows)
            return "\n".join(f"{label:<{width}}  {value}" for label, value in rows)
        msg = f"Unknown TextStats format specifier: {spec}"
        raise ValueError(msg)

    @property
    def unique_word_count(self) -> int:
        return len(self.word_frequencies)

    @property
    def hapax_count(self) -> int:
        return sum(1 for count in self.word_frequencies.values() if count == 1)

    @property
    def type_token_ratio(self) -> float:
        return self.unique_word_count / self.word_count if self.word_count else 0.0

    @property
    def hapax_ratio(self) -> float:
        return self.hapax_count / self.unique_word_count if self.unique_word_count else 0.0

    @property
    def average_word_length(self) -> float:
        if not self.word_count:
            return 0.0
        total = sum(length * count for length, count in self.word_length_frequencies.items())
        return total / self.word_count

    @property
    def median_word_length(self) -> float:
        values = _expand_counter(self.word_length_frequencies)
        return float(median(values)) if values else 0.0

    @property
    def mode_word_length(self) -> int:
        if not self.word_length_frequencies:
            return 0
        max_count = max(self.word_length_frequencies.values())
        return min(
            length
            for length, count in self.word_length_frequencies.items()
            if count == max_count
        )

    @property
    def stdev_word_length(self) -> float:
        values = _expand_counter(self.word_length_frequencies)
        return float(stdev(values)) if len(values) > 1 else 0.0

    @property
    def average_words_per_sentence(self) -> float:
        if not self.sentence_count:
            return 0.0
        total = sum(
            words * count for words, count in self.sentence_word_count_frequencies.items()
        )
        return total / self.sentence_count

    @property
    def longest_sentence_words(self) -> int:
        return max(self.sentence_word_count_frequencies, default=0)

    @property
    def shortest_sentence_words(self) -> int:
        positive_lengths = [length for length in self.sentence_word_count_frequencies if length > 0]
        return min(positive_lengths, default=0)

    def top_words(self, limit: int = 10, min_count: int = 1) -> list[WordFrequency]:
        pairs = [
            (word, count)
            for word, count in self.word_frequencies.most_common()
            if count >= min_count
        ][:limit]
        return [
            WordFrequency(
                word=word,
                count=count,
                rank=index,
                percentage=(count / self.word_count * 100) if self.word_count else 0.0,
            )
            for index, (word, count) in enumerate(pairs, start=1)
        ]

    def bottom_words(self, limit: int = 10, min_count: int = 1) -> list[WordFrequency]:
        pairs = sorted(
            (
                (word, count)
                for word, count in self.word_frequencies.items()
                if count >= min_count
            ),
            key=lambda item: (item[1], item[0]),
        )[:limit]
        return [
            WordFrequency(
                word=word,
                count=count,
                rank=index,
                percentage=(count / self.word_count * 100) if self.word_count else 0.0,
            )
            for index, (word, count) in enumerate(pairs, start=1)
        ]

    def summary_rows(self) -> list[tuple[str, object]]:
        return [
            ("Characters", self.character_count),
            ("Characters without whitespace", self.character_count_no_whitespace),
            ("Bytes", self.byte_count),
            ("Words", self.word_count),
            ("Unique words", self.unique_word_count),
            ("Lines", self.line_count),
            ("Sentences", self.sentence_count),
            ("Paragraphs", self.paragraph_count),
            ("Average word length", f"{self.average_word_length:.2f}"),
            ("Median word length", f"{self.median_word_length:.2f}"),
            ("Mode word length", self.mode_word_length),
            ("Word length stdev", f"{self.stdev_word_length:.2f}"),
            ("Average words per sentence", f"{self.average_words_per_sentence:.2f}"),
            ("Longest sentence words", self.longest_sentence_words),
            ("Shortest sentence words", self.shortest_sentence_words),
            ("Type-token ratio", f"{self.type_token_ratio:.4f}"),
            ("Hapax legomena", self.hapax_count),
            ("Hapax ratio", f"{self.hapax_ratio:.4f}"),
        ]

    def to_dict(self, *, include_frequencies: bool = True) -> dict[str, object]:
        data: dict[str, object] = {
            "characters": self.character_count,
            "characters_without_whitespace": self.character_count_no_whitespace,
            "bytes": self.byte_count,
            "words": self.word_count,
            "unique_words": self.unique_word_count,
            "lines": self.line_count,
            "sentences": self.sentence_count,
            "paragraphs": self.paragraph_count,
            "average_word_length": self.average_word_length,
            "median_word_length": self.median_word_length,
            "mode_word_length": self.mode_word_length,
            "stdev_word_length": self.stdev_word_length,
            "average_words_per_sentence": self.average_words_per_sentence,
            "longest_sentence_words": self.longest_sentence_words,
            "shortest_sentence_words": self.shortest_sentence_words,
            "type_token_ratio": self.type_token_ratio,
            "hapax_legomena": self.hapax_count,
            "hapax_ratio": self.hapax_ratio,
        }
        if include_frequencies:
            data["word_frequencies"] = dict(self.word_frequencies)
            data["letter_frequencies"] = dict(self.letter_frequencies)
            data["punctuation_frequencies"] = dict(self.punctuation_frequencies)
        return data


def _expand_counter(counter: Counter[int]) -> list[int]:
    values: list[int] = []
    for value, count in sorted(counter.items()):
        values.extend([value] * count)
    return values
