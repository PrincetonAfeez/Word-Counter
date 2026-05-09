"""Formatting utilities for the word_counter package."""

from __future__ import annotations

import csv
import io
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import Protocol

from .colors import Ansi
from .models import ReadabilityScore, TextStats, WordFrequency


class OutputFormatter(Protocol):
    def format_stats(self, stats: TextStats) -> str:
        """Format a single stats object."""


class PlainFormatter:
    def __init__(self, *, no_color: bool = False, top_n: int = 10) -> None:
        self.color = Ansi.auto(force_disabled=no_color)
        self.top_n = top_n

    def format_stats(self, stats: TextStats) -> str:
        lines = [self.color.bold("Text statistics"), format(stats, "table")]
        top = stats.top_words(self.top_n)
        if top:
            lines.extend(["", self.color.bold("Top words"), ascii_bar_chart(top)])
        return "\n".join(lines)


class TableFormatter:
    def format_stats(self, stats: TextStats) -> str:
        return format(stats, "table")


class JsonFormatter:
    def format_stats(self, stats: TextStats) -> str:
        return json.dumps(stats.to_dict(), indent=2, sort_keys=True)


class CsvFormatter:
    def format_stats(self, stats: TextStats) -> str:
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["metric", "value"])
        writer.writerows(stats.summary_rows())
        return output.getvalue().rstrip()


class MarkdownFormatter:
    def format_stats(self, stats: TextStats) -> str:
        rows = ["| Metric | Value |", "| --- | ---: |"]
        rows.extend(f"| {label} | {value} |" for label, value in stats.summary_rows())
        return "\n".join(rows)


def create_formatter(name: str, *, no_color: bool = False, top_n: int = 10) -> OutputFormatter:
    normalized = name.casefold()
    if normalized == "plain":
        return PlainFormatter(no_color=no_color, top_n=top_n)
    if normalized == "table":
        return TableFormatter()
    if normalized == "json":
        return JsonFormatter()
    if normalized == "csv":
        return CsvFormatter()
    if normalized in {"md", "markdown"}:
        return MarkdownFormatter()
    msg = f"Unknown output format '{name}'"
    raise ValueError(msg)


def format_many(
    items: Mapping[str, TextStats],
    *,
    output_format: str,
    no_color: bool = False,
) -> str:
    if output_format == "json":
        return json.dumps(
            {name: stats.to_dict(include_frequencies=False) for name, stats in items.items()},
            indent=2,
            sort_keys=True,
        )
    if output_format == "csv":
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["source", "characters", "words", "lines", "sentences", "paragraphs"])
        for name, stats in items.items():
            writer.writerow(
                [
                    name,
                    stats.character_count,
                    stats.word_count,
                    stats.line_count,
                    stats.sentence_count,
                    stats.paragraph_count,
                ]
            )
        return output.getvalue().rstrip()
    headers = ["Source", "Chars", "Words", "Lines", "Sentences", "Paragraphs", "Unique"]
    rows = [
        [
            name,
            str(stats.character_count),
            str(stats.word_count),
            str(stats.line_count),
            str(stats.sentence_count),
            str(stats.paragraph_count),
            str(stats.unique_word_count),
        ]
        for name, stats in items.items()
    ]
    if output_format in {"markdown", "md"}:
        table = ["| " + " | ".join(headers) + " |"]
        table.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
        table.extend("| " + " | ".join(row) + " |" for row in rows)
        return "\n".join(table)
    color = Ansi.auto(force_disabled=no_color)
    return "\n".join([color.bold("Comparison"), _aligned_table(headers, rows)])


def format_word_frequencies(
    frequencies: Sequence[WordFrequency],
    *,
    output_format: str,
) -> str:
    if output_format == "json":
        return json.dumps([asdict(item) for item in frequencies], indent=2, sort_keys=True)
    if output_format == "csv":
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["rank", "word", "count", "percentage"])
        for item in frequencies:
            writer.writerow([item.rank, item.word, item.count, f"{item.percentage:.4f}"])
        return output.getvalue().rstrip()
    if output_format in {"markdown", "md"}:
        rows = ["| Rank | Word | Count | Percentage |", "| ---: | --- | ---: | ---: |"]
        rows.extend(
            f"| {item.rank} | {item.word} | {item.count} | {item.percentage:.2f}% |"
            for item in frequencies
        )
        return "\n".join(rows)
    return ascii_bar_chart(frequencies)


