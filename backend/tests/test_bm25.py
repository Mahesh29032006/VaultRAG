from backend.bm25 import BM25Index, tokenize_bm25


def test_bm25_tokenization_preserves_numbers_and_hyphens():
    text = "Dosage 20mg at $2,000 cost under zero-trust policy ratio 24/26."
    tokens = tokenize_bm25(text)
    assert "20mg" in tokens
    assert "$2000" in tokens
    assert "zero-trust" in tokens
    assert "24/26" in tokens


def test_bm25_empty_index_returns_zero():
    idx = BM25Index()
    assert idx.score("anything", "c1") == 0.0
    assert idx.search("anything") == []


def test_bm25_search_ranking():
    idx = BM25Index()
    idx.add("c1", "Torsemide 20mg oral daily for acute heart failure patients.")
    idx.add("c2", "Delaware law governs this enterprise software contract liability cap.")
    idx.add("c3", "Torsemide dosage adjustments in elderly clinical trials.")

    results = idx.search("Torsemide 20mg", top_k=2)
    assert len(results) == 2
    assert results[0][0] == "c1"  # Best match has both Torsemide and 20mg


def test_bm25_unknown_term_scores_zero():
    idx = BM25Index()
    idx.add("c1", "Basic document about cardiology")
    assert idx.score("astrophysics quantum", "c1") == 0.0
    assert idx.search("astrophysics quantum") == []


def test_bm25_remove_chunk_updates_index():
    idx = BM25Index()
    idx.add("c1", "First doc")
    idx.add("c2", "Second doc")
    assert idx.N == 2

    idx.remove("c1")
    assert idx.N == 1
    assert "c1" not in idx.doc_tokens
    assert idx.score("first", "c1") == 0.0


def test_bm25_remove_missing_chunk_safe_noop():
    idx = BM25Index()
    idx.add("c1", "First doc")
    idx.remove("non_existent_chunk_id")
    assert idx.N == 1


def test_bm25_add_batch_rebuilds_stats():
    idx = BM25Index()
    idx.add_batch([("b1", "Batch doc one"), ("b2", "Batch doc two")])
    assert idx.N == 2
    assert idx.avgdl > 0
