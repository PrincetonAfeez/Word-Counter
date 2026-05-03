# Word Counter

Word Counter is a streaming-first Python CLI for counting words and producing text statistics from plain text, Markdown, HTML, JSON, DOCX, and PDF sources.

The stdlib path covers text, Markdown, HTML, JSON, tokenization, filtering, formatting, config, and history. DOCX and PDF support are optional extras that fail with install guidance when their dependencies are not present.

## Install

```powershell
python -m pip install -e .
```

During development you can also run it without installing:

```powershell
$env:PYTHONPATH = "src"
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

## Format Matrix

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

## Design Notes

The plain-text path reads chunks and keeps a token tail so words split across chunk boundaries are not counted twice or lost. Tokenizers are strategies selected by `--tokenizer`, normalizers are composable, and filters are simple callables. `TextStats.__add__` combines independent sources for `merge` and batch reporting.

Configuration is read from `~/.wordcount/config.toml` when present. History is appended to `~/.wordcount/history.jsonl` unless `WORDCOUNT_NO_HISTORY=1` is set.
