"""Extended handler utilities tests for the word_counter package."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from word_counter.exceptions import UnsupportedFormatError
from word_counter.handlers import (
    JsonHandler,
    PlainTextHandler,
    _extract_json_strings,
    create_handler,
    detect_format,
)


def test_detect_format_stdin_and_suffix_and_default(tmp_path: Path) -> None:
    assert detect_format("-") == "txt"
    assert detect_format(tmp_path / "x.md") == "md"
    assert detect_format(tmp_path / "README") == "txt"


def test_plain_text_handler_file_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "t.txt"
    path.write_text("hello world", encoding="utf-8")
    text = "".join(PlainTextHandler().extract_text(path))
    assert text == "hello world"


def test_plain_text_handler_stdin(monkeypatch) -> None:
    monkeypatch.setattr("word_counter.readers.sys.stdin", io.StringIO("stdin data"))
    out = "".join(PlainTextHandler().extract_text("-"))
    assert out == "stdin data"


def test_create_handler_aliases(tmp_path: Path) -> None:
    path = tmp_path / "f.txt"
    path.write_text("x", encoding="utf-8")
    for fmt in ("txt", "text", "plain"):
        h = create_handler(fmt, path)
        assert "".join(h.extract_text(path)) == "x"


def test_create_handler_unknown_format_raises() -> None:
    with pytest.raises(UnsupportedFormatError, match="Unsupported format"):
        create_handler("weird", "x.weird")


def test_json_handler_invalid_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(UnsupportedFormatError, match="Invalid JSON"):
        "".join(JsonHandler().extract_text(path))


def test_extract_json_strings_scalars_and_collections() -> None:
    assert list(_extract_json_strings("leaf")) == ["leaf"]
    assert sorted(_extract_json_strings({"a": "x", "b": {"c": "y"}})) == ["x", "y"]
    assert list(_extract_json_strings(["u", {"v": "w"}])) == ["u", "w"]
