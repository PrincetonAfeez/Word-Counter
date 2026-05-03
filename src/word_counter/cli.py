"""Command-line interface for the word_counter package."""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

from . import __version__
from .config import append_history, history_last, load_config, load_stopwords
from .exceptions import EmptyInputError, WordCountError
from .filters import MaxLength, MinLength, OnlyAlpha, RegexFilter, StopwordFilter, TokenPredicate
from .formatters import (
    create_formatter,
    format_diff,
    format_many,
    format_readability,
    format_word_frequencies,
)
from .handlers import create_handler
from .models import TextStats
from .normalization import (
    CaseFolder,
    DiacriticFolder,
    Normalizer,
    NumberStripper,
    PunctuationStripper,
)
from .stats import analyze_chunks, readability_scores
from .tokenizers import TokenizerRegistry

COMMANDS = {"stats", "top", "freq", "readability", "diff", "compare", "merge", "history"}
OUTPUT_FORMATS = ("plain", "table", "json", "csv", "markdown")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--version" in argv:
        print(f"word-counter {__version__}")
        return 0
    parser = build_parser()
    args = parser.parse_args(_normalize_argv(argv))
    try:
        output = dispatch(args)
    except WordCountError as exc:
        print(f"wordcount: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"wordcount: {exc}", file=sys.stderr)
        return 2
    if output:
        print(output)
    return 0


def build_parser() -> argparse.ArgumentParser:
    config = load_config()
    defaults = {
        "tokenizer": config.get("default_tokenizer", "smart"),
        "output_format": config.get("default_formatter", "plain"),
        "language": config.get("default_language", "en"),
    }
    parser = argparse.ArgumentParser(
        prog="wordcount",
        description="Count words and text statistics.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    stats = subparsers.add_parser("stats", help="show text statistics")
    _add_common_flags(stats, defaults)
    stats.add_argument("sources", nargs="*", default=["-"])

    top = subparsers.add_parser("top", help="show top words")
    _add_common_flags(top, defaults)
    top.add_argument("source")
    top.add_argument("-n", "--limit", type=int, default=20)

    freq = subparsers.add_parser("freq", help="show one word's frequency")
    _add_common_flags(freq, defaults)
    freq.add_argument("source")
    freq.add_argument("--word", required=True)

    readability = subparsers.add_parser("readability", help="show readability scores")
    _add_common_flags(readability, defaults)
    readability.add_argument("source")

    diff = subparsers.add_parser("diff", help="compare two files")
    _add_common_flags(diff, defaults)
    diff.add_argument("left")
    diff.add_argument("right")

    compare = subparsers.add_parser("compare", help="compare many files")
    _add_common_flags(compare, defaults)
    compare.add_argument("sources", nargs="+")

    merge = subparsers.add_parser("merge", help="combine many files")
    _add_common_flags(merge, defaults)
    merge.add_argument("sources", nargs="+")

    history = subparsers.add_parser("history", help="show invocation history")
    history.add_argument("--last", type=int, default=10)
    history.add_argument(
        "--format",
        dest="output_format",
        choices=("plain", "json"),
        default="plain",
    )
    return parser


def dispatch(args: argparse.Namespace) -> str:
    if args.command == "stats":
        return command_stats(args)
    if args.command == "top":
        stats = analyze_source(args.source, args)
        append_history(
            command="top",
            sources=[args.source],
            summary=stats.to_dict(include_frequencies=False),
        )
        return format_word_frequencies(
            stats.top_words(args.limit, min_count=args.min_count),
            output_format=args.output_format,
        )
    if args.command == "freq":
        stats = analyze_source(args.source, args)
        word = _normalize_query(args.word, _normalizers_from_args(args))
        count = stats.word_frequencies.get(word, 0)
        append_history(
            command="freq",
            sources=[args.source],
            summary={"word": word, "count": count},
        )
        if args.output_format == "json":
            return json.dumps({"word": word, "count": count}, indent=2, sort_keys=True)
        return f"{word}: {count}"
    if args.command == "readability":
        stats = analyze_source(args.source, args)
        append_history(
            command="readability",
            sources=[args.source],
            summary=stats.to_dict(include_frequencies=False),
        )
        return format_readability(readability_scores(stats), output_format=args.output_format)
    if args.command == "diff":
        left = analyze_source(args.left, args)
        right = analyze_source(args.right, args)
        append_history(
            command="diff",
            sources=[args.left, args.right],
            summary={"left_words": left.word_count, "right_words": right.word_count},
        )
        return format_diff(
            _source_label(args.left),
            left,
            _source_label(args.right),
            right,
            output_format=args.output_format,
        )
    if args.command == "compare":
        items = {
            _source_label(source): analyze_source(source, args)
            for source in _expand_sources(args.sources)
        }
        append_history(
            command="compare",
            sources=list(items),
            summary={
                "sources": len(items),
                "words": sum(item.word_count for item in items.values()),
            },
        )
        return format_many(items, output_format=args.output_format, no_color=args.no_color)
    if args.command == "merge":
        sources = _expand_sources(args.sources)
        if not sources:
            raise EmptyInputError("merge requires at least one source")
        merged = TextStats()
        for source in sources:
            merged += analyze_source(source, args)
        append_history(
            command="merge",
            sources=sources,
            summary=merged.to_dict(include_frequencies=False),
        )
        return create_formatter(args.output_format, no_color=args.no_color).format_stats(merged)
    if args.command == "history":
        records = history_last(args.last)
        if args.output_format == "json":
            return json.dumps(records, indent=2, sort_keys=True)
        if not records:
            return "No history yet."
        return "\n".join(
            f"{record['timestamp']}  {record['command']}  {', '.join(record['sources'])}"
            for record in records
        )
    raise ValueError(f"Unknown command {args.command}")


def command_stats(args: argparse.Namespace) -> str:
    sources = _expand_sources(args.sources)
    if len(sources) > 1:
        items = {_source_label(source): analyze_source(source, args) for source in sources}
        append_history(
            command="stats",
            sources=sources,
            summary={
                "sources": len(items),
                "words": sum(item.word_count for item in items.values()),
            },
        )
        return format_many(items, output_format=args.output_format, no_color=args.no_color)
    source = sources[0] if sources else "-"
    stats = analyze_source(source, args)
    append_history(
        command="stats",
        sources=[source],
        summary=stats.to_dict(include_frequencies=False),
    )
    return create_formatter(
        args.output_format,
        no_color=args.no_color,
        top_n=args.top,
    ).format_stats(stats)


def analyze_source(source: str, args: argparse.Namespace) -> TextStats:
    handler = create_handler(
        args.input_format,
        source,
        encoding=args.encoding,
        chunk_size=args.chunk_size,
    )
    tokenizer = TokenizerRegistry().create(args.tokenizer)
    return analyze_chunks(
        handler.extract_text(source),
        tokenizer=tokenizer,
        normalizers=_normalizers_from_args(args),
        predicates=_predicates_from_args(args),
        encoding=args.encoding or "utf-8",
    )


def _add_common_flags(parser: argparse.ArgumentParser, defaults: dict[str, str]) -> None:
    parser.add_argument("--tokenizer", default=defaults["tokenizer"])
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=OUTPUT_FORMATS,
        default=defaults["output_format"],
    )
    parser.add_argument(
        "--input-format",
        choices=(
            "txt",
            "text",
            "plain",
            "md",
            "markdown",
            "html",
            "htm",
            "json",
            "docx",
            "pdf",
        ),
    )
    parser.add_argument("--language", default=defaults["language"])
    parser.add_argument("--encoding")
    parser.add_argument("--chunk-size", type=int, default=64 * 1024)
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--ignore-case", dest="ignore_case", action="store_true", default=True)
    parser.add_argument("--case-sensitive", dest="ignore_case", action="store_false")
    parser.add_argument("--fold-diacritics", action="store_true")
    parser.add_argument("--strip-punctuation", action="store_true")
    parser.add_argument("--strip-numbers", action="store_true")
    parser.add_argument("--ignore-stopwords", action="store_true")
    parser.add_argument("--min-length", type=int)
    parser.add_argument("--max-length", type=int)
    parser.add_argument("--min-count", type=int, default=1)
    parser.add_argument("--only-alpha", action="store_true")
    parser.add_argument("--grep")
    parser.add_argument("--top", type=int, default=10, help=argparse.SUPPRESS)


def _normalizers_from_args(args: argparse.Namespace) -> tuple[Normalizer, ...]:
    normalizers: list[Normalizer] = []
    if args.ignore_case:
        normalizers.append(CaseFolder())
    if args.fold_diacritics:
        normalizers.append(DiacriticFolder())
    if args.strip_punctuation:
        normalizers.append(PunctuationStripper())
    if args.strip_numbers:
        normalizers.append(NumberStripper())
    return tuple(normalizers)


def _predicates_from_args(args: argparse.Namespace) -> tuple[TokenPredicate, ...]:
    predicates: list[TokenPredicate] = []
    if args.min_length is not None:
        predicates.append(MinLength(args.min_length))
    if args.max_length is not None:
        predicates.append(MaxLength(args.max_length))
    if args.only_alpha:
        predicates.append(OnlyAlpha())
    if args.grep:
        predicates.append(RegexFilter(args.grep))
    if args.ignore_stopwords:
        predicates.append(StopwordFilter(load_stopwords(args.language)))
    return tuple(predicates)


def _normalize_query(word: str, normalizers: tuple[Normalizer, ...]) -> str:
    for normalizer in normalizers:
        word = normalizer.normalize(word)
    return word


def _expand_sources(sources: list[str]) -> list[str]:
    expanded: list[str] = []
    for source in sources:
        if source == "-":
            expanded.append(source)
            continue
        matches = sorted(glob.glob(source))
        expanded.extend(matches or [source])
    return expanded


def _source_label(source: str) -> str:
    return "stdin" if source == "-" else Path(source).name


def _normalize_argv(argv: list[str]) -> list[str]:
    if not argv:
        return ["stats", "-"]
    if argv[0] in COMMANDS:
        return argv
    return ["stats", *argv]
