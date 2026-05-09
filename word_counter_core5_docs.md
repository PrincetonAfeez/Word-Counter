# Architecture Decision Record

## App 39 — Word Counter
**Text Analysis Group | Document 1 of 5**

## Title
Adopt a streaming-first, strategy-based architecture for a multi-format word counter.

## Status
Accepted

## Date
2026-05-09

## Context
Word Counter is a Python command-line application for counting words and producing text statistics from plain text, Markdown, HTML, JSON, DOCX, and PDF sources. Its main risk is that “word counting” can easily become either too trivial, by counting `split()` results only, or too broad, by trying to become a full document-processing/NLP platform. The project resolves that tension by making plain text streaming the primary path, while treating structured formats as adapters that yield text chunks into the same statistics engine.

The application needs to support terminal users, scripting workflows, and academic evaluation. It must be small enough to remain understandable, but robust enough to demonstrate real engineering ideas: chunked reading, tokenizer strategies, normalization pipelines, filters, output formatters, config, history, and optional third-party format support.

The central architectural question was: should the project be built as one CLI script, one format-specific tool per input type, or a reusable package with isolated strategies and handlers?

## Decision Drivers

- Preserve a simple `wordcount` CLI while keeping the counting engine reusable.
- Avoid loading large plain-text files entirely into memory.
- Keep the default runtime dependency-free.
- Support optional DOCX/PDF functionality without forcing those dependencies on every user.
- Make tokenization, normalization, filtering, and formatting independently testable.
- Make results mergeable for multi-file comparison and aggregation.
- Keep error behavior predictable for unsupported formats, decoding failures, bad tokenizers, and invalid commands.
- Align with the Constitution’s standards for scope discipline, verification, reflection, and architectural growth.

## Options Considered

### Option 1 — Single procedural script
A single `main.py` could parse arguments, read files, count words, and print results.

This would be fast to write but weak as a portfolio project. It would mix file I/O, tokenization, formatting, and CLI branching. It would also make DOCX/PDF support and later comparison modes harder to add cleanly.

### Option 2 — Format-specific tools
Separate commands or modules could handle text, Markdown, HTML, JSON, DOCX, and PDF independently.

This would isolate format quirks, but it risks duplicated tokenization/counting logic. The main design goal is that all formats produce text and then share the same analysis pipeline, so format-specific engines would work against that goal.

### Option 3 — Streaming engine with input handlers and strategy objects
This approach defines a shared analysis engine that accepts chunks of text. Input handlers adapt sources into chunks, tokenizers convert text into tokens, normalizers transform text before tokenization, predicates decide which tokens count, and formatters render results.

This is more work than a one-file script, but it keeps the project cohesive and extensible. It also makes the important behaviors directly testable.

### Option 4 — Full NLP/document-processing library
The project could use advanced libraries for parsing, language detection, stemming, lemmatization, PDF extraction, DOCX metadata, and readability analysis.

This is beyond the scope of a learning CLI. It would introduce dependency management, correctness expectations, and language-specific complexity that are not necessary for this app’s goals.

## Decision

Build Word Counter as a small Python package with a streaming-first analysis engine and strategy/adaptor modules:

- `readers.py` owns plain file, stdin, and string chunk reading.
- `handlers.py` adapts plain text, Markdown, HTML, JSON, DOCX, and PDF into text chunks.
- `tokenizers.py` provides whitespace, regex, smart, and n-gram tokenizers.
- `normalization.py` provides composable normalization steps.
- `filters.py` provides token predicates.
- `stats.py` computes `TextStats` from text chunks.
- `models.py` defines immutable result and token models.
- `formatters.py` renders plain, table, JSON, CSV, and Markdown output.
- `config.py` handles TOML defaults, stopwords, and history.
- `cli.py` composes the application and exposes the user-facing commands.

## Rationale

The streaming-first design directly addresses the largest practical concern: plain text may be large. A `StreamingReader` reads fixed-size chunks, and `analyze_chunks` keeps a token tail so words split across chunk boundaries are not lost or double-counted. That is a meaningful upgrade over `text.split()` and is appropriate for a late-portfolio CLI project.

The handler abstraction keeps format parsing separate from statistics. Plain text and HTML can stream naturally; Markdown and JSON are adapted through simpler full-file parsing because their cleanup/extraction rules are easier to apply to complete text. DOCX and PDF support are intentionally optional. If `python-docx` or `pypdf` is missing, the tool fails with install guidance instead of pretending support exists.

Tokenizers are strategies because there is no single universal definition of “word.” A whitespace tokenizer is useful for baseline comparisons, a regex tokenizer handles Unicode word matching, the smart tokenizer preserves contractions, URLs, and email addresses, and the n-gram tokenizer supports phrase counting without changing the statistics engine.

Normalization and filtering are separate because they answer different questions. Normalization changes text shape: case-folding, diacritic folding, punctuation stripping, and number stripping. Filtering decides whether a token should count: minimum length, maximum length, alpha-only, regex inclusion, and stopwords. This separation makes the pipeline easier to reason about.

Output formatting is separated because the same result needs to serve several audiences: humans reading a terminal summary, scripts consuming JSON, spreadsheet users reading CSV, and documentation/report users pasting Markdown.

## Trade-offs Accepted

- Markdown and JSON handlers load full files rather than streaming full parser state.
- DOCX and PDF support depend on optional third-party packages.
- The readability formulas use a heuristic syllable estimator, not a full linguistic model.
- N-gram tokenization works within the selected tokenizer’s emitted token stream and is not a full corpus analytics system.
- Config is intentionally simple and read-only; the CLI does not provide a rich config-management interface.
- History is append-only JSONL and can grow until the user cleans it manually.
- HTML parsing is stdlib-based and skips script/style, but it is not a browser-grade renderer.
- PDF text extraction quality depends on the optional `pypdf` library and source PDF structure.

## Consequences

The project becomes larger than a basic word counter, but the size is justified by clean boundaries and multiple real workflows. The engine can be tested independently from the CLI. Format handlers can be tested with small sample files. Tokenization and normalization choices can be tested directly. CLI tests can verify integration behavior without needing to assert every low-level count manually.

The package also becomes easier to extend. Adding another input format means implementing a handler that yields text chunks. Adding an output format means implementing a formatter. Adding a filtering rule means implementing a predicate.

