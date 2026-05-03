"""Normalization utilities tests for the word_counter package."""

from __future__ import annotations

from word_counter.normalization import (
    CaseFolder,
    DiacriticFolder,
    NormalizationPipeline,
    NumberStripper,
    PunctuationStripper,
)


def test_case_folder_casefolds() -> None:
    assert CaseFolder().normalize("HELLO") == "hello"
    assert CaseFolder().normalize("Straße") == "Straße".casefold()


def test_diacritic_folder_strips_combining_marks() -> None:
    assert DiacriticFolder().normalize("café") == "cafe"


def test_punctuation_stripper_default_preserves_sentence_endings() -> None:
    out = PunctuationStripper().normalize("Hello, world! Fine? Yes.")
    assert "!" in out
    assert "?" in out
    assert "." in out


def test_punctuation_stripper_can_strip_all_punctuation() -> None:
    out = PunctuationStripper(preserve_sentence_boundaries=False).normalize("Hi, there!")
    assert "," not in out
    assert "!" not in out


def test_number_stripper_replaces_digits_with_spaces() -> None:
    assert NumberStripper().normalize("a1b2c") == "a b c"


def test_normalization_pipeline_applies_in_order() -> None:
    pipeline = NormalizationPipeline((CaseFolder(), NumberStripper()))
    assert pipeline.normalize("HELLO2world") == "hello world"
