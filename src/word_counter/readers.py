"""Reader utilities for the word_counter package."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .exceptions import EncodingError


class StreamingReader(Protocol):
    def read_chunks(self, source: str | Path) -> Iterator[str]:
        """Yield text chunks from source."""


@dataclass(frozen=True)
class FileReader:
    encoding: str | None = None
    chunk_size: int = 64 * 1024

    def read_chunks(self, source: str | Path) -> Iterator[str]:
        path = Path(source)
        encoding = self.encoding or detect_encoding(path)
        try:
            with path.open("r", encoding=encoding, errors="strict", newline="") as handle:
                while True:
                    chunk = handle.read(self.chunk_size)
                    if not chunk:
                        break
                    yield chunk
        except UnicodeDecodeError as exc:
            msg = f"Could not decode {path} using {encoding}"
            raise EncodingError(msg) from exc


@dataclass(frozen=True)
class StdinReader:
    chunk_size: int = 64 * 1024

    def read_chunks(self, source: str | Path = "-") -> Iterator[str]:
        while True:
            chunk = sys.stdin.read(self.chunk_size)
            if not chunk:
                break
            yield chunk


@dataclass(frozen=True)
class StringReader:
    chunk_size: int = 64 * 1024

    def read_chunks(self, source: str | Path) -> Iterator[str]:
        text = str(source)
        for index in range(0, len(text), self.chunk_size):
            yield text[index : index + self.chunk_size]


def detect_encoding(path: Path) -> str:
    try:
        import chardet  # type: ignore[import-not-found]
    except ImportError:
        return "utf-8-sig"
    sample = path.read_bytes()[:8192]
    result = chardet.detect(sample)
    return str(result.get("encoding") or "utf-8-sig")