The main maintenance burden is keeping CLI help, README examples, config defaults, and behavior synchronized. Another risk is that users may assume DOCX/PDF support is available by default even though it is an optional extra.

## Superseded By

Not superseded.

## Constitution Alignment

This decision supports Article 1 by showing architectural thinking appropriate to a CLI that has grown past a one-file script. It supports Article 3 by keeping the scope as a medium utility rather than a full NLP platform. It supports Article 4 through separation of concerns and testable modules. It supports Article 6 through tests covering chunk boundaries, handlers, tokenizers, formatters, config, and CLI behavior.

-e

---

# Technical Design Document

## App 39 — Word Counter
**Text Analysis Group | Document 2 of 5**

## Purpose & Scope

Word Counter counts words and produces text statistics from multiple source formats. It is intended for command-line use, scripting, and lightweight writing-analysis workflows.

The app provides:

- Statistics for characters, bytes, words, unique words, lines, sentences, paragraphs, and distributions.
- Top-word and single-word frequency commands.
- Readability scoring.
- Multi-file comparison.
- Diff-style metric comparison between two sources.
- Merge of multiple sources into one combined `TextStats` result.
- Plain, table, JSON, CSV, and Markdown output formats.
- Plain text, Markdown, HTML, JSON, DOCX, and PDF input handlers.
- Config defaults from `~/.wordcount/config.toml`.
- Stopword loading from packaged resources.
- Append-only command history in `~/.wordcount/history.jsonl`, unless disabled by environment variable.

The app does not try to be a full NLP system. It does not do language-aware stemming, lemmatization, document layout reconstruction, PDF OCR, or advanced grammar analysis.

## System Context

The user runs `wordcount` or `python -m word_counter` from a terminal. The CLI parses arguments, determines the command, chooses a format handler, tokenizer, normalizers, predicates, and formatter, then prints the result to stdout. Errors are printed to stderr and return exit code `2`.

The package can also be imported programmatically. Public API exports include `TextStats`, `Token`, `TokenType`, `WordFrequency`, `ReadabilityScore`, `analyze_chunks`, `analyze_text`, and `readability_scores`.

The only always-required runtime dependency is the Python standard library. Optional extras enable DOCX and PDF parsing.

## Component Breakdown

### `word_counter.__init__`
Exports the public package API and version. It exposes model classes and core analysis functions so users do not need to import deep internal modules for common programmatic use.

### `word_counter.__main__`
Thin module execution shim. It imports `main` from `cli.py` and exits with the returned status code.

### `models.py`
Defines the core immutable data structures:

- `TokenType`: enum for word, number, punctuation, whitespace, emoji, URL, and email tokens.
- `Token`: token value, type, and source offsets.
- `WordFrequency`: word/count/rank/percentage row.
- `ReadabilityScore`: score, grade label, and algorithm name.
- `TextStats`: aggregate immutable statistics and derived metric properties.

`TextStats` also implements `__add__` so independent sources can be combined. When both stats came from `analyze_text`, it can rebuild exact concatenation stats from raw text. Otherwise it combines counters and scalar counts.

### `readers.py`
Defines low-level chunk readers:

- `StreamingReader` protocol.
- `FileReader`: reads file chunks with detected or specified encoding.
- `StdinReader`: reads stdin chunks.
- `StringReader`: yields chunks from an in-memory string.
- `detect_encoding`: uses optional `chardet` when present, otherwise falls back to `utf-8-sig`.

### `handlers.py`
Adapts source formats into text chunks:

- `PlainTextHandler`: uses `FileReader` or `StdinReader`.
- `MarkdownHandler`: removes common Markdown syntax and yields cleaned text.
- `HtmlHandler`: uses stdlib `HTMLParser` and ignores `script`/`style` content.
- `JsonHandler`: recursively extracts string values from JSON data.
- `DocxHandler`: uses optional `python-docx` to extract paragraphs.
- `PdfHandler`: uses optional `pypdf` to extract page text.
- `create_handler`: resolves explicit or detected format names.
- `detect_format`: derives format from extension or defaults stdin to text.

### `tokenizers.py`
Defines tokenization strategies:

- `Tokenizer` protocol.
- `WhitespaceTokenizer`: emits whitespace/non-whitespace runs.
- `RegexTokenizer`: emits Unicode word, punctuation, and whitespace groups.
- `SmartTokenizer`: preserves URLs, emails, contractions, hyphenated words, numbers, emoji, whitespace, and punctuation.
- `NgramTokenizer`: wraps another tokenizer and emits n-word windows.
- `TokenizerRegistry`: resolves names such as `smart`, `regex`, `whitespace`, and `ngram:2:smart`.
- `classify_token`: assigns token type to a raw value.
- `WORDISH_TYPES`: token types counted by the statistics engine.

### `normalization.py`
Provides composable text-level normalizers:

- `CaseFolder`.
- `DiacriticFolder`.
- `PunctuationStripper`.
- `NumberStripper`.
- `NormalizationPipeline`.

Normalization happens before tokenization. This means punctuation stripping, for example, changes the text stream before the tokenizer sees it.

### `filters.py`
Provides token-level predicates:

- `MinLength`.
- `MaxLength`.
- `OnlyAlpha`.
- `RegexFilter`.
- `StopwordFilter`.
- `compose_predicates`.

Filtering happens after tokenization. A token must pass all configured predicates to be counted.

### `stats.py`
Owns the statistics engine:

- `analyze_text`: convenience wrapper for in-memory text.
- `analyze_chunks`: streaming analysis engine.
- `readability_scores`: returns Flesch Reading Ease, Flesch-Kincaid Grade, and Coleman-Liau Index results.
- Helpers for token-tail buffering, paragraph counting, sentence segmentation, character distribution, syllable estimation, and line-break counting.

### `formatters.py`
Renders results:

- `PlainFormatter`.
- `TableFormatter`.
- `JsonFormatter`.
- `CsvFormatter`.
- `MarkdownFormatter`.
- `format_many` for compare/multi-source stats.
- `format_word_frequencies` for top words.
- `format_readability` for readability scores.
- `format_diff` for two-source comparisons.
- `ascii_bar_chart` for human-readable top-word bars.

### `colors.py`
Small ANSI helper that only enables color when stdout is a TTY and `NO_COLOR` is not set. Also supports forced disablement through CLI `--no-color`.

### `config.py`
Handles user configuration, stopwords, and history:

