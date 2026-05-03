"""CLI tests for the word_counter package."""

from __future__ import annotations

from pathlib import Path

from word_counter.cli import main


def test_default_command_prints_stats(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.setenv("WORDCOUNT_NO_HISTORY", "1")
    path = tmp_path / "sample.txt"
    path.write_text("Hello hello world.", encoding="utf-8")
    assert main([str(path), "--format", "table"]) == 0
    output = capsys.readouterr().out
    assert "Words" in output
    assert "3" in output


def test_top_command_can_emit_json(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.setenv("WORDCOUNT_NO_HISTORY", "1")
    path = tmp_path / "sample.txt"
    path.write_text("red blue red", encoding="utf-8")
    assert main(["top", str(path), "-n", "1", "--format", "json"]) == 0
    assert '"word": "red"' in capsys.readouterr().out


def test_freq_command_normalizes_query(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.setenv("WORDCOUNT_NO_HISTORY", "1")
    path = tmp_path / "sample.txt"
    path.write_text("Example example", encoding="utf-8")
    assert main(["freq", str(path), "--word", "EXAMPLE"]) == 0
    assert "example: 2" in capsys.readouterr().out
