from backend.rrf import reciprocal_rank_fusion


def test_rrf_empty_rankings_returns_empty():
    assert reciprocal_rank_fusion([]) == []


def test_rrf_all_rankings_empty_returns_empty():
    assert reciprocal_rank_fusion([[], [], []]) == []


def test_rrf_single_ranking_preserves_order():
    ranking = ["docA", "docB", "docC"]
    fused = reciprocal_rank_fusion([ranking], k=60)
    assert [cid for cid, _ in fused] == ["docA", "docB", "docC"]
    assert fused[0][1] > fused[1][1] > fused[2][1]


def test_rrf_fusion_multiple_lists_scoring():
    dense = ["docA", "docB", "docC"]
    bm25 = ["docB", "docA", "docD"]
    fused = reciprocal_rank_fusion([dense, bm25], k=60)

    # docA and docB both have 2 appearances, so should be top 2
    top_two = [cid for cid, _ in fused[:2]]
    assert "docA" in top_two
    assert "docB" in top_two

    # docC and docD have 1 appearance each
    assert fused[2][1] < fused[1][1]


def test_rrf_absent_chunk_contributes_zero():
    list1 = ["docX"]
    list2 = ["docY"]
    fused = reciprocal_rank_fusion([list1, list2], k=60)
    assert len(fused) == 2
    # Both ranked #1 in their respective single list -> same score 1/(60+1)
    assert fused[0][1] == fused[1][1]