- App directory: `~/.wordcount`.
- Config file: `~/.wordcount/config.toml`.
- History file: `~/.wordcount/history.jsonl`.
- `load_config` returns a dictionary of config defaults.
- `load_stopwords` reads packaged stopword resources by language.
- `append_history` writes JSONL records unless `WORDCOUNT_NO_HISTORY` is set.
- `history_last` reads recent records.

### `cli.py`
Argparse-based application composition:

- Normalizes bare source invocations to `stats`.
- Supports `--version`.
- Defines all commands and common flags.
- Builds tokenizers, normalizers, predicates, handlers, and formatters.
- Appends history for analysis commands.
- Returns `0` on success and `2` for handled application errors.

### `exceptions.py`
Custom exception hierarchy:

- `WordCountError` base.
- `UnsupportedFormatError`.
- `EncodingError`.
- `EmptyInputError`.
- `TokenizerError`.

## Module Dependency Graph

```text
__main__.py
  -> cli.py

cli.py
  -> config.py
  -> exceptions.py
  -> filters.py
  -> formatters.py
  -> handlers.py
  -> models.py
  -> normalization.py
  -> stats.py
  -> tokenizers.py

stats.py
  -> filters.py
  -> models.py
  -> normalization.py
  -> readers.py
  -> tokenizers.py

handlers.py
  -> exceptions.py
  -> readers.py
  -> json, re, html.parser, pathlib
  -> optional docx
  -> optional pypdf

formatters.py
  -> colors.py
  -> models.py
  -> csv, json, sys

config.py
  -> importlib.resources
  -> json, os, pathlib, datetime

readers.py
  -> exceptions.py
  -> pathlib, sys
  -> optional chardet

tokenizers.py
  -> exceptions.py
  -> models.py
  -> re

filters.py
  -> models.py
  -> re
```

Dependency direction is mostly inward: CLI composes, handlers adapt I/O, stats computes, models hold results, and formatters render.

## Core Algorithms & Logic

### CLI dispatch

1. `main()` receives arguments or reads `sys.argv`.
2. If `--version` is present, it prints version and exits `0`.
3. `_normalize_argv()` inserts `stats` when the user passes a source directly.
4. `build_parser()` creates command parsers with defaults from `load_config()`.
5. `dispatch()` calls the command handler.
6. Command handler calls `analyze_source()` for one or more sources.
7. Result is rendered by a formatter or specialized output function.
8. History is appended unless disabled.
9. Output is printed to stdout.

### Source analysis pipeline

1. `analyze_source()` creates a handler with `create_handler(input_format, source, encoding, chunk_size)`.
2. Handler yields text chunks from a file, stdin, or structured extraction process.
3. `TokenizerRegistry().create(args.tokenizer)` selects tokenizer.
4. `_normalizers_from_args()` constructs ordered normalizers.
5. `_predicates_from_args()` constructs token predicates.
6. `analyze_chunks()` consumes chunks and returns `TextStats`.

### Chunk-safe token counting

`analyze_chunks()` maintains `token_tail` between chunks. If a chunk does not end in whitespace, the final non-whitespace run is held back. The next chunk is prefixed with that tail. This avoids counting `inter` and `national` as separate words when `international` crosses a chunk boundary.

For each processable segment:

1. Normalize text using `NormalizationPipeline`.
2. Tokenize normalized text.
3. Keep only token types in `WORDISH_TYPES`.
4. Apply composed predicates.
5. Update `word_frequencies` and `word_length_frequencies`.

### Sentence segmentation

`_SentenceSegmenter` buffers chunks and finds boundaries using punctuation patterns for `.`, `!`, and `?`. Each completed sentence is tokenized and counted, and the sentence word count is recorded in `sentence_word_count_frequencies`. On finish, remaining word-like text becomes a sentence.

### Paragraph counting

`_ParagraphCounter` processes lines across chunks. A nonblank line starts a paragraph if the previous processed line was blank or no paragraph is active. Blank lines reset the paragraph state.

### Readability scoring

`readability_scores()` computes three scores from `TextStats`:

- Flesch Reading Ease.
- Flesch-Kincaid Grade.
- Coleman-Liau Index.

It estimates syllables with a simple vowel-group heuristic. Empty input returns three zero-valued “No words” scores.

### Format handling

- Plain text streams directly from file/stdin chunks.
- Markdown is read fully and cleaned with regular expressions.
- HTML streams through `HTMLParser` and emits collected text while skipping script/style bodies.
- JSON is read fully and recursively extracts only strings.
- DOCX reads paragraph text using optional `docx` library.
- PDF yields page text using optional `pypdf` library.

### Merge logic

The `merge` command starts from an empty `TextStats()` and repeatedly adds each analyzed source. Counter fields are combined and scalar counts are added. For direct `analyze_text` use, raw text can be retained so exact concatenation behavior can be rebuilt in small in-memory use cases.

## Data Structures

### `Token`

```python
Token(value: str, type: TokenType, start: int = 0, end: int = 0)
```

Purpose: carry token content, classification, and offsets.

### `TextStats`

Key fields:

```python
character_count: int
character_count_no_whitespace: int
word_count: int
line_count: int
sentence_count: int
paragraph_count: int
byte_count: int
word_frequencies: Counter[str]
word_length_frequencies: Counter[int]
sentence_word_count_frequencies: Counter[int]
letter_frequencies: Counter[str]
punctuation_frequencies: Counter[str]
```

Purpose: immutable aggregate result with derived metrics.

### `WordFrequency`

```python
WordFrequency(word: str, count: int, rank: int, percentage: float)
```

Purpose: stable row shape for top/bottom words and multiple output formats.

### `ReadabilityScore`

```python
ReadabilityScore(score: float, grade_level: str, algorithm_name: str)
```

Purpose: readable representation of each readability algorithm’s result.

### Config dictionary

`load_config()` returns a dictionary. Recognized keys include:

```toml
default_tokenizer = "smart"
default_formatter = "plain"
default_language = "en"
```

The CLI falls back to built-in defaults if keys are absent.

### History records

Each JSONL record contains:

```json
{
  "timestamp": "...",
  "command": "stats",
  "sources": ["essay.txt"],
  "summary": {"words": 123}
}
```

## State Management

The application is mostly stateless during a single command. Analysis state lives in local variables inside `analyze_chunks()`. Long-term state is limited to:

