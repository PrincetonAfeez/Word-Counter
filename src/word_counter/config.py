"""Configuration utilities for the word_counter package."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path
from typing import Any

APP_DIR = Path.home() / ".wordcount"
CONFIG_PATH = APP_DIR / "config.toml"
HISTORY_PATH = APP_DIR / "history.jsonl"


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    import tomllib

    with path.open("rb") as handle:
        data = tomllib.load(handle)
    return dict(data)


def load_stopwords(language: str) -> frozenset[str]:
    filename = f"{language.casefold()}.txt"
    try:
        text = (
            resources.files("word_counter")
            .joinpath("resources", "stopwords", filename)
            .read_text(encoding="utf-8")
        )
    except FileNotFoundError:
        return frozenset()
    return frozenset(
        line.strip().casefold()
        for line in text.splitlines()
        if line.strip() and not line.startswith("#")
    )


def append_history(
    *,
    command: str,
    sources: list[str],
    summary: dict[str, object],
    path: Path = HISTORY_PATH,
) -> None:
    if os.environ.get("WORDCOUNT_NO_HISTORY"):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "command": command,
        "sources": sources,
        "summary": summary,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def history_last(limit: int, path: Path = HISTORY_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines[-limit:] if line.strip()]
