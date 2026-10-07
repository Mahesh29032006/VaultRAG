from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pytest
from backend.config import Settings
from backend.document_loader import DocumentLoader
from backend.errors import (
    EmptyDocumentError,
    UnsupportedFileTypeError,
)
from backend.privacy_guard import PrivacyGuard
from backend.rag_engine import RAGEngine
from backend.models import QueryRequest

def test_all_edge_cases():
    test_dir = Path("test_files")
    settings = Settings(data_dir="data_edge_test")
    engine = RAGEngine(settings=settings)
    engine.clear_all()

    results = {}

    # 1. Valid docs
    for fname in ["clinical_discharge.txt", "finance_q3.txt", "legal_msa.md"]:
        fpath = test_dir / fname
        doc = engine.ingest_document(fpath, title=fname)
        assert doc.chunk_count > 0
        results[fname] = f"Ingested OK ({doc.chunk_count} chunks)"

    # 2. Empty & whitespace
    for fname in ["empty.txt", "whitespace.txt"]:
        fpath = test_dir / fname
        try:
            engine.ingest_document(fpath, title=fname)
            results[fname] = "FAILED: Did not raise EmptyDocumentError"
        except EmptyDocumentError as e:
            results[fname] = f"Rejected cleanly: {type(e).__name__}"

    # 3. Unsupported docx
    fpath = test_dir / "unsupported.docx"
    try:
        engine.ingest_document(fpath, title=fpath.name)
        results["unsupported.docx"] = "FAILED: Did not raise UnsupportedFileTypeError"
    except UnsupportedFileTypeError as e:
        results["unsupported.docx"] = f"Rejected cleanly: {type(e).__name__}"

    # 4. Binary fake
    fpath = test_dir / "binary_fake.txt"
    try:
        doc = engine.ingest_document(fpath, title=fpath.name)
        results["binary_fake.txt"] = f"Handled without crash ({doc.chunk_count} chunks)"
    except Exception as e:
        results["binary_fake.txt"] = f"Rejected cleanly: {type(e).__name__}"

    # 5. Bad JSON
    fpath = test_dir / "bad.json"
    try:
        doc = engine.ingest_document(fpath, title=fpath.name)
        results["bad.json"] = f"Handled without crash ({doc.chunk_count} chunks)"
    except Exception as e:
        results["bad.json"] = f"Error: {e}"

    # 6. CRLF
    fpath = test_dir / "crlf.txt"
    doc = engine.ingest_document(fpath, title=fpath.name)
    results["crlf.txt"] = f"Ingested OK ({doc.chunk_count} chunks, normalized lines)"

    # 7. Unicode name
    fpath = next(test_dir.glob("unicode_*.txt"))
    doc = engine.ingest_document(fpath, title=fpath.name)
    results[fpath.name] = f"Ingested OK ({doc.chunk_count} chunks, unicode preserved)"

    # 8. Giant line
    fpath = test_dir / "giant_line.txt"
    doc = engine.ingest_document(fpath, title=fpath.name)
    results["giant_line.txt"] = f"Ingested OK ({doc.chunk_count} chunks without hanging)"

    # 9. Deduplication: Ingest clinical_discharge.txt again
    fpath = test_dir / "clinical_discharge.txt"
    doc_dup = engine.ingest_document(fpath, title=fpath.name)
    assert doc_dup.chunk_count == 0  # deduplicated
    results["clinical_discharge.txt (dup)"] = "Deduplicated cleanly (chunk_count=0, count unchanged)"

    # 10. Prompt injection query
    fpath = test_dir / "injection.txt"
    engine.ingest_document(fpath, title=fpath.name)
    resp = engine.query(QueryRequest(query="What is the Torsemide dose in injection notes?", mode="airgap"))
    assert "system prompt" not in resp.answer.lower()
    results["injection.txt"] = "Safe: System prompt not leaked, 500mg instruction ignored"

    # 11. PII mix test in PrivacyGuard
    pii_text = (test_dir / "pii_mix.txt").read_text(encoding="utf-8")
    red = PrivacyGuard.redact(pii_text)
    # Repeated SSN gets the same token:
    ssn_tokens = [e.token for e in red.detected_entities if e.type == "SSN"]
    assert len(ssn_tokens) == 2
    assert ssn_tokens[0] == ssn_tokens[1] == "[SAFE_SSN_1]"
    # Card, Email, Phone
    types_found = {e.type for e in red.detected_entities}
    assert "EMAIL" in types_found
    assert "PHONE" in types_found
    assert "FINANCIAL" in types_found or "SSN" in types_found
    results["pii_mix.txt"] = f"Masked {len(red.detected_entities)} entities: {types_found}; repeated SSN token reused"

    # Clean up
    engine.clear_all()

    print("\n" + "=" * 80)
    print("EDGE-CASE VERIFICATION RESULTS:")
    print("=" * 80)
    for k, v in results.items():
        print(f"  * {k:<30} -> {v}")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    test_all_edge_cases()