- User config at `~/.wordcount/config.toml`.
- History at `~/.wordcount/history.jsonl`.
- Packaged stopwords under package resources.
- Environment variable `WORDCOUNT_NO_HISTORY`.
- Environment variable `NO_COLOR` affecting ANSI output.

`TextStats` is frozen, so returned results are treated as values rather than mutable session objects.

## Error Handling Strategy

Errors are handled at module boundaries:

- `EncodingError` wraps decode failures.
- `UnsupportedFormatError` handles unknown formats, bad JSON, or missing optional DOCX/PDF dependencies.
- `TokenizerError` handles invalid tokenizer names and invalid n-gram setup.
- CLI catches `WordCountError` and `ValueError`, prints `wordcount: <message>` to stderr, and exits `2`.

Some standard filesystem errors may still propagate if files are missing or inaccessible; this is a known area for hardening.

## External Dependencies

Runtime core: Python 3.11+ standard library.

Optional extras:

- `python-docx>=1.1` for DOCX support.
- `pypdf>=4` for PDF support.

Optional/dev tooling:

- `hypothesis`.
- `mypy`.
- `pytest`.
- `ruff`.

Optional encoding detection:

- `chardet`, if installed, is used by `detect_encoding`; otherwise `utf-8-sig` is used.

## Concurrency Model

No concurrency is used. The CLI runs synchronously in one process and one thread. Streaming reduces memory pressure without introducing asynchronous or parallel execution.

## Known Limitations

- Markdown cleanup is regex-based and not a full Markdown parser.
- JSON input is read into memory before string extraction.
- DOCX input extracts paragraphs but not all document structures.
- PDF extraction is dependent on source PDF text availability and `pypdf` behavior.
- Readability scoring uses a heuristic syllable estimator.
- History is append-only and has no built-in rotation.
- Config is simple and does not validate every possible key.
- `merge` scalar sentence/paragraph counts are approximate when streaming sources are combined because cross-file boundaries are not semantically identical to one continuous document.

## Design Patterns Used

- Strategy pattern: tokenizers and output formatters.
- Adapter pattern: format handlers adapt multiple file formats into text chunks.
- Pipeline pattern: handler → normalizer → tokenizer → predicate → stats → formatter.
- Value object: `TextStats`, `Token`, `WordFrequency`, `ReadabilityScore`.
- Registry/factory: `TokenizerRegistry`, `create_handler`, `create_formatter`.
- Command dispatcher: CLI command functions mapped through argparse subcommands.
- Append-only log: history JSONL.

## Verification Notes

The repository includes tests for core statistics, chunk boundaries, handlers, tokenizers, formatters, config/history, and CLI commands. Tests explicitly check that chunk boundaries do not split words, Markdown links are stripped correctly, HTML script/style content is ignored, JSON strings are extracted recursively, tokenizer behaviors differ intentionally, and CLI default command behavior works.

-e

---

# Interface Design Specification

## App 39 — Word Counter
**Text Analysis Group | Document 3 of 5**

## Invocation Syntax

Installed command:

```bash
wordcount [GLOBAL_OR_COMMAND_ARGS]
```

Module command:

```bash
python -m word_counter [GLOBAL_OR_COMMAND_ARGS]
```

Bare source shortcut:

```bash
wordcount essay.txt
```

Equivalent to:

```bash
wordcount stats essay.txt
```

Stdin:

```bash
wordcount stats -
```

## Commands

```text
stats        show text statistics
top          show top words
freq         show one word's frequency
readability  show readability scores
diff         compare two files
compare      compare many files
merge        combine many files
history      show invocation history
```

## Argument Reference Table

### Global behavior

| Argument | Type | Required | Default | Valid values | Description |
| --- | --- | --- | --- | --- | --- |
| `--version` | flag | no | false | present/absent | Prints version and exits. |

`--version` is handled before argparse command dispatch.

### Common analysis flags

These flags apply to `stats`, `top`, `freq`, `readability`, `diff`, `compare`, and `merge`.

| Argument | Type | Required | Default | Valid values | Description |
| --- | --- | --- | --- | --- | --- |
| `--tokenizer` | string | no | config `default_tokenizer` or `smart` | `smart`, `regex`, `whitespace`, `ngram[:N][:base]` | Selects tokenizer strategy. |
| `--format` | string | no | config `default_formatter` or `plain` | `plain`, `table`, `json`, `csv`, `markdown` | Selects output format. |
| `--input-format` | string | no | extension detection | `txt`, `text`, `plain`, `md`, `markdown`, `html`, `htm`, `json`, `docx`, `pdf` | Overrides source format detection. |
| `--language` | string | no | config `default_language` or `en` | packaged stopword language such as `en`, `es`, `fr` | Stopword language. Unknown language yields empty stopword set. |
| `--encoding` | string | no | detected/`utf-8-sig` fallback | Python text encoding name | Encoding for text-based inputs. |
| `--chunk-size` | int | no | `65536` | positive integer recommended | Chunk size for streaming reads. |
| `--no-color` | flag | no | false | present/absent | Disables ANSI coloring. |
| `--ignore-case` | flag | no | true | present/absent | Enables case folding. |
| `--case-sensitive` | flag | no | false | present/absent | Disables default case folding. |
| `--fold-diacritics` | flag | no | false | present/absent | Converts accented characters to base forms where possible. |
| `--strip-punctuation` | flag | no | false | present/absent | Replaces punctuation with spaces while preserving sentence punctuation by default. |
| `--strip-numbers` | flag | no | false | present/absent | Replaces digit sequences with spaces before tokenization. |
| `--ignore-stopwords` | flag | no | false | present/absent | Adds stopword filter for selected language. |
| `--min-length` | int | no | none | integer | Counts only tokens at least this long. |
| `--max-length` | int | no | none | integer | Counts only tokens at most this long. |
| `--min-count` | int | no | `1` | integer | Minimum frequency for top-word output. |
| `--only-alpha` | flag | no | false | present/absent | Counts only alphabetic word tokens, allowing apostrophes/hyphens. |
| `--grep` | regex string | no | none | valid Python regex | Counts only tokens matching the regex. |

### `stats`

```bash
wordcount stats [sources ...] [common flags]
```

| Argument | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `sources` | list of paths/globs/`-` | no | `-` | Sources to analyze. Multiple sources produce comparison-style output. |

### `top`

```bash
wordcount top SOURCE -n N [common flags]
```

| Argument | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `source` | path or `-` | yes | none | Source to analyze. |
| `-n`, `--limit` | int | no | `20` | Number of top words to show. |

