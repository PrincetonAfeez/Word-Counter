"""Extended CLI tests for the word_counter package."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from word_counter.cli import (
    _expand_sources,
    _normalize_argv,
    _normalize_query,
    _normalizers_from_args,
    _predicates_from_args,
    _source_label,
    analyze_source,
    build_parser,
    command_stats,
    dispatch,
    main,
)
from word_counter.exceptions import EmptyInputError, UnsupportedFormatError


def _merge_args(tmp_path, **overrides):
    p = tmp_path / "a.txt"
    p.write_text("one two", encoding="utf-8")
    base = dict(
        command="merge",
        sources=[str(p)],
        tokenizer="smart",
        output_format="plain",
        input_format=None,
        language="en",
        encoding=None,
        chunk_size=1024,
        no_color=True,
        ignore_case=True,
        fold_diacritics=False,
        strip_punctuation=False,
        strip_numbers=False,
        ignore_stopwords=False,
        min_length=None,
        max_length=None,
        min_count=1,
        only_alpha=False,
        grep=None,
        top=10,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_main_version_flag(capsys) -> None:
    assert main(["--version"]) == 0
    assert "word-counter" in capsys.readouterr().out


def test_main_default_stats_implicit_command(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.setenv("WORDCOUNT_NO_HISTORY", "1")
    path = tmp_path / "z.txt"
    path.write_text("a b c", encoding="utf-8")
    assert main([str(path), "--format", "json"]) == 0
    assert '"words"' in capsys.readouterr().out


def test_main_merge_and_diff_and_readability(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.setenv("WORDCOUNT_NO_HISTORY", "1")
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("One two.", encoding="utf-8")
    b.write_text("One two three.", encoding="utf-8")
    assert main(["merge", str(a), str(b), "--format", "table"]) == 0
    assert "Words" in capsys.readouterr().out

    assert main(["diff", str(a), str(b), "--format", "json"]) == 0
    assert "delta" in capsys.readouterr().out

    assert main(["readability", str(a), "--format", "csv"]) == 0
    assert "Flesch" in capsys.readouterr().out


def test_main_compare_markdown(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.setenv("WORDCOUNT_NO_HISTORY", "1")
    for name in ("x.txt", "y.txt"):
        (tmp_path / name).write_text("word", encoding="utf-8")
    assert main(
        ["compare", str(tmp_path / "x.txt"), str(tmp_path / "y.txt"), "--format", "markdown"]
    ) == 0
    assert "| Source |" in capsys.readouterr().out


def test_main_history_plain_and_json(capsys, monkeypatch) -> None:
    monkeypatch.setenv("WORDCOUNT_NO_HISTORY", "1")
    fake_records = [
        {"timestamp": "t1", "command": "stats", "sources": ["s.txt"], "summary": {"words": 1}},
    ]
    monkeypatch.setattr("word_counter.cli.history_last", lambda last: fake_records[-last:])
    assert main(["history", "--last", "5", "--format", "plain"]) == 0
    assert "stats" in capsys.readouterr().out

    assert main(["history", "--format", "json"]) == 0
    assert "stats" in capsys.readouterr().out


def test_main_history_empty_message(capsys, monkeypatch) -> None:
    monkeypatch.setenv("WORDCOUNT_NO_HISTORY", "1")
    monkeypatch.setattr("word_counter.cli.history_last", lambda last: [])
    assert main(["history"]) == 0
    assert "No history" in capsys.readouterr().out


def test_main_stats_multiple_sources(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.setenv("WORDCOUNT_NO_HISTORY", "1")
    (tmp_path / "1.txt").write_text("a", encoding="utf-8")
    (tmp_path / "2.txt").write_text("b", encoding="utf-8")
    assert main(["stats", str(tmp_path / "1.txt"), str(tmp_path / "2.txt"), "--format", "csv"]) == 0
    assert "source" in capsys.readouterr().out


def test_main_returns_two_on_wordcount_error(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.setenv("WORDCOUNT_NO_HISTORY", "1")
    bad = tmp_path / "x.json"
    bad.write_text("{", encoding="utf-8")
    assert main(["stats", str(bad)]) == 2
    assert "wordcount:" in capsys.readouterr().err


def test_build_parser_accepts_stats_with_dash_default() -> None:
    parser = build_parser()
    args = parser.parse_args(["stats", "-"])
    assert args.command == "stats"
    assert args.sources == ["-"]


def test_dispatch_unknown_command_raises() -> None:
    with pytest.raises(ValueError, match="Unknown command"):
        dispatch(SimpleNamespace(command="not-a-command"))


def test_dispatch_merge_empty_sources_raises(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("word_counter.cli._expand_sources", lambda sources: [])
    args = _merge_args(tmp_path)
    with pytest.raises(EmptyInputError, match="merge requires"):
        dispatch(args)


def test_command_stats_single_source(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("WORDCOUNT_NO_HISTORY", "1")
    path = tmp_path / "q.txt"
    path.write_text("alpha beta", encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(["stats", str(path), "--format", "table"])
    out = command_stats(args)
    assert "Words" in out


def test_normalize_argv_inserts_default_stats_command() -> None:
    assert _normalize_argv([]) == ["stats", "-"]
    assert _normalize_argv(["file.txt"]) == ["stats", "file.txt"]
    assert _normalize_argv(["top", "a.txt"]) == ["top", "a.txt"]


def test_source_label_stdin_and_basename(tmp_path: Path) -> None:
    assert _source_label("-") == "stdin"
    nested = tmp_path / "d" / "f.txt"
    nested.parent.mkdir()
    nested.write_text("x", encoding="utf-8")
    assert _source_label(str(nested)) == "f.txt"


def test_expand_sources_preserves_stdin_and_globs(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("1", encoding="utf-8")
    assert _expand_sources(["-"]) == ["-"]
    globs = _expand_sources([str(tmp_path / "*.txt")])
    assert len(globs) == 1
    assert _expand_sources(["missing_pattern_xyz_123.txt"]) == ["missing_pattern_xyz_123.txt"]


def test_normalizers_predicates_and_normalize_query(tmp_path: Path) -> None:
    path = tmp_path / "p.txt"
    path.write_text("x", encoding="utf-8")
    parser = build_parser()
    args_default = parser.parse_args(["stats", str(path)])
    norms_default = _normalizers_from_args(args_default)
    assert len(norms_default) == 1
    assert _normalize_query("HELLO", norms_default) == "hello"

    args_full = parser.parse_args(
        [
            "stats",
            str(path),
            "--case-sensitive",
            "--fold-diacritics",
            "--strip-punctuation",
            "--strip-numbers",
            "--min-length",
            "2",
            "--max-length",
            "10",
            "--only-alpha",
            "--grep",
            "a",
            "--ignore-stopwords",
        ]
    )
    assert len(_normalizers_from_args(args_full)) == 3
    assert len(_predicates_from_args(args_full)) == 5


def test_analyze_source_unsupported_format_propagates(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("WORDCOUNT_NO_HISTORY", "1")
    p = tmp_path / "weird.xyz"
    p.write_text("hi", encoding="utf-8")
    ns = SimpleNamespace(
        input_format="weird",
        encoding=None,
        chunk_size=1024,
        tokenizer="smart",
        ignore_case=True,
        fold_diacritics=False,
        strip_punctuation=False,
        strip_numbers=False,
        min_length=None,
        max_length=None,
        only_alpha=False,
        grep=None,
        ignore_stopwords=False,
        language="en",
    )
    with pytest.raises(UnsupportedFormatError):
        analyze_source(str(p), ns)
