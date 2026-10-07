from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

# Ensure project root in python path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from backend.config import Settings
from backend.models import QueryRequest
from backend.rag_engine import RAGEngine


BENCHMARK_QUERIES = [
    # Clinical queries (expected doc: clinical_ehr_cardiology.txt)
    ("What is the Torsemide dosage prescribed to the patient?", "clinical_ehr_cardiology.txt"),
    ("What was the patient's Left Ventricular Ejection Fraction LVEF?", "clinical_ehr_cardiology.txt"),
    ("What is the patient's NT-proBNP laboratory finding?", "clinical_ehr_cardiology.txt"),
    ("Which oral medication was switched from IV Lasix?", "clinical_ehr_cardiology.txt"),
    ("What is the discharge dosage for Sacubitril / Valsartan Entresto?", "clinical_ehr_cardiology.txt"),

    # Legal queries (expected doc: legal_msa.txt)
    ("What is the aggregate liability cap under Section 8?", "legal_msa.txt"),
    ("Which state substantive law governs this Agreement?", "legal_msa.txt"),
    ("What are the invoice payment terms and late interest penalty?", "legal_msa.txt"),
    ("What is the required monthly system availability SLA uptime percentage?", "legal_msa.txt"),
    ("How long does the non-disclosure period survive termination?", "legal_msa.txt"),

    # Defense queries (expected doc: defense_radar.txt)
    ("What are the operational frequency bands of the Spectre-9 AESA radar?", "defense_radar.txt"),
    ("How many Gallium Nitride GaN T/R modules are in the antenna aperture?", "defense_radar.txt"),
    ("What is the aggregate aperture radiated peak power in Kilowatts?", "defense_radar.txt"),
    ("What coolant is used for thermal dissipation in the radar subsystem?", "defense_radar.txt"),
    ("Under which US export control regulations is this document restricted?", "defense_radar.txt"),

    # Financial queries (expected doc: financial_audit_q3.txt)
    ("What is the Net Asset Value NAV of Apex Meridian Master Fund?", "financial_audit_q3.txt"),
    ("What is the gross leverage ratio of the portfolio?", "financial_audit_q3.txt"),
    ("What is the 99% 1-Day Value at Risk VaR reported?", "financial_audit_q3.txt"),
    ("What is the size of the Term Loan extended to BioSynthetix AG?", "financial_audit_q3.txt"),
    ("Which accounting firm served as lead external auditor?", "financial_audit_q3.txt"),
]


def get_git_commit() -> str:
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            return res.stdout.strip()[:8]
    except Exception:
        pass
    return "NOT MEASURED"


