"""Handler utilities tests for the word_counter package."""

from __future__ import annotations

from pathlib import Path

from word_counter.handlers import HtmlHandler, JsonHandler, MarkdownHandler


def test_markdown_handler_strips_links_and_heading(tmp_path: Path) -> None:
    path = tmp_path / "sample.md"
    path.write_text("# Title\nRead [docs](https://example.com).", encoding="utf-8")
    assert "Title" in "".join(MarkdownHandler().extract_text(path))
    assert "docs" in "".join(MarkdownHandler().extract_text(path))
    assert "https://example.com" not in "".join(MarkdownHandler().extract_text(path))


def test_html_handler_ignores_script_and_style(tmp_path: Path) -> None:
    path = tmp_path / "sample.html"
    path.write_text(
        "<html><style>hidden</style><body>Hello <b>world</b><script>nope</script></body></html>",
        encoding="utf-8",
    )
    text = "".join(HtmlHandler().extract_text(path))
    assert "Hello" in text
    assert "world" in text
    assert "hidden" not in text
    assert "nope" not in text


def test_json_handler_extracts_nested_strings(tmp_path: Path) -> None:
    path = tmp_path / "sample.json"
    path.write_text(
        '{"title": "Hello", "items": [{"body": "world"}], "count": 2}',
        encoding="utf-8",
    )
    assert "".join(JsonHandler().extract_text(path)) == "Hello world"
