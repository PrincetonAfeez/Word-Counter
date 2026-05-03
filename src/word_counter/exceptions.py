"""Exceptions for the word_counter package."""

from __future__ import annotations


class WordCountError(Exception):
    """Base class for word-counter errors."""


class UnsupportedFormatError(WordCountError):
    """Raised when a source format cannot be read."""


class EncodingError(WordCountError):
    """Raised when text cannot be decoded with the selected encoding."""


class EmptyInputError(WordCountError):
    """Raised when a command needs input but none was supplied."""


class TokenizerError(WordCountError):
    """Raised when a tokenizer cannot be created or used."""
