from pathlib import Path
import pytest
from backend.errors import SensitiveDataCloudBlockedError
from backend.models import QueryRequest
from backend.rag_engine import RAGEngine


def test_end_to_end_ingest_three_docs_query_citation_present(seeded_engine: RAGEngine):
    req = QueryRequest(query="What is the Torsemide dosage?", mode="airgap")
    res = seeded_engine.query(req)
    assert res.retrieved_chunks is not None
    assert len(res.retrieved_chunks) > 0
    assert "20 mg" in res.answer or "Torsemide" in res.answer
    assert "[Doc:" in res.answer
    assert res.evaluation.grounding_confidence_heuristic > 0.0


def test_end_to_end_ingest_doc_with_ssn_redacts_in_context(empty_engine: RAGEngine, tmp_path: Path):
    doc_path = tmp_path / "ehr_patient.txt"
    doc_path.write_text("Patient SSN 123-45-6789 was prescribed Lisinopril 10 mg.", encoding="utf-8")
    empty_engine.ingest_document(doc_path, title="Patient Record", category="CLINICAL")

    # Ingested chunks should have [SAFE_SSN_1] instead of raw SSN
    for chunk in empty_engine.chunks.values():
        assert "123-45-6789" not in chunk.content
        assert "[SAFE_SSN_1]" in chunk.content


def test_end_to_end_delete_document_clears_results(empty_engine: RAGEngine, tmp_path: Path):
    doc_path = tmp_path / "temporary.txt"
    doc_path.write_text("Unique specific keyword ABCXYZ123 for deletion testing.", encoding="utf-8")
    doc = empty_engine.ingest_document(doc_path, title="Temporary", category="GENERAL")

    # Query finds it
    res1 = empty_engine.query(QueryRequest(query="ABCXYZ123"))
    assert len(res1.retrieved_chunks) >= 1

    # Delete doc
    empty_engine.delete_document(doc.id)

    # Query now returns no documents
    res2 = empty_engine.query(QueryRequest(query="ABCXYZ123"))
    assert len(res2.retrieved_chunks) == 0
    assert "No relevant documents" in res2.answer


def test_end_to_end_audit_ledger_records_ingest_and_query(empty_engine: RAGEngine, tmp_path: Path):
    doc_path = tmp_path / "audit_test.txt"
    doc_path.write_text("Audit test documentation content line.", encoding="utf-8")
    empty_engine.ingest_document(doc_path, title="Audit Doc", category="GENERAL")

    empty_engine.query(QueryRequest(query="documentation content"))

    events = [r.event_type for r in empty_engine.audit_ledger.get_all()]
    assert "DOCUMENT_INGEST" in events
    assert "LOCAL_QUERY" in events


def test_end_to_end_cloud_mode_blocks_sensitive_document(seeded_engine: RAGEngine):
    # Seeded engine has a CLINICAL document with Torsemide
    seeded_engine.settings.gemini_api_key = "fake_key_for_test"
    req = QueryRequest(query="What is the Torsemide dosage?", mode="cloud")
    with pytest.raises(SensitiveDataCloudBlockedError):
        seeded_engine.query(req)


def test_end_to_end_ollama_offline_uses_fallback_path(seeded_engine: RAGEngine):
    # Ensure Ollama client points to offline port
    seeded_engine.ollama_client.base_url = "http://127.0.0.1:59999"
    res = seeded_engine.query(QueryRequest(query="What is the liability cap under Delaware law?"))
    assert res.offline_fallback is True
    assert "$2,000,000" in res.answer
    assert "Note: Local LLM unavailable" in res.answer