### `freq`

```bash
wordcount freq SOURCE --word WORD [common flags]
```

| Argument | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `source` | path or `-` | yes | none | Source to analyze. |
| `--word` | string | yes | none | Query word. It is normalized with the same normalizers as the analyzed text. |

### `readability`

```bash
wordcount readability SOURCE [common flags]
```

| Argument | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `source` | path or `-` | yes | none | Source to analyze. |

### `diff`

```bash
wordcount diff LEFT RIGHT [common flags]
```

| Argument | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `left` | path | yes | none | Baseline source. |
| `right` | path | yes | none | Comparison source. |

### `compare`

```bash
wordcount compare SOURCES... [common flags]
```

| Argument | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `sources` | one or more paths/globs | yes | none | Sources to analyze separately. |

### `merge`

```bash
wordcount merge SOURCES... [common flags]
```

| Argument | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `sources` | one or more paths/globs | yes | none | Sources to analyze and combine. |

### `history`

```bash
wordcount history [--last N] [--format plain|json]
```

| Argument | Type | Required | Default | Valid values | Description |
| --- | --- | --- | --- | --- | --- |
| `--last` | int | no | `10` | positive integer | Number of recent history records to show. |
| `--format` | string | no | `plain` | `plain`, `json` | Output format for history. |

## Input Contract

### Source references

Sources may be:

- A file path.
- A glob pattern.
- `-` for stdin.

For commands accepting multiple sources, glob patterns are expanded. If a glob does not match, the original string is treated as a source path.

### Format detection

If `--input-format` is not supplied:

- `-` maps to text.
- The file extension is used.
- Missing extension defaults to text.

### Supported input formats

| Format | Aliases | Behavior | Dependency |
| --- | --- | --- | --- |
| Plain text | `txt`, `text`, `plain` | Streaming chunks from file or stdin. | stdlib |
| Markdown | `md`, `markdown` | Reads all text, strips common Markdown syntax. | stdlib |
| HTML | `html`, `htm` | Streams through `HTMLParser`, skips script/style. | stdlib |
| JSON | `json` | Reads full JSON, recursively extracts string values. | stdlib |
| DOCX | `docx` | Extracts paragraph text. | `word-counter[docx]` |
| PDF | `pdf` | Extracts page text. | `word-counter[pdf]` |

### Encoding

Text handlers use the specified `--encoding` or detection. If optional `chardet` is unavailable, detection falls back to `utf-8-sig`.

### Tokenizer contract

- `smart`: recognizes URLs, emails, words, numbers, emoji, whitespace, punctuation.
- `regex`: Unicode-aware word groups plus punctuation/whitespace.
- `whitespace`: fast baseline using whitespace/non-whitespace groups.
- `ngram[:N][:base]`: wraps another tokenizer, default `N=2`, default base `smart`.

### Validation

- Unknown output formats are rejected by argparse or formatter factory.
- Unknown input formats raise `UnsupportedFormatError`.
- Unknown tokenizer names raise `TokenizerError`.
- Invalid JSON raises `UnsupportedFormatError`.
- Missing DOCX/PDF dependencies raise `UnsupportedFormatError` with installation guidance.

## Output Contract

### Standard output

Successful commands print one result to stdout.

### Standard error

Handled application errors print:

```text
wordcount: <message>
```

### Output formats

| Format | Structure |
| --- | --- |
| `plain` | Human-readable text; stats include summary rows and top-word bars. |
| `table` | Aligned metric rows. |
| `json` | Pretty JSON with sorted keys where implemented. |
| `csv` | CSV rows with headers. |
| `markdown` | Markdown table. |

### `stats` plain output shape

```text
Text statistics
Characters                     27
Characters without whitespace  23
Bytes                          27
Words                          4
...

Top words
 1. hello ████████████████████████████████     2 (50.00%)
```

ANSI styling appears only when enabled and supported.

### `freq` plain output shape

```text
example: 2
```

### `history` plain output shape

```text
2026-05-09T12:34:56+00:00  stats  essay.txt
```

If empty:

```text
No history yet.
```

## Exit Code Reference

| Exit code | Meaning |
| ---: | --- |
| `0` | Successful command. |
| `2` | Handled application error, invalid tokenizer, unsupported format, decode error, bad value, or argparse parsing failure. |

## Error Output Behavior

Errors caught by CLI print to stderr as:

```text
wordcount: <error message>
```

Argparse errors use argparse’s standard usage/error output and exit behavior.

DOCX missing dependency example:

```text
wordcount: DOCX support requires: pip install word-counter[docx]
```

PDF missing dependency example:

```text
wordcount: PDF support requires: pip install word-counter[pdf]
```

## Environment Variables

| Variable | Effect |
| --- | --- |
| `WORDCOUNT_NO_HISTORY` | If set to any value, disables appending history records. |
| `NO_COLOR` | Disables ANSI color in formatter color auto-detection. |
| `PYTHONPATH` | Development-only way to run from source without installing. |

## Configuration Files

Config path:

```text
~/.wordcount/config.toml
```

Supported defaults used by CLI:

```toml
default_tokenizer = "smart"
default_formatter = "plain"
default_language = "en"
```

Precedence:

1. CLI flags.
2. Config defaults.
3. Built-in defaults.

## Side Effects

- `stats`, `top`, `freq`, `readability`, `diff`, `compare`, and `merge` append to `~/.wordcount/history.jsonl` unless `WORDCOUNT_NO_HISTORY` is set.
- The app reads packaged stopword resource files when `--ignore-stopwords` is used.
- The app reads source files and stdin.
- The app does not modify analyzed input files.

## Usage Examples

### Basic stats

```bash
wordcount essay.txt
```

### Explicit stats with table output

```bash
wordcount stats essay.txt --format table
```

### Stdin

```bash
cat essay.txt | wordcount stats -
```

### Top words, ignoring stopwords

```bash
wordcount top essay.txt -n 20 --ignore-stopwords --language en
```

### Query one word

```bash
wordcount freq essay.txt --word example
```

### Readability

```bash
wordcount readability essay.txt --format markdown
```

### Compare drafts

```bash
wordcount diff draft1.txt draft2.txt --format table
```

### Compare many files

```bash
wordcount compare "chapters/*.txt" --format csv
```

### Merge chapters

```bash
wordcount merge chapter1.txt chapter2.txt chapter3.txt --format json
```

