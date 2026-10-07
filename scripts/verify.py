import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
import httpx


def main():
    root_dir = Path(__file__).resolve().parent.parent
    os.chdir(root_dir)

    # Ensure sample data exists
    sample_file = root_dir / "sample_data" / "clinical_ehr_cardiology.txt"
    if not sample_file.exists():
        print(f"FAIL: Sample file {sample_file} not found.")
        sys.exit(1)

    print("--- [1] Starting FastAPI Subprocess on 127.0.0.1:8093 ---")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8093"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    base_url = "http://127.0.0.1:8093"
    failures = []

    try:
        # Step 2: Wait <= 30s for /health == 200
        print("--- [2] Waiting for /health == 200 (max 30s) ---")
        healthy = False
        start_wait = time.time()
        with httpx.Client(timeout=2.0) as client:
            while time.time() - start_wait < 30:
                try:
                    res = client.get(f"{base_url}/health")
                    if res.status_code == 200:
                        healthy = True
                        break
                except Exception:
                    time.sleep(0.5)

        if not healthy:
            failures.append("Server did not become healthy within 30s")
            print("FAIL: Server health check timed out")
            return

        print("PASS: [2] Health check responded 200 OK")

        with httpx.Client(timeout=15.0) as client:
            # Ensure clean database before test
            client.delete(f"{base_url}/api/rag/documents")

            # Step 3: Assert mode == "airgap"
            res = client.get(f"{base_url}/health")
            data = res.json()
            if data.get("mode") == "airgap":
                print("PASS: [3] mode == 'airgap'")
            else:
                failures.append(f"Expected mode 'airgap', got {data.get('mode')}")
                print(f"FAIL: [3] mode == {data.get('mode')}")

            # Step 4 & 5: POST /api/rag/ingest sample_data/clinical_ehr_cardiology.txt
            with open(sample_file, "rb") as fp:
                res = client.post(
                    f"{base_url}/api/rag/ingest",
                    files={"file": (sample_file.name, fp, "text/plain")},
                    data={"title": "Clinical EHR Cardiology", "category": "CLINICAL"}
                )

            if res.status_code == 200:
                print("PASS: [4] POST /api/rag/ingest returned 200")
            else:
                failures.append(f"POST /api/rag/ingest returned status {res.status_code}: {res.text}")
                print(f"FAIL: [4] POST /api/rag/ingest returned {res.status_code}")

            ingest_data = res.json()
            chunk_cnt = ingest_data.get("chunk_count", 0)
            if chunk_cnt >= 1:
                print(f"PASS: [5] chunk_count >= 1 (got {chunk_cnt})")
            else:
                failures.append(f"Expected chunk_count >= 1, got {chunk_cnt}")
                print(f"FAIL: [5] chunk_count == {chunk_cnt}")

            # Step 6: GET /api/rag/documents -> assert 1 document
            res = client.get(f"{base_url}/api/rag/documents")
            docs = res.json().get("documents", [])
            if len(docs) == 1:
                print("PASS: [6] GET /api/rag/documents returned 1 document")
            else:
                failures.append(f"Expected 1 document, got {len(docs)}")
                print(f"FAIL: [6] Document count: {len(docs)}")

            # Step 7: POST /api/rag/ingest same file again -> deduplicated=True, chunk_count == 0
            with open(sample_file, "rb") as fp:
                res = client.post(
                    f"{base_url}/api/rag/ingest",
                    files={"file": (sample_file.name, fp, "text/plain")},
                    data={"title": "Clinical EHR Cardiology", "category": "CLINICAL"}
                )
            dup_data = res.json()
            if dup_data.get("deduplicated") is True and dup_data.get("chunk_count") == 0:
                print("PASS: [7] Ingest deduplicated=True and chunk_count == 0")
            else:
                failures.append(f"Expected deduplicated=True and chunk_count=0, got {dup_data}")
                print(f"FAIL: [7] Deduplication response: {dup_data}")

            # Step 8, 9, 10, 11, 12: POST /api/rag/query "What is the Torsemide dosage?"
            res = client.post(
                f"{base_url}/api/rag/query",
                json={"query": "What is the Torsemide dosage?", "mode": "airgap"}
            )
            if res.status_code == 200:
                print("PASS: [8] POST /api/rag/query returned 200")
            else:
                failures.append(f"Query returned status {res.status_code}: {res.text}")
                print(f"FAIL: [8] Query status {res.status_code}")

            q_data = res.json()
            answer = q_data.get("answer", "")
            evaluation = q_data.get("evaluation", {})

            # Step 9: Assert "20 mg" in answer
            if "20 mg" in answer or "20mg" in answer.lower():
                print("PASS: [9] '20 mg' found in answer")
            else:
                failures.append(f"'20 mg' not found in answer: {answer}")
                print(f"FAIL: [9] '20 mg' not in answer")

            # Step 10: Assert >= 1 citation matching [Doc:.+, Page \d+, Line \d+-\d+]
            citation_matches = re.findall(r"\[Doc:\s*[^,\]]+,\s*Page\s*\d+,\s*Line\s*\d+-\d+\]", answer)
            if len(citation_matches) >= 1:
                print(f"PASS: [10] Citations matched: {citation_matches}")
            else:
                failures.append("No valid citations found in answer")
                print("FAIL: [10] No citation matching pattern")

            # Step 11: Assert evaluation.grounding_confidence_heuristic >= 0.80
            grounding = evaluation.get("grounding_confidence_heuristic", 0.0)
            if grounding >= 0.80:
                print(f"PASS: [11] grounding_confidence_heuristic >= 0.80 ({grounding})")
            else:
                failures.append(f"grounding_confidence_heuristic < 0.80 ({grounding})")
                print(f"FAIL: [11] grounding_confidence_heuristic = {grounding}")

            # Step 12: Assert evaluation.unsupported_claim_rate_heuristic <= 0.20
            unsupported = evaluation.get("unsupported_claim_rate_heuristic", 1.0)
            if unsupported <= 0.20:
                print(f"PASS: [12] unsupported_claim_rate_heuristic <= 0.20 ({unsupported})")
            else:
                failures.append(f"unsupported_claim_rate_heuristic > 0.20 ({unsupported})")
                print(f"FAIL: [12] unsupported_claim_rate_heuristic = {unsupported}")

            # Step 13, 14, 15: POST /api/privacy/redact with SSN + MRN + phone
            sample_phi = "Patient MRN: 9482-10492-CV, SSN 382-49-1092, Phone (415) 892-4410."
            res = client.post(f"{base_url}/api/privacy/redact", json={"text": sample_phi})
            red_res = res.json()
            entities = red_res.get("detected_entities", [])
            t_map = red_res.get("token_map", {})

            if len(entities) >= 3:
                print(f"PASS: [13] Detected entities >= 3 ({len(entities)})")
            else:
                failures.append(f"Expected >= 3 entities, got {len(entities)}")
                print(f"FAIL: [13] Entities: {len(entities)}")

            if len(t_map) >= 3:
                print(f"PASS: [14] token_map has all three items: {list(t_map.keys())}")
            else:
                failures.append(f"token_map does not contain all items: {t_map}")
                print(f"FAIL: [14] token_map size: {len(t_map)}")

            # Step 15: POST /api/privacy/restore -> assert exact original
            res = client.post(
                f"{base_url}/api/privacy/restore",
                json={"redacted_text": red_res.get("redacted_text", ""), "token_map": t_map}
            )
            restored = res.json().get("restored_text", "")
            if restored == sample_phi:
                print("PASS: [15] Restored text exactly matches original")
            else:
                failures.append(f"Restored text mismatch: {restored} != {sample_phi}")
                print("FAIL: [15] Restoration mismatch")

            # Step 16 & 17: GET /api/audit/logs -> integrity.valid == True
            res = client.get(f"{base_url}/api/audit/logs")
            audit_res = res.json()
            if audit_res.get("integrity", {}).get("valid") is True:
                print("PASS: [16] Audit ledger integrity valid == True")
            else:
                failures.append("Audit ledger integrity is invalid")
                print("FAIL: [16] Audit integrity not valid")

            events = [r.get("event_type") for r in audit_res.get("ledger", [])]
            required_events = {"DOCUMENT_INGEST", "PII_REDACT", "LOCAL_QUERY"}
            if required_events.issubset(set(events)):
                print(f"PASS: [17] Event types present: {required_events}")
            else:
                failures.append(f"Missing required audit events: {required_events - set(events)}")
                print(f"FAIL: [17] Missing events from ledger")

            # Step 18: GET /api/telemetry/memory?model_id=llama3:8b&quant_type=Q4_K_M&context_length=4096
            res = client.get(f"{base_url}/api/telemetry/memory?model_id=llama3:8b&quant_type=Q4_K_M&context_length=4096")
            mem_data = res.json()
            tot_gib = mem_data.get("total_memory_gib_estimate", 0.0)
            if 4.5 <= tot_gib <= 6.5:
                print(f"PASS: [18] total_memory_gib_estimate between 4.5 and 6.5 ({tot_gib} GiB)")
            else:
                failures.append(f"total_memory_gib_estimate out of bounds: {tot_gib}")
                print(f"FAIL: [18] total_memory_gib_estimate = {tot_gib}")

            # Step 19: Assert response header "X-Air-Gap-Status" == "ENFORCED"
            air_gap_header = res.headers.get("x-air-gap-status")
            if air_gap_header == "ENFORCED":
                print("PASS: [19] X-Air-Gap-Status == 'ENFORCED'")
            else:
                failures.append(f"Header X-Air-Gap-Status != 'ENFORCED', got '{air_gap_header}'")
                print(f"FAIL: [19] Header = {air_gap_header}")

            # Step 20: GET /health -> assert index_healthy, manifest_healthy, audit_healthy all True
            res = client.get(f"{base_url}/health")
            h_data = res.json()
            if (
                h_data.get("index_healthy") is True and
                h_data.get("manifest_healthy") is True and
                h_data.get("audit_healthy") is True
            ):
                print("PASS: [20] index_healthy, manifest_healthy, audit_healthy all True")
            else:
                failures.append(f"Health checks failed: {h_data}")
                print(f"FAIL: [20] Health checks: {h_data}")

    finally:
        # Step 21: Kill server
        print("--- [21] Terminating server process ---")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()

    # Step 22: Summary report
    print("\n================ VERIFICATION SUMMARY ================")
    if not failures:
        print("ALL CHECKS PASSED")
        sys.exit(0)
    else:
        print(f"VERIFICATION FAILED: {len(failures)} failures encountered:")
        for f in failures:
            print(f" - {f}")
        sys.exit(1)


if __name__ == "__main__":
    main()
