"""Configuration utilities tests for the word_counter package."""

from __future__ import annotations

import json

from word_counter import config as config_module
from word_counter.config import (
    append_history,
    history_last,
    load_config,
    load_stopwords,
)


def test_load_config_missing_file_returns_empty_dict(tmp_path) -> None:
    missing = tmp_path / "nope.toml"
    assert load_config(missing) == {}


def test_load_config_reads_toml(tmp_path) -> None:
    path = tmp_path / "cfg.toml"
    path.write_text('default_tokenizer = "regex"\n', encoding="utf-8")
    data = load_config(path)
    assert data["default_tokenizer"] == "regex"


def test_load_stopwords_english_contains_common_word() -> None:
    words = load_stopwords("en")
    assert "the" in words
    assert isinstance(words, frozenset)


def test_load_stopwords_unknown_language_returns_empty() -> None:
    assert load_stopwords("zz") == frozenset()


def test_load_stopwords_is_case_insensitive_key() -> None:
    assert load_stopwords("EN") == load_stopwords("en")


def test_append_history_writes_jsonl(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("WORDCOUNT_NO_HISTORY", raising=False)
    hist = tmp_path / "history.jsonl"
    append_history(
        command="stats",
        sources=["a.txt"],
        summary={"words": 3},
        path=hist,
    )
    line = hist.read_text(encoding="utf-8").strip()
    record = json.loads(line)
    assert record["command"] == "stats"
    assert record["sources"] == ["a.txt"]
    assert record["summary"] == {"words": 3}
    assert "timestamp" in record


def test_append_history_skips_when_env_set(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WORDCOUNT_NO_HISTORY", "1")
    hist = tmp_path / "history.jsonl"
    append_history(command="stats", sources=["a.txt"], summary={}, path=hist)
    assert not hist.exists()


def test_history_last_returns_tail(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("WORDCOUNT_NO_HISTORY", raising=False)
    hist = tmp_path / "history.jsonl"
    for index in range(3):
        append_history(command="stats", sources=[f"{index}.txt"], summary={"n": index}, path=hist)
    rows = history_last(2, path=hist)
    assert len(rows) == 2
    assert rows[-1]["sources"] == ["2.txt"]


def test_history_last_missing_file_returns_empty_list(tmp_path) -> None:
    assert history_last(5, path=tmp_path / "missing.jsonl") == []


def test_config_module_paths_are_paths() -> None:
    assert "wordcount" in str(config_module.CONFIG_PATH)
    assert config_module.HISTORY_PATH.suffix == ".jsonl"
