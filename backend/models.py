from typing import Literal
from pydantic import BaseModel, Field


class DetectedEntity(BaseModel):
    id: str
    type: Literal[
        "NAME", "SSN", "MRN", "PHONE", "FAX", "EMAIL", "DATE", "ADDRESS",
        "FINANCIAL", "PROVIDER_ID", "HEALTH_PLAN_ID", "ACCOUNT",
        "LICENSE", "VEHICLE_ID", "DEVICE_ID", "URL", "IP_ADDRESS",
        "BIOMETRIC_REF"
    ]
    raw: str
    token: str
    start_index: int
    end_index: int
    confidence: float


class RedactionResult(BaseModel):
    original_text: str
    redacted_text: str
    detected_entities: list[DetectedEntity]
    token_map: dict[str, str]
    reverse_token_map: dict[str, str]
    risk_score_heuristic: int
    safe_harbor_oriented: bool


class DocumentChunk(BaseModel):
    id: str
    doc_id: str
    doc_name: str
    category: Literal["CLINICAL", "FINANCIAL", "LEGAL", "DEFENSE", "GENERAL"]
    content: str
    chunk_index: int
    word_count: int
    page_number: int
    start_line: int
    end_line: int
    sha256: str


class IngestedDocument(BaseModel):
    id: str
    title: str
    category: Literal["CLINICAL", "FINANCIAL", "LEGAL", "DEFENSE", "GENERAL"]
    sha256: str
    chunk_count: int
    ingested_at: str
    source_filename: str


class RetrievedChunk(BaseModel):
    chunk_id: str
    doc_name: str
    category: str
    page_number: int
    start_line: int
    end_line: int
    text: str
    similarity_score: float
    bm25_score: float
    rrf_score: float
    citation_label: str


class ClaimVerification(BaseModel):
    claim_text: str
    status: Literal["VERIFIED", "INFERRED", "UNSUPPORTED"]
    verifying_doc: str | None
    verifying_lines: str | None
    confidence_heuristic: float
    evidence_snippet: str | None


class EvaluationReport(BaseModel):
    is_grounded: bool
    unsupported_claim_rate_heuristic: float
    grounding_confidence_heuristic: float
    total_citations_found: int
    citations_verified: int
    total_quotes_found: int
    verbatim_quotes_matched: int
    unsupported_claims_flagged: int
    verdict: str
    audit_notes: list[str]
    claim_matrix: list[ClaimVerification]


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=4, ge=1, le=20)
    mode: Literal["airgap", "cloud"] = "airgap"
    redact_pii: bool = True
    use_rag: bool = True


class QueryResponse(BaseModel):
    query: str
    answer: str
    retrieved_chunks: list[RetrievedChunk]
    evaluation: EvaluationReport
    redaction: RedactionResult | None
    latency_ms: float
    retrieval_latency_ms: float
    generation_latency_ms: float
    mode: str
    model_name: str
    air_gapped: bool
    offline_fallback: bool


class AuditRecord(BaseModel):
    index: int
    timestamp: str
    event_type: Literal[
        "GENESIS", "DOCUMENT_INGEST", "PII_REDACT", "LOCAL_QUERY",
        "AIR_GAP_VERIFY", "QUANT_TELEMETRY", "MODE_SWITCH",
        "ERROR", "SYSTEM_SHUTDOWN"
    ]
    payload_summary: str
    data_hash: str
    previous_hash: str
    current_hash: str


class MemoryCalculation(BaseModel):
    model_id: str
    quant_type: str
    context_length: int
    batch_size: int
    weight_memory_gib: float
    kv_cache_memory_gib: float
    activation_memory_gib_estimate: float
    total_memory_gib_estimate: float
    fits_on_16gib: bool
    fits_on_8gib: bool
    recommended_hardware: str
    notes: str = "Values are estimates. Actual usage depends on runtime and hardware."
