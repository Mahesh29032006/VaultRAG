import pytest
from backend.chunker import Chunker


def test_chunker_empty_and_whitespace_returns_empty():
    assert Chunker.chunk("") == []
    assert Chunker.chunk("   \n\t  \n  ") == []


def test_chunker_text_under_chunk_size_single_chunk():
    text = "Short text block under 450 characters."
    chunks = Chunker.chunk(text, chunk_size=450, overlap=60)
    assert len(chunks) == 1
    assert chunks[0].content == text
    assert chunks[0].chunk_index == 0


def test_chunker_text_exactly_chunk_size_single_chunk():
    text = "A" * 450
    chunks = Chunker.chunk(text, chunk_size=450, overlap=60)
    assert len(chunks) == 1
    assert len(chunks[0].content) == 450


def test_chunker_text_chunk_size_plus_one_produces_two_chunks():
    text = "B" * 451
    chunks = Chunker.chunk(text, chunk_size=450, overlap=60)
    assert len(chunks) == 2


def test_chunker_overlap_greater_or_equal_raises_value_error():
    with pytest.raises(ValueError, match="overlap"):
        Chunker.chunk("Some text", chunk_size=100, overlap=100)
    with pytest.raises(ValueError, match="overlap"):
        Chunker.chunk("Some text", chunk_size=100, overlap=120)


def test_chunker_one_million_char_single_line_terminates():
    long_line = "word " * 200_000  # 1M chars
    chunks = Chunker.chunk(long_line, chunk_size=500, overlap=50)
    assert len(chunks) > 1000
    assert all(len(c.content) <= 500 for c in chunks)


def test_chunker_repeated_blank_lines_no_empty_chunks():
    text = "Paragraph One.\n\n\n\n\n\nParagraph Two.\n\n\nParagraph Three."
    chunks = Chunker.chunk(text, chunk_size=100, overlap=20)
    assert len(chunks) >= 1
    for c in chunks:
        assert c.content.strip() != ""


def test_chunker_unicode_char_counts_accurate():
    hindi_chinese = "नमस्ते दुनिया! 你好世界! 🌍🚀 " * 20
    chunks = Chunker.chunk(hindi_chinese, chunk_size=200, overlap=30)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c.content) <= 200


def test_chunker_huge_single_word_hard_split():
    huge_word = "X" * 10_000
    chunks = Chunker.chunk(huge_word, chunk_size=400, overlap=50)
    assert len(chunks) > 20
    assert all(len(c.content) <= 400 for c in chunks)
