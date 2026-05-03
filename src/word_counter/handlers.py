"""Handler utilities for the word_counter package."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Protocol

from .exceptions import UnsupportedFormatError
from .readers import FileReader, StdinReader


class FormatHandler(Protocol):
    def extract_text(self, source: str | Path) -> Iterator[str]:
        """Yield text chunks extracted from source."""


@dataclass(frozen=True)
class PlainTextHandler:
    encoding: str | None = None
    chunk_size: int = 64 * 1024

    def extract_text(self, source: str | Path) -> Iterator[str]:
        if str(source) == "-":
            yield from StdinReader(chunk_size=self.chunk_size).read_chunks(source)
            return
        reader = FileReader(encoding=self.encoding, chunk_size=self.chunk_size)
        yield from reader.read_chunks(source)


@dataclass(frozen=True)
class MarkdownHandler:
    encoding: str | None = None
    chunk_size: int = 64 * 1024

    def extract_text(self, source: str | Path) -> Iterator[str]:
        text = _read_all(source, self.encoding, self.chunk_size)
        text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
        text = re.sub(r"`([^`]*)`", r"\1", text)
        text = re.sub(r"!\[([^\]]*)]\([^)]+\)", r"\1", text)
        text = re.sub(r"\[([^\]]+)]\([^)]+\)", r"\1", text)
        text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s{0,3}[-*+]\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"[*_~>#|]", " ", text)
        yield text


@dataclass(frozen=True)
class HtmlHandler:
    encoding: str | None = None
    chunk_size: int = 64 * 1024

    def extract_text(self, source: str | Path) -> Iterator[str]:
        parser = _TextHTMLParser()
        for chunk in PlainTextHandler(self.encoding, self.chunk_size).extract_text(source):
            parser.feed(chunk)
            text = parser.pop_text()
            if text:
                yield text
        parser.close()
        text = parser.pop_text()
        if text:
            yield text


@dataclass(frozen=True)
class JsonHandler:
    encoding: str | None = None
    chunk_size: int = 64 * 1024

    def extract_text(self, source: str | Path) -> Iterator[str]:
        text = _read_all(source, self.encoding, self.chunk_size)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            msg = f"Invalid JSON in {source}"
            raise UnsupportedFormatError(msg) from exc
        yield " ".join(_extract_json_strings(data))


@dataclass(frozen=True)
class DocxHandler:
    encoding: str | None = None
    chunk_size: int = 64 * 1024

    def extract_text(self, source: str | Path) -> Iterator[str]:
        try:
            import docx  # type: ignore[import-not-found]
        except ImportError as exc:
            msg = "DOCX support requires: pip install word-counter[docx]"
            raise UnsupportedFormatError(msg) from exc
        document = docx.Document(str(source))
        yield "\n".join(paragraph.text for paragraph in document.paragraphs)


@dataclass(frozen=True)
class PdfHandler:
    encoding: str | None = None
    chunk_size: int = 64 * 1024

    def extract_text(self, source: str | Path) -> Iterator[str]:
        try:
            from pypdf import PdfReader  # type: ignore[import-not-found]
        except ImportError as exc:
            msg = "PDF support requires: pip install word-counter[pdf]"
            raise UnsupportedFormatError(msg) from exc
        reader = PdfReader(str(source))
        for page in reader.pages:
            yield page.extract_text() or ""


def create_handler(
    input_format: str | None,
    source: str | Path,
    *,
    encoding: str | None = None,
    chunk_size: int = 64 * 1024,
) -> FormatHandler:
    format_name = (input_format or detect_format(source)).casefold()
    factories: dict[str, Callable[..., FormatHandler]] = {
        "txt": PlainTextHandler,
        "text": PlainTextHandler,
        "plain": PlainTextHandler,
        "md": MarkdownHandler,
        "markdown": MarkdownHandler,
        "html": HtmlHandler,
        "htm": HtmlHandler,
        "json": JsonHandler,
        "docx": DocxHandler,
        "pdf": PdfHandler,
    }
    try:
        return factories[format_name](encoding=encoding, chunk_size=chunk_size)
    except KeyError as exc:
        msg = f"Unsupported format '{format_name}'"
        raise UnsupportedFormatError(msg) from exc


def detect_format(source: str | Path) -> str:
    if str(source) == "-":
        return "txt"
    suffix = Path(source).suffix.lower().lstrip(".")
    return suffix or "txt"


def _read_all(source: str | Path, encoding: str | None, chunk_size: int) -> str:
    return "".join(PlainTextHandler(encoding, chunk_size).extract_text(source))


def _extract_json_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _extract_json_strings(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _extract_json_strings(item)


class _TextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)

    def pop_text(self) -> str:
        text = " ".join(self._parts)
        self._parts.clear()
        return text