### Smart tokenizer vs whitespace baseline

```bash
wordcount stats essay.txt --tokenizer smart
wordcount stats essay.txt --tokenizer whitespace
```

### N-grams

```bash
wordcount top essay.txt --tokenizer ngram:2:smart -n 20
```

### Markdown input

```bash
wordcount stats README.md --input-format markdown
```

### HTML input

```bash
wordcount stats page.html --input-format html
```

### JSON input

```bash
wordcount stats data.json --input-format json
```

### DOCX input

```bash
python -m pip install -e ".[docx]"
wordcount stats report.docx
```

### PDF input

```bash
python -m pip install -e ".[pdf]"
wordcount stats report.pdf
```

### Disable history for tests/scripts

```bash
WORDCOUNT_NO_HISTORY=1 wordcount stats essay.txt
```

### Intentional failure: unsupported tokenizer

```bash
wordcount stats essay.txt --tokenizer not-real
```

Expected result: stderr message and exit code `2`.

-e

---

# Runbook

## App 39 — Word Counter
**Text Analysis Group | Document 4 of 5**

## Prerequisites

- Python 3.11 or newer.
- Terminal or shell environment.
- No required runtime third-party dependencies for text, Markdown, HTML, JSON, tokenization, formatting, config, stopwords, and history.
- Optional DOCX support: `python-docx` via `word-counter[docx]`.
- Optional PDF support: `pypdf` via `word-counter[pdf]`.
- Development tools: pytest, Ruff, Mypy, Hypothesis from the `dev` extra.

## Installation Procedure

### Standard editable install

```bash
python -m pip install -e .
```

### Install from requirements file

```bash
python -m pip install -r requirements.txt
```

### Install optional DOCX support

```bash
python -m pip install -e ".[docx]"
```

### Install optional PDF support

```bash
python -m pip install -e ".[pdf]"
```

### Install all optional input support

```bash
python -m pip install -e ".[docx,pdf]"
```

### Install development dependencies

```bash
python -m pip install -e ".[dev]"
```

## Configuration Steps

Configuration is optional.

Create:

```text
~/.wordcount/config.toml
```

Example:

```toml
default_tokenizer = "smart"
default_formatter = "plain"
default_language = "en"
```

If the file is absent, the CLI uses built-in defaults.

To disable history for a session:

```bash
export WORDCOUNT_NO_HISTORY=1
```

On PowerShell:

```powershell
$env:WORDCOUNT_NO_HISTORY = "1"
```

## Standard Operating Procedures

### Show help

```bash
wordcount --help
wordcount stats --help
wordcount top --help
```

### Count a text file

```bash
wordcount stats essay.txt
```

### Count stdin

```bash
cat essay.txt | wordcount stats -
```

### Produce machine-readable JSON

```bash
wordcount stats essay.txt --format json
```

### Produce CSV for spreadsheet use

```bash
wordcount stats essay.txt --format csv > stats.csv
```

### Produce Markdown for reports

```bash
wordcount stats essay.txt --format markdown > stats.md
```

### Get top words

```bash
wordcount top essay.txt -n 20 --ignore-stopwords
```

### Query a word

```bash
wordcount freq essay.txt --word architecture
```

### Generate readability scores

```bash
wordcount readability essay.txt --format table
```

### Compare two drafts

```bash
wordcount diff draft1.txt draft2.txt --format markdown
```

### Compare several files

```bash
wordcount compare chapter*.txt --format table
```

### Merge several files into one aggregate

```bash
wordcount merge chapter1.txt chapter2.txt chapter3.txt --format json
```

### Inspect history

```bash
wordcount history --last 10
wordcount history --last 10 --format json
```

## Health Checks

### Version check

```bash
wordcount --version
```

Expected:

```text
word-counter 0.1.0
```

### Minimal stats check

```bash
printf "Hello hello world.\n" | wordcount stats - --format table
```

Expected: output includes a `Words` row with `3`.

### Top-word check

```bash
printf "red blue red\n" | wordcount top - -n 1 --format json
```

Expected JSON includes:

```json
"word": "red"
```

### Handler check: Markdown

Create `sample.md`:

```markdown
# Title
Read [docs](https://example.com).
```

Run:

```bash
wordcount stats sample.md --format table
```

Expected: link URL is not counted as normal visible prose when Markdown handler is selected.

### Handler check: JSON

Create `sample.json`:

```json
{"title":"Hello","items":[{"body":"world"}],"count":2}
```

Run:

```bash
wordcount stats sample.json --format table
```

Expected: string values are analyzed; numeric value `2` is not extracted as JSON text.

## Expected Output Samples

### Table stats

```text
Characters                     18
Characters without whitespace  16
Bytes                          18
Words                          3
Unique words                   2
Lines                          1
Sentences                      1
Paragraphs                     1
...
```

### Top words, plain

```text
 1. red ████████████████████████████████     2 (66.67%)
 2. blue ████████████████                    1 (33.33%)
```

### Frequency

```text
example: 2
```

### History empty

```text
No history yet.
```

## Known Failure Modes

| Symptom | Probable cause | Diagnostic step | Resolution |
| --- | --- | --- | --- |
| `wordcount: Unsupported format '...'` | Bad `--input-format` or unsupported extension | Check command and extension | Use supported format or force `--input-format txt`. |
| `wordcount: DOCX support requires...` | Optional DOCX dependency missing | Run `python -m pip show python-docx` | Install `word-counter[docx]`. |
| `wordcount: PDF support requires...` | Optional PDF dependency missing | Run `python -m pip show pypdf` | Install `word-counter[pdf]`. |
| Decode error | Wrong encoding | Try `--encoding utf-8`, `--encoding utf-8-sig`, or known source encoding | Re-run with correct encoding. |
| Counts differ from `wc -w` | Different tokenizer semantics | Compare with `--tokenizer whitespace` | Use tokenizer matching desired definition. |
| Stopwords not removed | Missing `--ignore-stopwords` or unsupported language | Run with `--ignore-stopwords --language en` | Use packaged language or add another feature later. |
| History unexpectedly written | `WORDCOUNT_NO_HISTORY` not set | Check environment | Set `WORDCOUNT_NO_HISTORY=1`. |
| No ANSI color | stdout is not a TTY, `NO_COLOR` set, or `--no-color` used | Check env/flags | Remove disabling flag/env if color is desired. |
| JSON command fails | Invalid JSON input | Validate file with a JSON parser | Fix JSON or analyze as plain text. |

