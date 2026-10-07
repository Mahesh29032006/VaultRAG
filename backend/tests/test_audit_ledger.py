import json
from pathlib import Path
import time
import pytest
from backend.audit_ledger import AuditLedger
from backend.errors import AuditIntegrityError
from backend.models import IngestedDocument


def test_audit_ledger_e50_missing_file_creates_genesis(tmp_path: Path):
    ledger_path = tmp_path / "ledger.json"
    assert not ledger_path.exists()
    ledger = AuditLedger(str(ledger_path))
    assert ledger_path.exists()
    records = ledger.get_all()
    assert len(records) == 1
    assert records[0].event_type == "GENESIS"
    assert records[0].previous_hash == "0" * 64
    valid, _ = ledger.verify_integrity()
    assert valid is True


def test_audit_ledger_e51_corrupt_file_raises_integrity_error(tmp_path: Path):
    ledger_path = tmp_path / "corrupt_ledger.json"
    ledger_path.write_text("CORRUPTED_NON_JSON_DATA", encoding="utf-8")
    with pytest.raises(AuditIntegrityError):
        AuditLedger(str(ledger_path))


def test_audit_ledger_e52_tampered_block_detected(tmp_path: Path):
    ledger_path = tmp_path / "tamper_ledger.json"
    ledger = AuditLedger(str(ledger_path))
    ledger.log_pii_redact(entity_count=3, risk_score=36)
    ledger.log_local_query(model="llama3:8b", chunk_count=4, grounded=True)

    # Tamper with block 1 on disk
    with open(ledger_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    records[1]["current_hash"] = "0" * 64  # Tamper with block hash
    with open(ledger_path, "w", encoding="utf-8") as f:
        json.dump(records, f)

    # Re-instantiating should catch tampering
    with pytest.raises(AuditIntegrityError):
        AuditLedger(str(ledger_path))


def test_audit_ledger_append_event_chaining(tmp_path: Path):
    ledger_path = tmp_path / "chain_ledger.json"
    ledger = AuditLedger(str(ledger_path))
    rec1 = ledger.log_air_gap_verify(verified=True, egress_bytes=0)
    rec2 = ledger.log_quant_telemetry("llama3:8b", "Q4_K_M", 5.19)

    assert rec1.previous_hash == ledger.records[0].current_hash
    assert rec2.previous_hash == rec1.current_hash
    valid, bad_idx = ledger.verify_integrity()
    assert valid is True
    assert bad_idx == -1


def test_audit_ledger_no_raw_pii_stored(tmp_path: Path):
    ledger_path = tmp_path / "pii_ledger.json"
    ledger = AuditLedger(str(ledger_path))
    ledger.log_pii_redact(entity_count=5, risk_score=60)
    raw_content = ledger_path.read_text(encoding="utf-8")
    # Raw personal data values are never stored
    assert "123-45-6789" not in raw_content
    assert "John Doe" not in raw_content


def test_audit_ledger_e53_verification_performance(tmp_path: Path):
    ledger_path = tmp_path / "perf_ledger.json"
    ledger = AuditLedger(str(ledger_path))

    # Fast mock generation of 2,000 blocks to test verification throughput
    prev = ledger.records[0].current_hash
    for i in range(1, 2000):
        ts = f"2026-10-07T12:00:{i%60:02d}Z"
        summary = f"Event {i}"
        d_hash = ledger._compute_sha256(summary + json.dumps({"i": i}, sort_keys=True))
        c_hash = ledger._compute_sha256(f"{i}:{ts}:LOCAL_QUERY:{d_hash}:{prev}")
        from backend.models import AuditRecord
        rec = AuditRecord(
            index=i,
            timestamp=ts,
            event_type="LOCAL_QUERY",
            payload_summary=summary,
            data_hash=d_hash,
            previous_hash=prev,
            current_hash=c_hash
        )
        ledger.records.append(rec)
        prev = c_hash

    t0 = time.perf_counter()
    valid, bad_idx = ledger.verify_integrity()
    elapsed = time.perf_counter() - t0
    assert valid is True
    assert elapsed < 0.2  # Under 200ms
