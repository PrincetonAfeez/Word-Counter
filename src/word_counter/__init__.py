"""Streaming-first word counting and text statistics."""

from __future__ import annotations

from .models import ReadabilityScore, TextStats, Token, TokenType, WordFrequency
from .stats import analyze_chunks, analyze_text, readability_scores

__all__ = [
    "ReadabilityScore",
    "TextStats",
    "Token",
    "TokenType",
    "WordFrequency",
    "analyze_chunks",
    "analyze_text",
    "readability_scores",
]

__version__ = "0.1.0"