## Troubleshooting Decision Tree

### The command does not run

1. Run `python --version`.
2. Confirm Python is 3.11+.
3. Run `python -m pip show word-counter`.
4. If not installed, run `python -m pip install -e .`.
5. Try `python -m word_counter --version`.

### The input file is not recognized

1. Check the extension.
2. Run with explicit `--input-format`.
3. For text-like unknown extensions, use `--input-format txt`.
4. For DOCX/PDF, install optional extras.

### The count looks wrong

1. Identify which tokenizer was used.
2. Compare `--tokenizer whitespace`, `--tokenizer regex`, and `--tokenizer smart`.
3. Check whether `--ignore-case`, `--case-sensitive`, `--strip-punctuation`, `--strip-numbers`, or `--ignore-stopwords` changed the result.
4. Use `wordcount top SOURCE --format json` to inspect counted tokens.

### The command is slow or memory-heavy

1. Prefer plain text when analyzing very large documents.
2. Avoid Markdown/JSON handlers for huge files when streaming plain text is acceptable.
3. Increase or tune `--chunk-size` only after testing.
4. Avoid expensive optional PDF extraction for large scanned or layout-heavy PDFs.

### DOCX/PDF fails

1. Confirm optional package is installed.
2. Confirm the file exists and is readable.
3. Confirm the file is actually DOCX/PDF, not a renamed file.
4. For PDF, confirm text extraction is possible; scanned image PDFs may produce little or no text.

### History is unwanted in tests

1. Set `WORDCOUNT_NO_HISTORY=1`.
2. Re-run the command.
3. Optionally remove `~/.wordcount/history.jsonl` if it was already created.

## Dependency Failure Handling

DOCX and PDF handlers catch `ImportError` and raise `UnsupportedFormatError` with install guidance. This keeps the base app lightweight while providing clear next steps for users who need optional formats.

Encoding detection uses optional `chardet` if installed, but falls back to `utf-8-sig`. This means missing `chardet` is not a fatal failure.

## Recovery Procedures

### Reset history

```bash
rm ~/.wordcount/history.jsonl
```

PowerShell:

```powershell
Remove-Item "$HOME\.wordcount\history.jsonl"
```

### Disable history temporarily

```bash
export WORDCOUNT_NO_HISTORY=1
```

### Remove config and return to defaults

```bash
rm ~/.wordcount/config.toml
```

### Reinstall package

```bash
python -m pip uninstall word-counter
python -m pip install -e .
```

## Logging Reference

The app does not use a logging framework. Operational history is stored as JSONL records in:

```text
~/.wordcount/history.jsonl
```

Each record includes timestamp, command, sources, and summary.

## Maintenance Notes

- Keep README examples synchronized with argparse commands and flags.
- Keep optional dependency names in README, `pyproject.toml`, and error messages synchronized.
- Add tests whenever a new tokenizer, handler, normalizer, or formatter is introduced.
- Consider history rotation or a `history clear` command if history grows too large.
- Consider stronger file-not-found handling in CLI if user-facing behavior needs polish.
- Avoid adding heavyweight NLP dependencies unless the project scope changes.
- If PDF/DOCX behavior becomes central, add integration tests guarded by optional dependencies.

## Verification Commands

```bash
python -m pytest
python -m ruff check src tests
python -m mypy src/word_counter
```

The repository includes tests for stats, chunk boundaries, handlers, tokenizers, formatters, config/history, and CLI behavior. I did not run the suite while preparing this document.

-e

---

# Lessons Learned

## App 39 — Word Counter
**Text Analysis Group | Document 5 of 5**

## Project Summary

Word Counter is a streaming-first CLI and Python package for counting words and producing text statistics across multiple input formats. It turns a familiar beginner exercise into a more realistic software design problem: how to count text accurately enough, from several sources, without turning the program into a dependency-heavy NLP platform.

The project’s strongest design choice is the separation between text extraction, tokenization, normalization, filtering, statistics, and formatting. This makes each layer small enough to test and understand while allowing the CLI to support many combinations.

## Original Goals vs. Actual Outcome

### Original goals

- Count words from files and stdin.
- Support common text-derived formats.
- Offer useful text statistics beyond word count.
- Provide multiple output formats.
- Keep the app usable from the command line.
- Demonstrate streaming behavior.

### Actual outcome

The final project goes beyond a basic counter. It supports plain text, Markdown, HTML, JSON, DOCX, and PDF inputs. It includes tokenizers, normalizers, stopword filtering, readability scores, history, config, diff, compare, and merge commands. The app remains standard-library-first and uses optional extras only for DOCX/PDF.

The result is a legitimate CLI utility rather than a toy script.

## Technical Decisions That Paid Off

### Streaming-first analysis

Processing plain text as chunks makes the app more realistic. The token-tail buffer is a small but important detail that shows awareness of real streaming problems.

### Format handlers as adapters

Handlers keep the statistics engine format-agnostic. HTML, Markdown, JSON, DOCX, and PDF all produce chunks of text. This prevented the counter from being duplicated per format.

### Tokenizer strategy

Different users mean different word definitions. Strategy tokenizers made it possible to support fast whitespace counting, Unicode regex counting, smart token preservation, and n-grams with one engine.

### Normalization/filter separation

Separating normalizers from token predicates clarified the pipeline. Case folding and diacritic folding are not the same kind of operation as stopword filtering or minimum-length filtering.

### Immutable `TextStats`

A frozen result object helps preserve clean data flow. It also made derived metrics easy to expose as properties and made merge operations more intentional.

### Multiple formatters

Supporting JSON, CSV, Markdown, table, and plain output makes the tool useful beyond manual terminal use.

### Optional DOCX/PDF extras

Keeping DOCX/PDF optional preserved the dependency-free core and avoided penalizing users who only need text/Markdown/HTML/JSON support.

## Technical Decisions That Created Debt

### Regex Markdown cleanup

The Markdown handler is practical but not complete. Markdown is complex, and regex cleanup can miss edge cases such as nested links, tables, frontmatter, footnotes, or fenced code variations.

### Full-file JSON and Markdown handling

Plain text streams, but Markdown and JSON load full content. This is acceptable for the current scope but creates memory limitations for very large structured files.

### Simple config model

`load_config()` returns a dictionary rather than a typed config object. This is flexible, but it makes validation and documentation weaker than a dataclass-based approach.

