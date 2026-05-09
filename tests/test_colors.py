"""Color utilities tests for the word_counter package."""

from __future__ import annotations

from word_counter.colors import Ansi


def test_ansi_auto_respects_force_disabled() -> None:
    ansi = Ansi.auto(force_disabled=True)
    assert ansi.enabled is False


def test_ansi_auto_respects_no_color_env(monkeypatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    ansi = Ansi.auto(force_disabled=False)
    assert ansi.enabled is False


def test_ansi_color_returns_plain_when_disabled() -> None:
    ansi = Ansi(enabled=False)
    assert ansi.color("x", "32") == "x"


def test_ansi_color_wraps_when_enabled() -> None:
    ansi = Ansi(enabled=True)
    assert ansi.color("x", "32") == "\033[32mx\033[0m"


def test_ansi_bold_green_yellow_red_delegate_to_color() -> None:
    ansi = Ansi(enabled=True)
    assert "\033[1m" in ansi.bold("b")
    assert "\033[32m" in ansi.green("g")
    assert "\033[33m" in ansi.yellow("y")
    assert "\033[31m" in ansi.red("r")


def test_ansi_auto_without_no_color_uses_isatty(monkeypatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)

    class FakeStdout:
        def isatty(self) -> bool:
            return True

    monkeypatch.setattr("word_counter.colors.sys.stdout", FakeStdout())
    assert Ansi.auto(force_disabled=False).enabled is True
