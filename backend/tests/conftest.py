from pathlib import Path
import pytest
from backend.audit_ledger import AuditLedger
from backend.config import Settings
from backend.rag_engine import RAGEngine


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    # Minimal valid single-page PDF containing text
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length 53 >>\nstream\n"
        b"BT /F1 12 Tf 72 712 Td (Minimal Valid PDF Document Content) Tj ET\n"
        b"endstream\nendobj\n"
        b"xref\n0 5\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000302 00000 n \n"
        b"trailer\n<< /Size 5 /Root 1 0 R >>\n"
        b"startxref\n406\n%%EOF\n"
    )


@pytest.fixture
def sample_text_bytes() -> bytes:
    return b"This is a sample document for testing text ingestion in SovereignRAG."


@pytest.fixture
def tmp_settings(tmp_path: Path) -> Settings:
    d = tmp_path / "data"
    d.mkdir(parents=True, exist_ok=True)
    return Settings(
        data_dir=str(d),
        faiss_index_path=str(d / "faiss.index"),
        chunks_path=str(d / "chunks.pkl"),
        manifest_path=str(d / "manifest.json"),
        chroma_dir=str(d / "chromadb"),
        audit_ledger_path=str(d / "audit_ledger.json"),
        uploads_dir=str(d / "uploads"),
        config_path=str(d / "config.json"),
        engine_mode="airgap",
        top_k=4,
        chunk_size=450,
        chunk_overlap=60
    )


@pytest.fixture
def empty_engine(tmp_settings: Settings) -> RAGEngine:
    ledger = AuditLedger(tmp_settings.audit_ledger_path)
    return RAGEngine(settings=tmp_settings, audit_ledger=ledger)


@pytest.fixture
def seeded_engine(empty_engine: RAGEngine, tmp_path: Path) -> RAGEngine:
    docs_dir = tmp_path / "seed_docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    f1 = docs_dir / "clinical_summary.txt"
    f1.write_text(
        "Patient John Doe was diagnosed with acute decompensated heart failure. "
        "The attending physician prescribed Torsemide 20 mg oral daily for fluid retention. "
        "Blood pressure was recorded as 130/80 mmHg.",
        encoding="utf-8"
    )

    f2 = docs_dir / "master_services_agreement.txt"
    f2.write_text(
        "This Master Services Agreement is entered into under the governing law of the State of Delaware. "
        "Aggregate liability under Section 8 shall not exceed $2,000,000 for all claims. "
        "Payment terms are net 30 days from invoice date.",
        encoding="utf-8"
    )

    f3 = docs_dir / "zero_trust_architecture.txt"
    f3.write_text(
        "The zero-trust enterprise infrastructure implements mutual TLS for service-to-service communication. "
        "Cryptographic identity is provided via SPIFFE and SPIRE attestations. "
        "All network egress is blocked by default at the eBPF layer.",
        encoding="utf-8"
    )

    empty_engine.ingest_document(f1, title="Clinical Cardiology Summary", category="CLINICAL")
    empty_engine.ingest_document(f2, title="Master Services Agreement", category="LEGAL")
    empty_engine.ingest_document(f3, title="Zero Trust Architecture", category="GENERAL")

    return empty_engine


@pytest.fixture
def fake_ollama_responses() -> list[str]:
    return [
        "Based on verified local documentation [Doc: clinical_summary.txt, Page 1, Line 1-3]:\n"
        "Patient was prescribed Torsemide 20 mg oral daily."
    ]


@pytest.fixture(autouse=True)
def reset_main_settings(tmp_path: Path):
    import backend.main as main_mod
    test_cfg = tmp_path / "test_config.json"
    main_mod.settings.config_path = str(test_cfg)
    main_mod.settings.gemini_api_key = ""
    main_mod.settings.engine_mode = "airgap"
    yield
    main_mod.settings.gemini_api_key = ""
    main_mod.settings.engine_mode = "airgap"

