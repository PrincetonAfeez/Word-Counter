"""Statistics utilities for the word_counter package."""

from __future__ import annotations

import re
import string
import unicodedata
from collections import Counter
from collections.abc import Callable, Iterable

from .filters import TokenPredicate, compose_predicates
from .models import ReadabilityScore, TextStats, Token
from .normalization import CaseFolder, NormalizationPipeline, Normalizer
from .readers import StringReader
from .tokenizers import WORDISH_TYPES, SmartTokenizer, Tokenizer


def analyze_text(
    text: str,
    *,
    tokenizer: Tokenizer | None = None,
    normalizers: Iterable[Normalizer] | None = None,
    predicates: Iterable[TokenPredicate] | None = None,
    encoding: str = "utf-8",
    chunk_size: int = 64 * 1024,
) -> TextStats:
    selected_tokenizer: Tokenizer = tokenizer or SmartTokenizer()
    normalizer_tuple = tuple(normalizers if normalizers is not None else (CaseFolder(),))
    predicate_tuple = tuple(predicates or ())

    def rebuild(value: str) -> TextStats:
        return analyze_text(
            value,
            tokenizer=selected_tokenizer,
            normalizers=normalizer_tuple,
            predicates=predicate_tuple,
            encoding=encoding,
            chunk_size=chunk_size,
        )

    stats = analyze_chunks(
        StringReader(chunk_size=chunk_size).read_chunks(text),
        tokenizer=selected_tokenizer,
        normalizers=normalizer_tuple,
        predicates=predicate_tuple,
        encoding=encoding,
    )
    return TextStats(
        character_count=stats.character_count,
        character_count_no_whitespace=stats.character_count_no_whitespace,
        word_count=stats.word_count,
        line_count=stats.line_count,
        sentence_count=stats.sentence_count,
        paragraph_count=stats.paragraph_count,
        byte_count=stats.byte_count,
        word_frequencies=stats.word_frequencies,
        word_length_frequencies=stats.word_length_frequencies,
        sentence_word_count_frequencies=stats.sentence_word_count_frequencies,
        letter_frequencies=stats.letter_frequencies,
        punctuation_frequencies=stats.punctuation_frequencies,
        _raw_text=text,
        _rebuild_from_text=rebuild,
    )


def analyze_chunks(
    chunks: Iterable[str],
    *,
    tokenizer: Tokenizer | None = None,
    normalizers: Iterable[Normalizer] | None = None,
    predicates: Iterable[TokenPredicate] | None = None,
    encoding: str = "utf-8",
) -> TextStats:
    selected_tokenizer: Tokenizer = tokenizer or SmartTokenizer()
    normalizer_tuple = tuple(normalizers if normalizers is not None else (CaseFolder(),))
    pipeline = NormalizationPipeline(normalizer_tuple)
    predicate = compose_predicates(tuple(predicates or ()))

    character_count = 0
    character_count_no_whitespace = 0
    byte_count = 0
    line_breaks = 0
    last_char = ""
    word_frequencies: Counter[str] = Counter()
    word_length_frequencies: Counter[int] = Counter()
    letter_frequencies: Counter[str] = Counter()
    punctuation_frequencies: Counter[str] = Counter()
    sentence_word_counts: Counter[int] = Counter()
    paragraphs = _ParagraphCounter()
    sentences = _SentenceSegmenter(
        lambda sentence: _record_sentence(
            sentence,
            selected_tokenizer,
            pipeline,
            predicate,
            sentence_word_counts,
        )
    )

    token_tail = ""
    for chunk in chunks:
        if not chunk:
            continue
        character_count += len(chunk)
        character_count_no_whitespace += sum(1 for ch in chunk if not ch.isspace())
        byte_count += len(chunk.encode(encoding, errors="replace"))
        line_breaks += _count_line_breaks(chunk)
        last_char = chunk[-1]
        _record_character_distribution(chunk, letter_frequencies, punctuation_frequencies)
        paragraphs.feed(chunk)
        sentences.feed(chunk)
        token_tail = _process_token_segment(
            token_tail + chunk,
            final=False,
            tokenizer=selected_tokenizer,
            pipeline=pipeline,
            predicate=predicate,
            word_frequencies=word_frequencies,
            word_length_frequencies=word_length_frequencies,
        )

    if token_tail:
        _process_token_segment(
            token_tail,
            final=True,
            tokenizer=selected_tokenizer,
            pipeline=pipeline,
            predicate=predicate,
            word_frequencies=word_frequencies,
            word_length_frequencies=word_length_frequencies,
        )
    paragraphs.finish()
    sentences.finish()
    word_count = sum(word_frequencies.values())
    line_count = 0 if character_count == 0 else line_breaks + (0 if last_char in "\r\n" else 1)

    return TextStats(
        character_count=character_count,
        character_count_no_whitespace=character_count_no_whitespace,
        word_count=word_count,
        line_count=line_count,
        sentence_count=sum(sentence_word_counts.values()),
        paragraph_count=paragraphs.count,
        byte_count=byte_count,
        word_frequencies=word_frequencies,
        word_length_frequencies=word_length_frequencies,
        sentence_word_count_frequencies=sentence_word_counts,
        letter_frequencies=letter_frequencies,
        punctuation_frequencies=punctuation_frequencies,
    )


