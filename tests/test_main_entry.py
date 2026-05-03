"""Main entry point tests for the word_counter package."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_run_module_as_main_prints_version() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "word_counter", "--version"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env={**dict(__import__("os").environ), "PYTHONPATH": str(root / "src")},
    )
    assert result.returncode == 0
    assert "word-counter" in result.stdout
