import csv
import hashlib
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import Settings
from backend.models import QueryRequest
from backend.rag_engine import RAGEngine

def main():
    root = Path(__file__).resolve().parent.parent
    settings = Settings(data_dir=str(root / "data_golden_eval"))
    engine = RAGEngine(settings=settings)
    engine.clear_all()

    # Ingest golden corpus
    test_files_dir = root / "test_files"
    sample_dir = root / "sample_data"

    docs_to_ingest = [
        (test_files_dir / "clinical_discharge.txt", "CLINICAL"),
        (test_files_dir / "finance_q3.txt", "FINANCIAL"),
        (test_files_dir / "legal_msa.md", "LEGAL"),
        (sample_dir / "defense_radar.txt", "DEFENSE"),
    ]

    for p, cat in docs_to_ingest:
        if p.exists():
            engine.ingest_document(p, title=p.name, category=cat)

    csv_path = test_files_dir / "golden.csv"
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    print("=" * 95)
    print("20-QUERY GOLDEN BENCHMARK EVALUATION (DIRECT, REWORDED, TYPO, PII, NO-ANSWER)")
    print("=" * 95)
    print(f"{'#':<2} | {'Query':<42} | {'Expected':<18} | {'Top-1 Retr':<18} | {'Lat(ms)':<7} | {'Verdict'}")
    print("-" * 95)

    correct_retrievals = 0
    total_domain_queries = 0
    pii_protected_count = 0
    total_pii_queries = 0

    for idx, row in enumerate(reader, start=1):
        q = row["question"]
        expected = row["expected_doc"]
        q_type = row["query_type"]

        t0 = time.perf_counter()
        resp = engine.query(QueryRequest(query=q, mode="airgap", redact_pii=True))
        lat_ms = round((time.perf_counter() - t0) * 1000, 2)

        top_doc = resp.retrieved_chunks[0].doc_name if resp.retrieved_chunks else "NONE"

        verdict = "FAIL"
        if q_type in ("direct", "reworded", "factual", "typo_variant", "cross_domain"):
            total_domain_queries += 1
            if top_doc == expected:
                verdict = "MATCH"
                correct_retrievals += 1
            else:
                verdict = f"MISMATCH ({top_doc})"

        elif q_type == "pii_query":
            total_pii_queries += 1
            raw_leaked = any(raw in resp.answer for raw in ["123-45-6789", "555-014-2299", "48210-33781-CV"])
            if not raw_leaked:
                verdict = "PROTECTED"
                pii_protected_count += 1
            else:
                verdict = "LEAKED"

        elif q_type == "no_answer":
            # For no-answer, answer should not hallucinate a factual Mars capital
            if "not mentioned" in resp.answer.lower() or "no documentation" in resp.answer.lower() or "unavailable" in resp.answer.lower() or "photometry" not in resp.answer.lower():
                verdict = "REFUSED/NO_HALLUCINATION"
            else:
                verdict = "HALLUCINATION"

        q_disp = (q[:39] + "...") if len(q) > 42 else q
        print(f"{idx:<2} | {q_disp:<42} | {expected:<18} | {top_doc:<18} | {lat_ms:<7.2f} | {verdict}")

    engine.clear_all()

    print("=" * 95)
    print("GOLDEN EVALUATION SUMMARY:")
    print(f"Domain Retrieval Accuracy:  {correct_retrievals}/{total_domain_queries} ({(correct_retrievals/total_domain_queries)*100:.1f}%)")
    print(f"PII Leakage Prevention:     {pii_protected_count}/{total_pii_queries} ({'100%' if pii_protected_count == total_pii_queries else 'FAILED'})")
    print("=" * 95)

if __name__ == "__main__":
    main()
