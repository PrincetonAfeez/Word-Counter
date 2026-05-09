"""Color utilities for the word_counter package."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Ansi:
    enabled: bool = True

    @classmethod
    def auto(cls, *, force_disabled: bool = False) -> Ansi:
        enabled = (
            not force_disabled
            and "NO_COLOR" not in os.environ
            and hasattr(sys.stdout, "isatty")
            and sys.stdout.isatty()
        )
        return cls(enabled=enabled)

    def color(self, text: str, code: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}\033[0m"

    def bold(self, text: str) -> str:
        return self.color(text, "1")

    def green(self, text: str) -> str:
        return self.color(text, "32")

    def yellow(self, text: str) -> str:
        return self.color(text, "33")

    def red(self, text: str) -> str:
        return self.color(text, "31")
