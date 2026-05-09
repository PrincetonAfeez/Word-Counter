# Architecture

## Streaming-First Design

Plain text is processed as chunks from a `StreamingReader`. The statistics engine updates character, byte, line, paragraph, sentence, token, and distribution counts as chunks arrive. A token tail buffers the final non-whitespace run from each chunk, then joins it with the next chunk so split words are preserved.

Markdown, HTML, and JSON use format handlers that adapt structured content into text chunks. HTML is parsed with the stdlib `HTMLParser` and skips `script` and `style` content.

## Tokenization As Strategy

Tokenizers implement a `Tokenizer` protocol:

- `WhitespaceTokenizer` is fast and naive.
- `RegexTokenizer` uses Unicode-aware word matching.
- `SmartTokenizer` preserves contractions and hyphenated words, and recognizes URLs and emails.
- `NgramTokenizer` wraps another tokenizer and emits configurable n-grams.

The CLI selects these through `TokenizerRegistry` and the `--tokenizer` flag.

## Normalization As Pipeline

Normalization is separate from tokenization. `NormalizationPipeline` runs ordered normalizers such as `CaseFolder`, `DiacriticFolder`, `PunctuationStripper`, and `NumberStripper`.

Stopwords are intentionally implemented as token predicates because they operate after tokenization. That keeps concerns clear: text-shape changes happen before tokenization, token inclusion decisions happen after tokenization.

## Statistics As Pure Reads

`analyze_chunks` builds one immutable `TextStats` value. Derived metrics such as average word length, type-token ratio, hapax ratio, and sentence averages read from that value. Readability scores are pure functions of `TextStats` plus a documented syllable heuristic.

## Mergeability Proof

`TextStats.__add__` combines counts and counters from independent sources. The CLI uses that in `wordcount merge`. In-memory `analyze_text` also keeps enough context to rebuild exact concatenation stats during tests and small programmatic use.