def readability_scores(stats: TextStats) -> list[ReadabilityScore]:
    if not stats.word_count:
        return [
            ReadabilityScore(0.0, "No words", "Flesch Reading Ease"),
            ReadabilityScore(0.0, "No words", "Flesch-Kincaid Grade"),
            ReadabilityScore(0.0, "No words", "Coleman-Liau Index"),
        ]
    words = stats.word_count
    sentences = max(1, stats.sentence_count)
    syllables = sum(
        _estimate_syllables(word) * count
        for word, count in stats.word_frequencies.items()
    )
    letters = sum(stats.letter_frequencies.values())
    reading_ease = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
    fk_grade = 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59
    coleman_liau = 0.0588 * (letters / words * 100) - 0.296 * (sentences / words * 100) - 15.8
    return [
        ReadabilityScore(reading_ease, _reading_ease_grade(reading_ease), "Flesch Reading Ease"),
        ReadabilityScore(fk_grade, f"Grade {max(0.0, fk_grade):.1f}", "Flesch-Kincaid Grade"),
        ReadabilityScore(coleman_liau, f"Grade {max(0.0, coleman_liau):.1f}", "Coleman-Liau Index"),
    ]


def _process_token_segment(
    text: str,
    *,
    final: bool,
    tokenizer: Tokenizer,
    pipeline: NormalizationPipeline,
    predicate: TokenPredicate,
    word_frequencies: Counter[str],
    word_length_frequencies: Counter[int],
) -> str:
    segment = text
    tail = ""
    if not final and text and not text[-1].isspace():
        split_at = _last_whitespace_index(text)
        if split_at == -1:
            return text
        segment = text[: split_at + 1]
        tail = text[split_at + 1 :]
    normalized = pipeline.normalize(segment)
    for token in tokenizer.tokenize(normalized):
        if _countable(token) and predicate(token):
            word_frequencies[token.value] += 1
            word_length_frequencies[len(token.value)] += 1
    return tail


def _record_sentence(
    sentence: str,
    tokenizer: Tokenizer,
    pipeline: NormalizationPipeline,
    predicate: TokenPredicate,
    sentence_word_counts: Counter[int],
) -> None:
    normalized = pipeline.normalize(sentence)
    count = sum(
        1
        for token in tokenizer.tokenize(normalized)
        if _countable(token) and predicate(token)
    )
    if count:
        sentence_word_counts[count] += 1


def _record_character_distribution(
    text: str,
    letters: Counter[str],
    punctuation: Counter[str],
) -> None:
    for ch in text:
        if ch.isalpha():
            letters[ch.casefold()] += 1
        elif ch in string.punctuation or unicodedata.category(ch).startswith("P"):
            punctuation[ch] += 1


def _countable(token: Token) -> bool:
    return token.type in WORDISH_TYPES


def _last_whitespace_index(text: str) -> int:
    for index in range(len(text) - 1, -1, -1):
        if text[index].isspace():
            return index
    return -1


def _count_line_breaks(text: str) -> int:
    crlf = text.count("\r\n")
    return text.count("\n") + text.count("\r") - crlf


def _estimate_syllables(word: str) -> int:
    cleaned = re.sub(r"[^a-z]", "", word.casefold())
    if not cleaned:
        return 1
    cleaned = re.sub(r"e\b", "", cleaned)
    groups = re.findall(r"[aeiouy]+", cleaned)
    return max(1, len(groups))


def _reading_ease_grade(score: float) -> str:
    if score >= 90:
        return "Very easy"
    if score >= 80:
        return "Easy"
    if score >= 70:
        return "Fairly easy"
    if score >= 60:
        return "Standard"
    if score >= 50:
        return "Fairly difficult"
    if score >= 30:
        return "Difficult"
    return "Very difficult"


class _ParagraphCounter:
    def __init__(self) -> None:
        self.count = 0
        self._in_paragraph = False
        self._buffer = ""

    def feed(self, text: str) -> None:
        self._buffer += text
        while True:
            match = re.search(r"\r\n|\n|\r", self._buffer)
            if not match:
                return
            line = self._buffer[: match.start()]
            self._process_line(line)
            self._buffer = self._buffer[match.end() :]

    def finish(self) -> None:
        if self._buffer:
            self._process_line(self._buffer)
            self._buffer = ""

    def _process_line(self, line: str) -> None:
        if line.strip():
            if not self._in_paragraph:
                self.count += 1
                self._in_paragraph = True
        else:
            self._in_paragraph = False


class _SentenceSegmenter:
    _boundary = re.compile(r"[.!?]+(?=\s|$)")

    def __init__(self, callback: Callable[[str], None]) -> None:
        self._callback = callback
        self._buffer = ""

    def feed(self, text: str) -> None:
        self._buffer += text
        self._drain(final=False)

    def finish(self) -> None:
        self._drain(final=True)
        if re.search(r"\w", self._buffer):
            self._callback(self._buffer)
        self._buffer = ""

    def _drain(self, *, final: bool) -> None:
        while True:
            match = self._boundary.search(self._buffer)
            if not match:
                return
            if not final and match.end() == len(self._buffer):
                return
            sentence = self._buffer[: match.end()]
            self._callback(sentence)
            self._buffer = self._buffer[match.end() :]
