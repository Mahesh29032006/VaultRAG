from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Literal
from backend.errors import AuditIntegrityError
from backend.models import AuditRecord, IngestedDocument
from backend.storage import atomic_write_json, read_json

logger = logging.getLogger(__name__)


class AuditLedger:
    def __init__(self, path: str):
        self.path = Path(path)
        self.records: list[AuditRecord] = []
        self._load_or_init()

    def _compute_sha256(self, payload: str) -> str:
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _load_or_init(self) -> None:
        if not self.path.exists():
            # Create Genesis block
            ts = datetime.now(timezone.utc).isoformat()
            summary = "Genesis Block - SovereignRAG Tamper-Evident Ledger Initialized"
            data = {"version": "1.0", "air_gap_policy": "ENFORCED"}
            d_hash = self._compute_sha256(summary + json.dumps(data, sort_keys=True))
            prev_hash = "0" * 64
            c_hash = self._compute_sha256(f"0:{ts}:GENESIS:{d_hash}:{prev_hash}")

            genesis = AuditRecord(
                index=0,
                timestamp=ts,
                event_type="GENESIS",
                payload_summary=summary,
                data_hash=d_hash,
                previous_hash=prev_hash,
                current_hash=c_hash
            )
            self.records = [genesis]
            self._save()
            return

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception as e:
            raise AuditIntegrityError(f"Corrupt audit ledger file: {e}") from e

        if not isinstance(raw_data, list) or len(raw_data) == 0:
            raise AuditIntegrityError("Corrupt audit ledger: empty or non-list format")

        parsed_records: list[AuditRecord] = []
        for i, item in enumerate(raw_data):
            try:
                rec = AuditRecord(**item)
                parsed_records.append(rec)
            except Exception as e:
                raise AuditIntegrityError(f"Corrupt audit record at index {i}: {e}") from e

        self.records = parsed_records
        valid, bad_idx = self.verify_integrity()
        if not valid:
            raise AuditIntegrityError(f"Audit ledger integrity failure at block index {bad_idx}")

    def _save(self) -> None:
        serializable = [r.model_dump() for r in self.records]
        atomic_write_json(str(self.path), serializable)

    def _append(self, event_type: str, summary: str, data: dict) -> AuditRecord:
        idx = len(self.records)
        ts = datetime.now(timezone.utc).isoformat()
        prev_hash = self.records[-1].current_hash if self.records else "0" * 64

        d_hash = self._compute_sha256(summary + json.dumps(data, sort_keys=True))
        c_hash = self._compute_sha256(f"{idx}:{ts}:{event_type}:{d_hash}:{prev_hash}")

        record = AuditRecord(
            index=idx,
            timestamp=ts,
            event_type=event_type,  # type: ignore
            payload_summary=summary,
            data_hash=d_hash,
            previous_hash=prev_hash,
            current_hash=c_hash
        )
        self.records.append(record)
        self._save()
        return record

    def log_document_ingest(self, doc: IngestedDocument) -> AuditRecord:
        summary = f"Document Ingested: {doc.title} ({doc.chunk_count} chunks)"
        data = {
            "doc_id": doc.id,
            "category": doc.category,
            "sha256": doc.sha256,
            "chunks": doc.chunk_count
        }
        return self._append("DOCUMENT_INGEST", summary, data)

    def log_pii_redact(self, entity_count: int, risk_score: int) -> AuditRecord:
        summary = f"PII Redaction: {entity_count} entities sanitized (risk score: {risk_score})"
        data = {"entities_redacted": entity_count, "risk_score_heuristic": risk_score}
        return self._append("PII_REDACT", summary, data)

    def log_local_query(self, model: str, chunk_count: int, grounded: bool) -> AuditRecord:
        summary = f"Query executed via {model} (retrieved {chunk_count} chunks, grounded: {grounded})"
        data = {"model": model, "chunks_retrieved": chunk_count, "grounded": grounded}
        return self._append("LOCAL_QUERY", summary, data)

    def log_air_gap_verify(self, verified: bool, egress_bytes: int) -> AuditRecord:
        summary = f"Air Gap Verification: loopback={verified}, observed non-loopback egress bytes={egress_bytes}"
        data = {"loopback_verified": verified, "egress_bytes": egress_bytes}
        return self._append("AIR_GAP_VERIFY", summary, data)

    def log_quant_telemetry(self, model_id: str, quant_type: str, vram_gib: float) -> AuditRecord:
        summary = f"Quantization Telemetry: {model_id} ({quant_type}) memory estimate {vram_gib} GiB"
        data = {"model": model_id, "quant": quant_type, "vram_estimate_gib": vram_gib}
        return self._append("QUANT_TELEMETRY", summary, data)

    def log_error(self, error_class: str, message: str) -> AuditRecord:
        summary = f"Error: [{error_class}] {message[:120]}"
        data = {"error_class": error_class, "message": message}
        return self._append("ERROR", summary, data)

    def get_all(self) -> list[AuditRecord]:
        return list(self.records)

    def verify_integrity(self) -> tuple[bool, int]:
        """Validates the cryptographic chain of hashes across all blocks."""
        if not self.records:
            return True, -1

        for i, rec in enumerate(self.records):
            # Check previous hash linkage
            if i == 0:
                if rec.previous_hash != "0" * 64:
                    return False, 0
            else:
                if rec.previous_hash != self.records[i - 1].current_hash:
                    return False, i

            # Verify current hash recomputation
            expected_c_hash = self._compute_sha256(
                f"{rec.index}:{rec.timestamp}:{rec.event_type}:{rec.data_hash}:{rec.previous_hash}"
            )
            if rec.current_hash != expected_c_hash:
                return False, i

        return True, -1