def format_readability(
    scores: Sequence[ReadabilityScore],
    *,
    output_format: str,
) -> str:
    if output_format == "json":
        return json.dumps([asdict(score) for score in scores], indent=2, sort_keys=True)
    if output_format == "csv":
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["algorithm", "score", "grade_level"])
        for score in scores:
            writer.writerow([score.algorithm_name, f"{score.score:.2f}", score.grade_level])
        return output.getvalue().rstrip()
    if output_format in {"markdown", "md"}:
        rows = ["| Algorithm | Score | Grade |", "| --- | ---: | --- |"]
        rows.extend(
            f"| {score.algorithm_name} | {score.score:.2f} | {score.grade_level} |"
            for score in scores
        )
        return "\n".join(rows)
    table_rows = [
        [score.algorithm_name, f"{score.score:.2f}", score.grade_level]
        for score in scores
    ]
    return _aligned_table(["Algorithm", "Score", "Grade"], table_rows)


def ascii_bar_chart(frequencies: Sequence[WordFrequency], *, width: int = 32) -> str:
    if not frequencies:
        return ""
    max_count = max(item.count for item in frequencies)
    word_width = max(len(item.word) for item in frequencies)
    rows = []
    for item in frequencies:
        bar_width = max(1, round(item.count / max_count * width)) if max_count else 0
        bar = _bar_character() * bar_width
        rows.append(
            f"{item.rank:>2}. {item.word:<{word_width}} {bar:<{width}} "
            f"{item.count:>5} ({item.percentage:>5.2f}%)"
        )
    return "\n".join(rows)


def format_diff(
    left_name: str,
    left: TextStats,
    right_name: str,
    right: TextStats,
    *,
    output_format: str,
) -> str:
    metrics = [
        ("characters", left.character_count, right.character_count),
        ("words", left.word_count, right.word_count),
        ("unique_words", left.unique_word_count, right.unique_word_count),
        ("lines", left.line_count, right.line_count),
        ("sentences", left.sentence_count, right.sentence_count),
        ("paragraphs", left.paragraph_count, right.paragraph_count),
        ("type_token_ratio", left.type_token_ratio, right.type_token_ratio),
    ]
    if output_format == "json":
        return json.dumps(
            {
                metric: {
                    left_name: left_value,
                    right_name: right_value,
                    "delta": right_value - left_value,
                }
                for metric, left_value, right_value in metrics
            },
            indent=2,
            sort_keys=True,
        )
    rows = [
        [
            metric,
            _fmt_value(left_value),
            _fmt_value(right_value),
            _fmt_value(right_value - left_value),
        ]
        for metric, left_value, right_value in metrics
    ]
    if output_format in {"markdown", "md"}:
        table = [
            f"| Metric | {left_name} | {right_name} | Delta |",
            "| --- | ---: | ---: | ---: |",
        ]
        table.extend(f"| {' | '.join(row)} |" for row in rows)
        return "\n".join(table)
    return _aligned_table(["Metric", left_name, right_name, "Delta"], rows)


def _aligned_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    widths = [
        max(len(str(row[index])) for row in [headers, *rows])
        for index in range(len(headers))
    ]
    formatted = ["  ".join(str(value).ljust(widths[index]) for index, value in enumerate(headers))]
    formatted.append("  ".join("-" * width for width in widths))
    formatted.extend(
        "  ".join(str(value).ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    )
    return "\n".join(formatted)


def _fmt_value(value: float | int) -> str:
    return f"{value:.4f}" if isinstance(value, float) else str(value)


def _bar_character() -> str:
    block = "\u2588"
    encoding = sys.stdout.encoding or "utf-8"
    try:
        block.encode(encoding)
    except UnicodeEncodeError:
        return "#"
    return block
