"""Exceptions tests for the word_counter package."""

from __future__ import annotations

import pytest

from word_counter.exceptions import (
    EmptyInputError,
    EncodingError,
    TokenizerError,
    UnsupportedFormatError,
    WordCountError,
)


def test_exception_hierarchy() -> None:
    assert issubclass(UnsupportedFormatError, WordCountError)
    assert issubclass(EncodingError, WordCountError)
    assert issubclass(EmptyInputError, WordCountError)
    assert issubclass(TokenizerError, WordCountError)


def test_exceptions_can_be_raised_with_message() -> None:
    classes = (
        WordCountError,
        UnsupportedFormatError,
        EncodingError,
        EmptyInputError,
        TokenizerError,
    )
    for cls in classes:
        with pytest.raises(cls, match="msg"):
            raise cls("msg")