### Append-only history

JSONL history is easy to implement and inspect, but it has no retention policy, no compaction, and no command to clear it.

### Heuristic readability

Readability formulas are useful, but syllable estimation is intentionally approximate. Users may over-trust the precision of readability scores.

## What Was Harder Than Expected

### Defining “word”

URLs, emails, contractions, numbers, hyphenated terms, Unicode words, and punctuation make word counting more ambiguous than it first appears. The tokenizer abstraction is a response to that ambiguity.

### Chunk boundaries

Streaming analysis is not just reading chunks. The code must preserve token continuity across chunk boundaries, count lines correctly, and keep paragraph/sentence state across chunk splits.

### Multi-format consistency

Each input format has different extraction semantics. HTML has hidden script/style content. JSON has string and non-string values. Markdown has syntax that may or may not count as visible prose. DOCX and PDF have optional dependency behavior.

### Output compatibility

Plain output can be visually helpful, but JSON/CSV/Markdown outputs need stable structures. Formatting logic can grow quickly if not isolated.

## What Was Easier Than Expected

### Adding output formats

Once `TextStats` was stable, adding JSON, CSV, Markdown, table, and plain renderers became straightforward.

### Stopwords as predicates

Stopword filtering fit naturally into the predicate system. It did not require special cases in the statistics engine.

### CLI command reuse

Most commands reuse the same `analyze_source()` function. The command surface is broad, but the implementation is not heavily duplicated.

### Optional dependency messaging

Failing with installation guidance for DOCX/PDF is simpler and clearer than trying to silently degrade.

## Python-Specific Learnings

- `dataclass(frozen=True)` is useful for result/value objects.
- `Counter` is a strong fit for frequency and distribution tracking.
- `Protocol` allows structural typing for readers, tokenizers, handlers, predicates, and formatters.
- `HTMLParser` is enough for lightweight visible-text extraction from HTML.
- `importlib.resources` is a clean way to package stopword files.
- `argparse` can support a fairly rich CLI without external dependencies.
- `tomllib` makes basic TOML config possible in Python 3.11+.
- Unicode-aware tokenization requires care even when using regular expressions.

## Architecture Insights

The main architectural insight is that a word counter is not one algorithm. It is a pipeline of choices:

```text
source -> handler -> chunks -> normalizers -> tokenizer -> predicates -> stats -> formatter
```

Each arrow is a boundary. Keeping those boundaries explicit made the project easier to expand without rewriting the core.

Another insight is that “streaming” should be treated as a contract. If the app claims to stream, it must handle token tails and stateful counters correctly. Simply reading chunks is not enough.

## Testing Gaps

The existing tests cover many important behaviors, including chunk boundaries, handlers, tokenizers, formatters, config/history, and basic CLI behavior. Remaining gaps include:

- More direct tests for missing DOCX/PDF optional dependencies.
- More tests for bad encoding and file-not-found behavior.
- More tests for large-file behavior and memory assumptions.
- More tests for Markdown edge cases.
- More tests for complex HTML entity and malformed HTML behavior.
- More tests for `diff`, `compare`, `merge`, and `readability` CLI commands end-to-end.
- More tests for `ngram` CLI behavior with multiple tokenizer bases.

## Reusable Patterns Identified

- Strategy registry for user-selectable tokenizers.
- Handler adapter layer for multi-format input tools.
- Frozen aggregate result object with derived metrics.
- Predicate composition for user-specified filtering.
- Formatter factory for multi-output CLI apps.
- JSONL history as an audit trail for CLI runs.
- Environment variable escape hatch for test/script side effects.
- Optional dependency handlers with precise install guidance.

## If I Built This Again

I would keep the pipeline architecture and streaming-first core. I would likely improve the following:

- Replace dictionary config with a typed config dataclass.
- Add a `history clear` command.
- Add explicit file-not-found handling in the CLI.
- Add optional Markdown parser support for more faithful extraction.
- Add a structured report mode that includes both stats and readability together.
- Add a `--no-history` CLI flag in addition to `WORDCOUNT_NO_HISTORY`.
- Add a document explaining exact tokenizer semantics with examples.
- Add benchmark scripts and sample corpora instructions.

## Open Questions

- Should Markdown parsing remain regex-based or use an optional parser?
- Should stopword resources be user-extensible through config?
- Should DOCX/PDF support be tested in CI through optional dependency jobs?
- Should history include command-line flags or only command/source summaries?
- Should `merge` treat source boundaries as whitespace, paragraph breaks, or independent documents?
- Should readability be exposed in `stats` by default or remain a separate command?
- Should the app support directory traversal, or should shell globs remain the intended mechanism?

## Constitution Reflection

### Article 1 — Fundamentals and Architecture

The project demonstrates Python fundamentals through dataclasses, enums, protocols, counters, regex, file I/O, argparse, resources, and structured errors. It demonstrates appropriate architecture through a clean pipeline and strategy/adaptor boundaries.

### Article 2 — Honest Skill Level

The code reflects a strong learner project. It does not pretend to be an industrial NLP library. The README honestly explains that Markdown and JSON handlers load full files and that optional DOCX/PDF dependencies are required for those formats.

### Article 3 — Scope Discipline

The scope is larger than a basic CLI exercise but appropriate for a late portfolio app. The app remains focused on word counting/text statistics rather than expanding into full document conversion or natural language processing.

### Article 4 — Engineering Quality

The project uses clear module boundaries, predictable control flow, reusable strategies, and tested behavior. The main debt is not poor structure, but known simplifications in parsing and config depth.

### Article 5 — Trade-offs

Trade-offs are explicit: standard-library-first runtime, optional DOCX/PDF extras, simple Markdown cleanup, heuristic readability, and streaming priority for plain text.

### Article 6 — Verification

Tests verify statistics, chunk boundaries, handlers, tokenizers, formatters, config/history, and CLI basics. This satisfies behavioral verification for the project scope.

### Article 7 — Progressive Complexity

Compared with earlier text utilities, this app shows progression in streaming I/O, strategy composition, multi-format adapters, structured outputs, config, history, and derived metrics.

### Article 8 — Final Evaluation

Word Counter is a valid and portfolio-worthy project. It is authentic, appropriately scoped, architecturally intentional, testable, and reflective. Its weaknesses are reasonable for the learning stage and are mostly documented trade-offs rather than hidden flaws.

-e
