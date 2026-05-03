"""Statistics utilities tests for the word_counter package."""

from __future__ import annotations

from word_counter.normalization import CaseFolder
from word_counter.stats import analyze_chunks, analyze_text, readability_scores
from word_counter.tokenizers import SmartTokenizer


def test_analyze_text_counts_core_statistics() -> None:
    stats = analyze_text("Hello, world!\n\nHello again.")
    assert stats.character_count == 27
    assert stats.word_count == 4
    assert stats.line_count == 3
    assert stats.sentence_count == 2
    assert stats.paragraph_count == 2
    assert stats.word_frequencies["hello"] == 2
    assert stats.unique_word_count == 3


def test_chunk_boundaries_do_not_split_words() -> None:
    text = "streaming boundary handling keeps contractions like don't intact"
    whole = analyze_text(text)
    chunked = analyze_chunks(
        (text[index : index + 3] for index in range(0, len(text), 3)),
        tokenizer=SmartTokenizer(),
        normalizers=(CaseFolder(),),
    )
    assert chunked.word_count == whole.word_count
    assert chunked.word_frequencies == whole.word_frequencies


def test_textstats_add_rebuilds_in_memory_concatenation() -> None:
    left = analyze_text("hello")
    right = analyze_text("world")
    combined = analyze_text("helloworld")
    assert left + right == combined


def test_readability_scores_return_three_algorithms() -> None:
    scores = readability_scores(analyze_text("The cat sat. The dog ran."))
    assert [score.algorithm_name for score in scores] == [
        "Flesch Reading Ease",
        "Flesch-Kincaid Grade",
        "Coleman-Liau Index",
    ]
