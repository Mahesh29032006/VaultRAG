from collections import defaultdict


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion (RRF) over multiple ranked lists of chunk_ids.

    Formula:
      score(d) = sum_{rankings} (1.0 / (k + rank(d)))
      where rank(d) is 1-indexed. Absent chunks contribute 0.
    """
    if not rankings:
        return []

    scores: dict[str, float] = defaultdict(float)
    first_seen_index: dict[str, int] = {}
    counter = 0

    has_entries = False
    for ranking in rankings:
        if not ranking:
            continue
        has_entries = True
        for rank_idx, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] += 1.0 / (k + rank_idx)
            if chunk_id not in first_seen_index:
                first_seen_index[chunk_id] = counter
                counter += 1

    if not has_entries or not scores:
        return []

    # Sort primarily by score descending, secondary tie-breaker by arrival order
    sorted_items = sorted(
        scores.items(),
        key=lambda item: (item[1], -first_seen_index[item[0]]),
        reverse=True
    )

    return [(cid, round(score, 6)) for cid, score in sorted_items]
