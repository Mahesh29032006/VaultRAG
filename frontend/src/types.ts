export type EntityType =
  | 'NAME'
  | 'SSN'
  | 'MRN'
  | 'PHONE'
  | 'FAX'
  | 'EMAIL'
  | 'DATE'
  | 'ADDRESS'
  | 'FINANCIAL'
  | 'PROVIDER_ID'
  | 'HEALTH_PLAN_ID'
  | 'ACCOUNT'
  | 'LICENSE'
  | 'VEHICLE_ID'
  | 'DEVICE_ID'
  | 'URL'
  | 'IP_ADDRESS'
  | 'BIOMETRIC_REF';

export interface DetectedEntity {
  id: string;
  type: EntityType;
  raw: string;
  token: string;
  start_index: int_number;
  end_index: int_number;
  confidence: number;
}

export type int_number = number;

export interface RedactionResult {
  original_text: string;
  redacted_text: string;
  detected_entities: DetectedEntity[];
  token_map: Record<string, string>;
  reverse_token_map: Record<string, string>;
  risk_score_heuristic: number;
  safe_harbor_oriented: boolean;
}

export type DocumentCategory = 'CLINICAL' | 'FINANCIAL' | 'LEGAL' | 'DEFENSE' | 'GENERAL';

export interface DocumentChunk {
  id: string;
  doc_id: string;
  doc_name: string;
  category: DocumentCategory;
  content: string;
  chunk_index: number;
  word_count: number;
  page_number: number;
  start_line: number;
  end_line: number;
  sha256: string;
}

export interface IngestedDocument {
  id: string;
  title: string;
  category: DocumentCategory;
  sha256: string;
  chunk_count: number;
  ingested_at: string;
  source_filename: string;
}

export interface RetrievedChunk {
  chunk_id: string;
  doc_name: string;
  category: string;
  page_number: number;
  start_line: number;
  end_line: number;
  text: string;
  similarity_score: number;
  bm25_score: number;
  rrf_score: number;
  citation_label: string;
}

export type ClaimStatus = 'VERIFIED' | 'INFERRED' | 'UNSUPPORTED';

export interface ClaimVerification {
  claim_text: string;
  status: ClaimStatus;
  verifying_doc: string | null;
  verifying_lines: string | null;
  confidence_heuristic: number;
  evidence_snippet: string | null;
}

export interface EvaluationReport {
  is_grounded: boolean;
  unsupported_claim_rate_heuristic: number;
  grounding_confidence_heuristic: number;
  total_citations_found: number;
  citations_verified: number;
  total_quotes_found: number;
  verbatim_quotes_matched: number;
  unsupported_claims_flagged: number;
  verdict: string;
  audit_notes: string[];
  claim_matrix: ClaimVerification[];
}

export interface QueryRequest {
  query: string;
  top_k?: number;
  mode?: 'airgap' | 'cloud';
  redact_pii?: boolean;
  use_rag?: boolean;
}

export interface QueryResponse {
  query: string;
  answer: string;
  retrieved_chunks: RetrievedChunk[];
  evaluation: EvaluationReport;
  redaction: RedactionResult | null;
  latency_ms: number;
  retrieval_latency_ms: number;
  generation_latency_ms: number;
  mode: string;
  model_name: string;
  air_gapped: boolean;
  offline_fallback: boolean;
}

export type AuditEventType =
  | 'GENESIS'
  | 'DOCUMENT_INGEST'
  | 'PII_REDACT'
  | 'LOCAL_QUERY'
  | 'AIR_GAP_VERIFY'
  | 'QUANT_TELEMETRY'
  | 'MODE_SWITCH'
  | 'ERROR'
  | 'SYSTEM_SHUTDOWN';

export interface AuditRecord {
  index: number;
  timestamp: string;
  event_type: AuditEventType;
  payload_summary: string;
  data_hash: string;
  previous_hash: string;
  current_hash: string;
}

export interface MemoryCalculation {
  model_id: string;
  quant_type: string;
  context_length: number;
  batch_size: number;
  weight_memory_gib: number;
  kv_cache_memory_gib: number;
  activation_memory_gib_estimate: number;
  total_memory_gib_estimate: number;
  fits_on_16gib: boolean;
  fits_on_8gib: boolean;
  recommended_hardware: string;
  notes: string;
}

export interface HealthResponse {
  status: string;
  mode?: string;
  engine_mode?: string;
  documents?: number;
  total_documents?: number;
  chunks?: number;
  total_chunks?: number;
  index_healthy?: boolean;
  manifest_healthy?: boolean;
  audit_healthy?: boolean;
  audit_ledger_valid?: boolean;
  ollama?: {
    available: boolean;
    model?: string;
  };
  gemini?: {
    available: boolean;
  };
  air_gap?: {
    policy: string;
    verification: string;
  };
  csp_header_enforced?: boolean;
}

export interface HostTelemetry {
  platform: string;
  arch?: string;
  cpu_count?: number;
  cpu_model?: string;
  cpu_percent?: number;
  total_memory_gib?: number;
  free_memory_gib?: number;
  used_memory_gib?: number;
  memory_usage_percent?: number;
  memory_total_gib?: number;
  memory_available_gib?: number;
  memory_used_gib?: number;
  memory_percent?: number;
  disk_total_gib?: number;
  disk_used_gib?: number;
  disk_free_gib?: number;
  disk_percent?: number;
}

export interface ModelOption {
  id: string;
  name: string;
  base_params_billions: number;
  quant_options: string[];
  default_context: number;
  max_context: number;
}

export interface ConfigSettings {
  gemini_api_key_masked: string;
  gemini_api_key_configured: boolean;
  gemini_model: string;
  ollama_url: string;
  ollama_model: string;
  engine_mode: 'airgap' | 'cloud';
  top_k?: number;
  chunk_size?: number;
  chunk_overlap?: number;
}

