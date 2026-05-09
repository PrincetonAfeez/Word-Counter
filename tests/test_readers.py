"""Reader utilities tests for the word_counter package."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from word_counter.exceptions import EncodingError
from word_counter.readers import FileReader, StdinReader, StringReader, detect_encoding


def test_file_reader_yields_chunks(tmp_path: Path) -> None:
    path = tmp_path / "f.txt"
    path.write_text("abcdefghij", encoding="utf-8")
    chunks = list(FileReader(chunk_size=3).read_chunks(path))
    assert "".join(chunks) == "abcdefghij"


def test_file_reader_strict_encoding_raises_on_bad_bytes(tmp_path: Path) -> None:
    path = tmp_path / "latin1.bin"
    path.write_bytes("café".encode("latin-1"))
    reader = FileReader(encoding="utf-8", chunk_size=1024)
    with pytest.raises(EncodingError, match="Could not decode"):
        next(reader.read_chunks(path))


def test_string_reader_splits_on_chunk_size() -> None:
    reader = StringReader(chunk_size=4)
    chunks = list(reader.read_chunks("abcdefghij"))
    assert chunks == ["abcd", "efgh", "ij"]


def test_stdin_reader_reads_from_sys_stdin(monkeypatch) -> None:
    monkeypatch.setattr("word_counter.readers.sys.stdin", io.StringIO("abc"))
    chunks = list(StdinReader(chunk_size=2).read_chunks("-"))
    assert chunks == ["ab", "c"]


def test_detect_encoding_returns_string(tmp_path: Path) -> None:
    path = tmp_path / "x.txt"
    path.write_text("hello", encoding="utf-8")
    enc = detect_encoding(path)
    assert isinstance(enc, str)
    assert len(enc) > 0