def compute_corpus_hash(sample_dir: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(sample_dir.glob("*.txt")):
        h.update(f.read_bytes())
    return h.hexdigest()[:16]


def percentile(data: list[float], pct: float) -> float:
    if not data:
        return 0.0
    sorted_d = sorted(data)
    idx = int(len(sorted_d) * pct)
    idx = min(idx, len(sorted_d) - 1)
    return sorted_d[idx]


def main():
    settings = Settings(data_dir=str(root_dir / "data_bench"))
    engine = RAGEngine(settings=settings)
    engine.clear_all()

    # Ingest sample corpus
    sample_dir = root_dir / "sample_data"
    for f in sorted(sample_dir.glob("*.txt")):
        cat = "CLINICAL" if "clinical" in f.name else "FINANCIAL" if "financial" in f.name else "LEGAL" if "legal" in f.name else "DEFENSE"
        engine.ingest_document(f, title=f.name, category=cat)

    corpus_hash = compute_corpus_hash(sample_dir)
    git_commit = get_git_commit()
    ts = datetime.now(timezone.utc).isoformat()
    ollama_online = engine.ollama_client.health_check(timeout_s=0.5)

    header_mode = "OLLAMA LIVE" if ollama_online else "OFFLINE FALLBACK"

    print("=" * 100)
    print(f"SOVEREIGN-RAG EMPIRICAL RETRIEVAL & GROUNDING BENCHMARK [{header_mode}]")
    print("=" * 100)
    print(f"Timestamp:        {ts}")
    print(f"Corpus Hash:      {corpus_hash}")
    print(f"Git Commit:       {git_commit}")
    print(f"Model:            {settings.ollama_model} ({'LIVE' if ollama_online else 'DETERMINISTIC FALLBACK'})")
    import argparse
    parser = argparse.ArgumentParser(description="Benchmark Sovereign RAG retrieval and grounding")
    parser.add_argument("--rounds", type=int, default=5, help="Number of benchmark passes (default: 5 passes = 100 queries)")
    args = parser.parse_args()

    queries = BENCHMARK_QUERIES * args.rounds

    print(f"Embedding Space:  {settings.airgap_embedding_model} ({settings.airgap_embedding_dim}-D)")
    print(f"Sample Size:      N={len(queries)} ({len(BENCHMARK_QUERIES)} distinct queries x {args.rounds} rounds)")
    print("-" * 100)
    print(f"{'ID':<3} | {'Query':<40} | {'Docs':<4} | {'Retr(ms)':<8} | {'Gen(ms)':<8} | {'E2E(ms)':<8} | {'Grd(h)':<6} | {'Unsupp':<6} | {'Claims (V/I/U)'}")
    print("-" * 100)

    retrieval_times = []
    e2e_times = []
    grounding_scores = []
    unsupported_rates = []
    correct_doc_matches = 0

    for idx, (query_text, expected_doc) in enumerate(queries, start=1):
        t0 = time.perf_counter()
        res = engine.query(QueryRequest(query=query_text, mode="airgap"))
        t_end = time.perf_counter()

        actual_e2e_ms = round((t_end - t0) * 1000, 2)
        retrieval_times.append(res.retrieval_latency_ms)
        e2e_times.append(actual_e2e_ms)
        grounding_scores.append(res.evaluation.grounding_confidence_heuristic)
        unsupported_rates.append(res.evaluation.unsupported_claim_rate_heuristic)

        # Check doc match accuracy
        if res.retrieved_chunks and expected_doc in res.retrieved_chunks[0].doc_name:
            correct_doc_matches += 1

        v_count = sum(1 for c in res.evaluation.claim_matrix if c.status == "VERIFIED")
        i_count = sum(1 for c in res.evaluation.claim_matrix if c.status == "INFERRED")
        u_count = sum(1 for c in res.evaluation.claim_matrix if c.status == "UNSUPPORTED")
        claims_str = f"{v_count}V / {i_count}I / {u_count}U"

        q_short = (query_text[:37] + "...") if len(query_text) > 40 else query_text
        print(
            f"{idx:<3} | {q_short:<40} | {len(res.retrieved_chunks):<4} | "
            f"{res.retrieval_latency_ms:<8.2f} | {res.generation_latency_ms:<8.2f} | {actual_e2e_ms:<8.2f} | "
            f"{res.evaluation.grounding_confidence_heuristic:<6.2f} | {res.evaluation.unsupported_claim_rate_heuristic:<6.2f} | {claims_str}"
        )

    # Clean up benchmark database
    engine.clear_all()

    print("=" * 100)
    print("AGGREGATE EMPIRICAL BENCHMARK METRICS (MEASURED VIA TIME.PERF_COUNTER):")
    print("-" * 100)
    print(f"Retrieval Latency (ms):  P50 = {percentile(retrieval_times, 0.50):.2f} ms | P95 = {percentile(retrieval_times, 0.95):.2f} ms | Mean = {statistics.mean(retrieval_times):.2f} ms")
    print(f"End-to-End Latency (ms): P50 = {percentile(e2e_times, 0.50):.2f} ms | P95 = {percentile(e2e_times, 0.95):.2f} ms | Mean = {statistics.mean(e2e_times):.2f} ms")
    print(f"Grounding Confidence:   Avg = {statistics.mean(grounding_scores):.3f} (heuristic)")
    print(f"Unsupported Claim Rate: Avg = {statistics.mean(unsupported_rates):.3f} (heuristic)")
    doc_accuracy = (correct_doc_matches / len(queries)) * 100.0
    print(f"Doc Match Accuracy:     {doc_accuracy:.1f}% ({correct_doc_matches}/{len(queries)} queries matched expected top-1 document)")
    print("=" * 100)


if __name__ == "__main__":
    main()
