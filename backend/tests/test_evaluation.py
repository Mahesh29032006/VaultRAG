from backend.evaluation import evaluate_grounding
from backend.models import RetrievedChunk


def test_evaluation_refusal_returns_grounded_refusal():
    rep = evaluate_grounding("The provided documents do not contain information regarding this query.", [])
    assert rep.is_grounded is True
    assert rep.unsupported_claim_rate_heuristic == 0.0
    assert rep.grounding_confidence_heuristic == 1.0
    assert "GROUNDED_REFUSAL" in rep.verdict


def test_evaluation_empty_chunks_returns_no_context():
    rep = evaluate_grounding("Some arbitrary statement.", [])
    assert rep.is_grounded is False
    assert rep.unsupported_claim_rate_heuristic == 1.0
    assert "NO_CONTEXT" in rep.verdict


def test_evaluation_grounded_with_quotes_and_citations():
    chunk = RetrievedChunk(
        chunk_id="c1",
        doc_name="clinical_ehr.txt",
        category="CLINICAL",
        page_number=1,
        start_line=1,
        end_line=5,
        text="Patient prescribed Torsemide 20 mg oral daily for heart failure.",
        similarity_score=0.9,
        bm25_score=3.5,
        rrf_score=0.03,
        citation_label="Doc: clinical_ehr.txt, Page 1, Line 1-5"
    )
    response = (
        'Based on verified records [Doc: clinical_ehr.txt, Page 1, Line 1-5]:\n'
        '"Patient prescribed Torsemide 20 mg oral daily for heart failure." '
        '[Doc: clinical_ehr.txt, Page 1, Line 1-5]'
    )
    rep = evaluate_grounding(response, [chunk])
    assert rep.citations_verified >= 1
    assert rep.verbatim_quotes_matched >= 1
    assert rep.grounding_confidence_heuristic >= 0.80
    assert rep.unsupported_claim_rate_heuristic <= 0.20
    assert "heuristic" in rep.verdict.lower()


def test_evaluation_unsupported_hallucination_flagged():
    chunk = RetrievedChunk(
        chunk_id="c1",
        doc_name="notes.txt",
        category="GENERAL",
        page_number=1,
        start_line=1,
        end_line=2,
        text="The weather in San Francisco was sunny and mild yesterday.",
        similarity_score=0.5,
        bm25_score=1.0,
        rrf_score=0.01,
        citation_label="Doc: notes.txt, Page 1, Line 1-2"
    )
    response = "The reactor core temperature exceeded 5000 Kelvin causing immediate containment failure."
    rep = evaluate_grounding(response, [chunk])
    assert rep.is_grounded is False
    assert rep.unsupported_claims_flagged >= 1


def test_evaluation_metric_names_contain_heuristic():
    rep = evaluate_grounding("No context response", [])
    assert hasattr(rep, "grounding_confidence_heuristic")
    assert hasattr(rep, "unsupported_claim_rate_heuristic")


def test_evaluation_claim_matrix_statuses():
    chunk = RetrievedChunk(
        chunk_id="c1",
        doc_name="tech.txt",
        category="GENERAL",
        page_number=1,
        start_line=1,
        end_line=3,
        text="mTLS and SPIFFE authentication enforce zero trust security.",
        similarity_score=0.9,
        bm25_score=2.0,
        rrf_score=0.02,
        citation_label="Doc: tech.txt, Page 1, Line 1-3"
    )
    response = (
        "SPIFFE authentication enforces zero trust security principles.\n"
        "Unrelated statement about lunar exploration vehicles."
    )
    rep = evaluate_grounding(response, [chunk])
    statuses = {c.status for c in rep.claim_matrix}
    assert "VERIFIED" in statuses or "INFERRED" in statuses
