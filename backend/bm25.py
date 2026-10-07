import logging
import math
import re
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)


STOPWORDS = {
    "what", "is", "the", "a", "an", "of", "in", "to", "and", "or", "for", "on",
    "with", "as", "by", "at", "from", "it", "this", "that", "are", "was", "were",
    "be", "been", "have", "has", "had", "do", "does", "did", "how", "why", "when",
    "which", "who", "whom"
}


def tokenize_bm25(text: str) -> list[str]:
    """Tokenize preserving numbers, units ($2,000, 20mg, 3.5), and hyphenated terms."""
    if not text:
        return []
    cleaned = text.lower()
    # Normalize common commas inside numbers like $2,000 -> $2000
    cleaned = re.sub(r"(?<=\d),(?=\d)", "", cleaned)
    raw_tokens = re.findall(r"[\$%\w]+(?:[-./][\$%\w]+)*", cleaned)
    tokens = [t.strip(".,;:?!") for t in raw_tokens]
    return [t for t in tokens if len(t) >= 2 and t not in STOPWORDS]


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_ids: list[str] = []
        self.doc_tokens: dict[str, list[str]] = {}
        self.doc_len: dict[str, int] = {}
        self.tf: dict[str, Counter[str]] = {}
        self.df: Counter[str] = Counter()
        self.N: int = 0
        self.avgdl: float = 0.0

    def rebuild_stats(self) -> None:
        self.N = len(self.doc_ids)
        if self.N == 0:
            self.avgdl = 0.0
            self.df.clear()
            return

        self.df.clear()
        total_len = 0
        for cid in self.doc_ids:
            tokens = self.doc_tokens[cid]
            total_len += len(tokens)
            unique_terms = set(tokens)
            for t in unique_terms:
                self.df[t] += 1

        self.avgdl = total_len / self.N

    def add(self, chunk_id: str, text: str) -> None:
        if chunk_id in self.doc_tokens:
            self.remove(chunk_id)

        tokens = tokenize_bm25(text)
        self.doc_ids.append(chunk_id)
        self.doc_tokens[chunk_id] = tokens
        self.doc_len[chunk_id] = len(tokens)
        self.tf[chunk_id] = Counter(tokens)

        self.rebuild_stats()

    def add_batch(self, chunks: list[tuple[str, str]]) -> None:
        for chunk_id, text in chunks:
            if chunk_id in self.doc_tokens:
                self.remove(chunk_id)
            tokens = tokenize_bm25(text)
            self.doc_ids.append(chunk_id)
            self.doc_tokens[chunk_id] = tokens
            self.doc_len[chunk_id] = len(tokens)
            self.tf[chunk_id] = Counter(tokens)

        self.rebuild_stats()

    def remove(self, chunk_id: str) -> None:
        if chunk_id not in self.doc_tokens:
            logger.warning("Attempted to remove non-existent chunk_id from BM25 index: %s", chunk_id)
            return

        self.doc_ids = [cid for cid in self.doc_ids if cid != chunk_id]
        del self.doc_tokens[chunk_id]
        del self.doc_len[chunk_id]
        del self.tf[chunk_id]

        self.rebuild_stats()

    def score(self, query: str, chunk_id: str) -> float:
        if self.N == 0 or chunk_id not in self.doc_tokens:
            return 0.0

        q_tokens = tokenize_bm25(query)
        if not q_tokens:
            return 0.0

        dl = self.doc_len[chunk_id]
        if self.avgdl == 0.0:
            return 0.0

        tf_map = self.tf[chunk_id]
        total_score = 0.0

        for term in q_tokens:
            if term not in tf_map or term not in self.df:
                continue

            tf = tf_map[term]
            df = self.df[term]

            # Exact Formula: IDF(q) = ln( (N - df + 0.5) / (df + 0.5) + 1 )
            numerator = self.N - df + 0.5
            denominator = df + 0.5
            idf = math.log((numerator / denominator) + 1.0)

            # score = IDF * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))
            denom = tf + self.k1 * (1.0 - self.b + self.b * (dl / self.avgdl))
            if denom > 0:
                total_score += idf * (tf * (self.k1 + 1.0)) / denom

        return total_score

    def search(self, query: str, top_k: int = 20) -> list[tuple[str, float]]:
        if self.N == 0:
            return []

        q_tokens = tokenize_bm25(query)
        if not q_tokens:
            return []

        # Find candidate documents containing at least one query term
        candidate_ids = set()
        for term in q_tokens:
            if term in self.df:
                for cid in self.doc_ids:
                    if term in self.tf[cid]:
                        candidate_ids.add(cid)

        if not candidate_ids:
            return []

        scored = []
        for cid in candidate_ids:
            s = self.score(query, cid)
            if s > 0.0:
                scored.append((cid, float(s)))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def clear(self) -> None:
        self.doc_ids.clear()
        self.doc_tokens.clear()
        self.doc_len.clear()
        self.tf.clear()
        self.df.clear()
        self.N = 0
        self.avgdl = 0.0
