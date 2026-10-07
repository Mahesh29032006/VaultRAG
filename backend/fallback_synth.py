import re
from backend.models import RetrievedChunk


def _extract_best_sentences(text: str, query: str, max_sentences: int = 2) -> list[str]:
    # Split text into clean sentences
    raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", text) if s.strip()]
    if not raw_sentences:
        return []

    q_words = set(re.findall(r"\w+", query.lower()))

    # Score each sentence by overlap with query
    scored_sentences = []
    for idx, s in enumerate(raw_sentences):
        s_words = set(re.findall(r"\w+", s.lower()))
        overlap = len(q_words.intersection(s_words))
        scored_sentences.append((overlap, -idx, s))

    # Sort by overlap descending, then by original position
    scored_sentences.sort(reverse=True)
    selected = [item[2] for item in scored_sentences[:max_sentences]]
    return selected


def generate(query: str, chunks: list[RetrievedChunk]) -> str:
    """Deterministic grounded synthesis when Ollama is offline.

    Extracts verbatim evidence snippets with precise document and line citations.
    """
    if not chunks:
        return "The provided documents do not contain information regarding this query."

    # Pick top-3 by rrf_score
    top_chunks = sorted(chunks, key=lambda c: c.rrf_score, reverse=True)[:3]

    sections = []
    for c in top_chunks:
        best_sentences = _extract_best_sentences(c.text, query, max_sentences=2)
        if not best_sentences:
            continue

        citation = c.citation_label
        evidence_quotes = " ".join([f'"{s}"' for s in best_sentences])
        section = f"Based on verified local documentation [{citation}]:\n{evidence_quotes} [{citation}]"
        sections.append(section)

    if not sections:
        return "The provided documents do not contain information regarding this query."

    body = "\n\n".join(sections)
    suffix = "\n\nNote: Local LLM unavailable. Response synthesized deterministically from retrieved chunks only."
    return body + suffix
