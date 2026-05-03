# Word Counter

Word Counter is a streaming-first Python CLI for counting words and producing text statistics from plain text, Markdown, HTML, JSON, DOCX, and PDF sources.

The stdlib path covers text, Markdown, HTML, JSON, tokenization, filtering, formatting, config, and history. DOCX and PDF support are optional extras that fail with install guidance when their dependencies are not present.

**Requirements:** Python 3.11 or newer.

## Install

Editable install from the repository root:

```powershell
python -m pip install -e .
```

Using `requirements.txt` (also editable; matches `pyproject.toml`):

```powershell
python -m pip install -r requirements.txt
```

Optional input formats:

```powershell
python -m pip install -e ".[docx]"
python -m pip install -e ".[pdf]"
python -m pip install -e ".[docx,pdf]"
```

During development you can run without installing:

```powershell
$env:PYTHONPATH = "src"
python -m word_counter stats "Word Counter.txt"
```

On macOS or Linux:

```bash
export PYTHONPATH=src
python -m word_counter stats "Word Counter.txt"
```

## Usage

```powershell
wordcount "essay.txt"
wordcount stats "essay.txt" --format table
wordcount top "essay.txt" -n 20 --ignore-stopwords
wordcount freq "essay.txt" --word example
wordcount readability "essay.txt"
wordcount diff draft1.txt draft2.txt
wordcount compare *.txt --format markdown
wordcount merge chapter1.txt chapter2.txt --format json
Get-Content .\essay.txt | wordcount stats -
```

Useful flags:

```text
--tokenizer smart|regex|whitespace|ngram[:N][:base]
--format plain|table|json|csv|markdown
--input-format txt|markdown|html|json|docx|pdf
--case-sensitive
--fold-diacritics
--strip-punctuation
--strip-numbers
--ignore-stopwords --language en|es|fr
--min-length N --max-length N --only-alpha --grep PATTERN
```

## Development

Install with dev dependencies (tests, type checking, linting):

```powershell
python -m pip install -e ".[dev]"
```

Run the test suite, linter, and type checker:

```powershell
python -m pytest
python -m ruff check src tests
python -m mypy src/word_counter
```

See `ARCHITECTURE.md` and `BENCHMARKS.md` for design and performance notes.

## Format matrix

| Input | Handler | Dependencies |
| --- | --- | --- |
| `.txt` | streaming plain text | stdlib |
| `.md` | regex Markdown cleanup | stdlib |
| `.html`, `.htm` | `html.parser`, skips script/style | stdlib |
| `.json` | recursive string extraction | stdlib |
| `.docx` | paragraph extraction | `word-counter[docx]` |
| `.pdf` | page text extraction | `word-counter[pdf]` |

| Output | Good for |
| --- | --- |
| `plain` | human-readable terminal stats and top-word bars |
| `table` | compact terminal summaries |
| `json` | piping into tools such as `jq` |
| `csv` | spreadsheets |
| `markdown` | reports and GitHub issues |

## Design notes

The plain-text path reads chunks and keeps a token tail so words split across chunk boundaries are not counted twice or lost. Tokenizers are strategies selected by `--tokenizer`, normalizers are composable, and filters are simple callables. `TextStats.__add__` combines independent sources for `merge` and batch reporting.

Markdown and JSON handlers load the full file into memory for parsing; large files are best counted as plain text or streamed HTML where applicable.

Configuration is read from `~/.wordcount/config.toml` when present. History is appended to `~/.wordcount/history.jsonl` unless `WORDCOUNT_NO_HISTORY=1` is set.
