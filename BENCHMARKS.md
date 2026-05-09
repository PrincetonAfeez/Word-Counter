# Benchmarks

Benchmark target: Project Gutenberg's `War and Peace` text or any local corpus of similar size.

Example command:

```powershell
$env:PYTHONPATH = "src"
Measure-Command { python -m word_counter stats .\war-and-peace.txt --format table --no-color }
```

Memory expectations:

- Plain text processing uses fixed-size reads with a small token tail.
- Word frequencies grow with vocabulary size, not file size.
- Sentence and word-length distributions grow with observed distinct lengths.

Baseline comparison:

```powershell
python -m word_counter stats .\war-and-peace.txt --format json
cmd /c "type war-and-peace.txt | wc -w"
```

`wc -w` and Word Counter do not always agree because Word Counter can preserve contractions, URLs, emails, and Unicode words depending on the selected tokenizer. The `whitespace` tokenizer gives the closest baseline comparison.
