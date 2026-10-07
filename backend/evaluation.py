import re
from backend.models import ClaimVerification, EvaluationReport, RetrievedChunk

CITATION_REGEX = re.compile(r"\[Doc:\s*([^,\]]+),\s*Page\s*(\d+),\s*Line\s*(\d+)-(\d+)\]")
QUOTE_REGEX = re.compile(r'"([^"\n]{12,})"')


def evaluate_grounding(response_text: str, chunks: list[RetrievedChunk]) -> EvaluationReport:
    """Evaluates factual grounding and citation attribution of an answer against retrieved chunks.

    IMPORTANT: All scores are HEURISTIC metrics based on lexical overlap and citation parsing,
    not calibrated empirical accuracy models.
    """
    # 1. Refusal check
    if "do not contain information" in response_text.lower():
        return EvaluationReport(
            is_grounded=True,
            unsupported_claim_rate_heuristic=0.0,
            grounding_confidence_heuristic=1.0,
            total_citations_found=0,
            citations_verified=0,
            total_quotes_found=0,
            verbatim_quotes_matched=0,
            unsupported_claims_flagged=0,
            verdict="GROUNDED_REFUSAL (heuristic)",
            audit_notes=["Grounded refusal: model confirmed context lacked requested facts."],
            claim_matrix=[]
        )

    # 2. No context check
    if not chunks:
        return EvaluationReport(
            is_grounded=False,
            unsupported_claim_rate_heuristic=1.0,
            grounding_confidence_heuristic=0.0,
            total_citations_found=0,
            citations_verified=0,
            total_quotes_found=0,
            verbatim_quotes_matched=0,
            unsupported_claims_flagged=0,
            verdict="NO_CONTEXT (heuristic)",
            audit_notes=["No context chunks were retrieved."],
            claim_matrix=[]
        )

    # 3. Extract citations
    citations = CITATION_REGEX.findall(response_text)
    total_citations_found = len(citations)
    citations_verified = 0

    chunk_docs = {c.doc_name.lower(): c for c in chunks}
    for doc_name, page, s_line, e_line in citations:
        doc_clean = doc_name.strip().lower()
        # Verify against retrieved chunks
        matched = False
        for c_doc in chunk_docs:
            if doc_clean in c_doc or c_doc in doc_clean:
                matched = True
                break
        if matched:
            citations_verified += 1

    citation_present_rate = (
        (citations_verified / total_citations_found) if total_citations_found > 0 else 0.0
    )

    # 4. Extract quotes
    quotes = QUOTE_REGEX.findall(response_text)
    total_quotes_found = len(quotes)

    # 5. Check verbatim quotes
    all_chunks_text = " ".join(c.text for c in chunks).lower()
    norm_corpus = re.sub(r"\s+", " ", all_chunks_text)

    verbatim_quotes_matched = 0
    for q in quotes:
        norm_q = re.sub(r"\s+", " ", q.strip().lower())
        if norm_q in norm_corpus:
            verbatim_quotes_matched += 1

    quote_match_rate = (
        (verbatim_quotes_matched / total_quotes_found) if total_quotes_found > 0 else 1.0
    )

    # 6. Extract claims (bullet lines and full sentences, ignoring metadata lines)
    raw_lines = response_text.split("\n")
    candidate_claims = []
    for line in raw_lines:
        line_s = line.strip()
        if not line_s or line_s.startswith("Note:") or line_s.startswith("Based on"):
            continue
        # Split into sentences
        for s in re.split(r"(?<=[.!?])\s+", line_s):
            # Strip citations and quotes markers
            cleaned_s = CITATION_REGEX.sub("", s).replace('"', '').strip()
            if len(cleaned_s) >= 15:
                candidate_claims.append(cleaned_s)

    # 7. Verify claims via token overlap
    claim_matrix: list[ClaimVerification] = []
    verified_count = 0
    inferred_count = 0
    unsupported_count = 0

    for claim in candidate_claims:
        c_tokens = set(re.findall(r"\w+", claim.lower()))
        if not c_tokens:
            continue

        best_overlap = 0.0
        best_chunk: RetrievedChunk | None = None

        for ch in chunks:
            ch_tokens = set(re.findall(r"\w+", ch.text.lower()))
            overlap = len(c_tokens.intersection(ch_tokens)) / max(1, len(c_tokens))
            if overlap > best_overlap:
                best_overlap = overlap
                best_chunk = ch

        if best_overlap >= 0.50:
            status = "VERIFIED"
            verified_count += 1
        elif best_overlap >= 0.25:
            status = "INFERRED"
            inferred_count += 1
        else:
            status = "UNSUPPORTED"
            unsupported_count += 1

        v_doc = best_chunk.doc_name if best_chunk else None
        v_lines = f"{best_chunk.start_line}-{best_chunk.end_line}" if best_chunk else None
        snippet = best_chunk.text[:80] + "..." if best_chunk else None

        claim_matrix.append(
            ClaimVerification(
                claim_text=claim,
                status=status,
                verifying_doc=v_doc,
                verifying_lines=v_lines,
                confidence_heuristic=round(best_overlap, 3),
                evidence_snippet=snippet
            )
        )

    total_claims = len(claim_matrix)
    verified_claim_rate = (verified_count / total_claims) if total_claims > 0 else 1.0

    # 8. Compute heuristic metrics
    grounding_confidence_heuristic = (
        0.45 * quote_match_rate +
        0.25 * citation_present_rate +
        0.30 * verified_claim_rate
    )
    grounding_confidence_heuristic = max(0.0, min(1.0, grounding_confidence_heuristic))
    unsupported_claim_rate_heuristic = max(0.0, round(1.0 - grounding_confidence_heuristic, 3))
    grounding_confidence_heuristic = round(grounding_confidence_heuristic, 3)

    is_grounded = grounding_confidence_heuristic >= 0.70 and unsupported_count <= (total_claims // 2)
    verdict = (
        f"GROUNDED (heuristic score: {grounding_confidence_heuristic})"
        if is_grounded
        else f"POTENTIAL_HALLUCINATION (heuristic score: {grounding_confidence_heuristic})"
    )

    audit_notes = [
        f"Grounding confidence (heuristic): {grounding_confidence_heuristic}",
        f"Unsupported claim rate (heuristic): {unsupported_claim_rate_heuristic}",
        f"Citations matched: {citations_verified}/{total_citations_found}",
        f"Verbatim quotes matched: {verbatim_quotes_matched}/{total_quotes_found}",
        f"Claims matrix: {verified_count} verified, {inferred_count} inferred, {unsupported_count} unsupported"
    ]

    return EvaluationReport(
        is_grounded=is_grounded,
        unsupported_claim_rate_heuristic=unsupported_claim_rate_heuristic,
        grounding_confidence_heuristic=grounding_confidence_heuristic,
        total_citations_found=total_citations_found,
        citations_verified=citations_verified,
        total_quotes_found=total_quotes_found,
        verbatim_quotes_matched=verbatim_quotes_matched,
        unsupported_claims_flagged=unsupported_count,
        verdict=verdict,
        audit_notes=audit_notes,
        claim_matrix=claim_matrix
    )