def test_api_routes_lifecycle_and_telemetry(tmp_path: Path):
    from fastapi.testclient import TestClient
    from backend.main import app

    import uuid
    with TestClient(app) as client:
        # Health check
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["air_gap"]["policy"] == "ENFORCED"

        # Stats and Mode
        res = client.get("/api/stats")
        assert res.status_code == 200
        res = client.get("/api/mode")
        assert res.json()["mode"] in {"airgap", "cloud"}

        # Mode switch without key returns 400
        res = client.post("/api/mode", json={"mode": "cloud"})
        assert res.status_code == 400
        res = client.post("/api/mode", json={"mode": "invalid"})
        assert res.status_code == 400

        # Privacy routes
        res = client.post("/api/privacy/redact", json={"text": "Contact Dr. Robert Smith at 555-123-4567."})
        assert res.status_code == 200
        red_data = res.json()
        assert "[SAFE_PHONE_1]" in red_data["redacted_text"]

        res = client.post("/api/privacy/restore", json={
            "redacted_text": red_data["redacted_text"],
            "token_map": red_data["token_map"]
        })
        assert res.status_code == 200
        assert "555-123-4567" in res.json()["restored_text"]

        # Ingest file via API
        f = tmp_path / "api_doc.txt"
        f.write_text(f"API document test content {uuid.uuid4()} line for ingestion test.", encoding="utf-8")
        with open(f, "rb") as fp:
            res = client.post("/api/rag/ingest", files={"file": ("api_doc.txt", fp, "text/plain")}, data={"title": "API Doc"})
        assert res.status_code == 200
        assert res.json()["chunk_count"] >= 1

        # Ingest same file again -> deduplicated
        with open(f, "rb") as fp:
            res = client.post("/api/rag/ingest", files={"file": ("api_doc.txt", fp, "text/plain")}, data={"title": "API Doc"})
        assert res.status_code == 200
        assert res.json()["deduplicated"] is True
        assert res.json()["chunk_count"] == 0

        # Query via API
        res = client.post("/api/rag/query", json={"query": "ingestion test", "mode": "airgap"})
        assert res.status_code == 200
        assert "ingestion test" in res.json()["query"]

        # Chat SSE stream
        res = client.post("/api/chat", json={"query": "ingestion test", "mode": "airgap"})
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]
        assert "metadata" in res.text
        assert "complete" in res.text

        # List documents
        res = client.get("/api/rag/documents")
        assert res.status_code == 200
        assert len(res.json()["documents"]) >= 1
        doc_id = res.json()["documents"][0]["id"]

        # Audit logs and verify
        res = client.get("/api/audit/logs")
        assert res.status_code == 200
        assert len(res.json()["ledger"]) > 0

        res = client.post("/api/audit/verify")
        assert res.status_code == 200
        assert res.json()["valid"] is True

        # Telemetry routes
        res = client.get("/api/telemetry/memory?model_id=llama3:8b&quant_type=Q4_K_M&context_length=4096")
        assert res.status_code == 200
        assert 4.5 <= res.json()["total_memory_gib_estimate"] <= 6.5

        res = client.get("/api/telemetry/host")
        assert res.status_code == 200
        assert "platform" in res.json()

        res = client.get("/api/telemetry/models")
        assert res.status_code == 200
        assert "llama3:8b" in res.json()["models"]

        # Delete single document
        res = client.delete(f"/api/rag/documents/{doc_id}")
        assert res.status_code == 200

        # Clear all documents
        res = client.delete("/api/rag/documents")
        assert res.status_code == 200
        assert res.json()["cleared"] is True

def test_storage_atomic_and_safe_readers(tmp_path: Path):
    from backend.storage import (
        atomic_write_bytes,
        atomic_write_json,
        atomic_write_pickle,
        read_json,
        read_pickle,
        ensure_dirs,
    )

    d = tmp_path / "nested" / "dir"
    ensure_dirs([str(d)])
    assert d.exists()

    b_file = d / "data.bin"
    atomic_write_bytes(str(b_file), b"binary_data_content")
    assert b_file.read_bytes() == b"binary_data_content"

    j_file = d / "data.json"
    atomic_write_json(str(j_file), {"key": "val"})
    assert read_json(str(j_file)) == {"key": "val"}
    assert read_json(str(d / "missing.json"), default="def") == "def"

    p_file = d / "data.pkl"
    atomic_write_pickle(str(p_file), {"p_key": 123})
    assert read_pickle(str(p_file)) == {"p_key": 123}
    assert read_pickle(str(d / "missing.pkl"), default=None) is None


def test_settings_config_and_mode_switch_endpoints(tmp_path: Path):
    from fastapi.testclient import TestClient
    from backend.main import app, settings
    import backend.main as main_mod

    settings.gemini_api_key = ""
    settings.engine_mode = "airgap"

    with TestClient(app) as client:
        # 1. Switch to cloud mode without key should fail with 400
        res = client.post("/api/mode", json={"mode": "cloud"})
        assert res.status_code == 400
        assert "Gemini API key is not configured" in res.json()["detail"]

        # 2. Switch to cloud mode passing key should succeed
        res = client.post("/api/mode", json={"mode": "cloud", "gemini_api_key": "AIzaSyFakeKey123456789"})
        assert res.status_code == 200
        assert res.json()["mode"] == "cloud"
        assert settings.engine_mode == "cloud"
        assert settings.gemini_api_key == "AIzaSyFakeKey123456789"

        # 3. GET /api/settings/config should return masked key
        res = client.get("/api/settings/config")
        assert res.status_code == 200
        data = res.json()
        assert data["gemini_api_key_configured"] is True
        assert data["gemini_api_key_masked"] == "AIza...6789"
        assert data["engine_mode"] == "cloud"

        # 4. POST /api/settings/config should update settings
        res = client.post("/api/settings/config", json={"gemini_model": "gemini-1.5-pro"})
        assert res.status_code == 200
        assert res.json()["gemini_model"] == "gemini-1.5-pro"
        assert settings.gemini_model == "gemini-1.5-pro"

        # Switch back to airgap
        res = client.post("/api/mode", json={"mode": "airgap"})
        assert res.status_code == 200
        assert res.json()["mode"] == "airgap"


