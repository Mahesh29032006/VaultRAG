# SovereignRAG — Air-Gapped Private RAG Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178c6.svg)](https://www.typescriptlang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**SovereignRAG** is a unified, self-contained, enterprise-grade Retrieval-Augmented Generation (RAG) platform architected for strictly air-gapped environments. Merged from the high-precision hybrid retrieval core of **NexusRAG v2.0** and the confidential privacy, audit, and quantization telemetry infrastructure of **SovereignAI**, SovereignRAG allows organizations to query sensitive clinical, legal, financial, and defense documents with zero non-loopback egress during local operations.

---

## Key Highlights & Core Capabilities

1. **Air-Gapped Hybrid Retrieval Engine (NexusRAG Core)**
   - **DualIndex Vector Math**: Offline 384-dimensional dense embeddings (`all-MiniLM-L6-v2` via FAISS / pure-Python cosine vector math fallback) and optional 768-D cloud ChromaDB index.
   - **BM25 Lexical Ranking**: Pure-Python implementation from scratch featuring IDF smoothing, query stopword pruning, and length normalization ($k_1=1.5, b=0.75$).
   - **Reciprocal Rank Fusion (RRF)**: Rank-based fusion ($k=60$) combining dense semantic vectors and lexical sparse tokens into an unified, rank-ordered evidence set.
   - **Recursive Chunking**: Bounded chunking ($\le 1000$ characters, $150$ character overlap) preserving sentence and paragraph integrity with line and page number tracking.

2. **HIPAA Safe Harbor 18-Identifier Privacy Engine (SovereignAI Core)**
   - Full detection and right-to-left substitution across all **18 HIPAA Safe Harbor identifier categories**: Names, SSNs, MRNs, Phone, Fax, Email, Dates, Addresses, Financial/Account numbers, NPI Provider IDs, Health Plan IDs, Licenses, Vehicle VINs, Device IDs, URLs, IP addresses, and Biometric references.
   - Overlap and collision resolution (`_X` suffixing) with a reverse token map allowing 100% deterministic round-trip rehydration for authorized local environments.

3. **Cryptographic SHA-256 Audit Ledger**
   - Tamper-evident append-only Merkle-chained ledger recording every document ingestion, redaction, and local query.
   - Every block contains `previous_hash`, `timestamp`, `event_type`, and `data_hash` commitments.
   - **Zero PII Exposure**: Raw confidential data is never stored in audit blocks; only deterministic cryptographic hashes are recorded.

4. **Hardware & INT4 Quantization Telemetry Lab**
   - Analytical memory calculations strictly computed in **GiB** ($1024^3$ bytes): Parameter weights ($W$), Key-Value cache ($2 \times L \times H \times D \times \text{bytes}$), and activation footprints.
   - Live hardware feasibility indicators (e.g., 8 GiB vs 16 GiB unified memory compatibility).
   - Real-time host telemetry via `psutil` (CPU percentage, memory used/total in GiB, disk storage).

5. **Empirical Grounding & Heuristic Claim Verification**
   - Deterministic sentence-level claim extraction, n-gram quote matching, and citation validation.
   - Verification status: `VERIFIED`, `INFERRED`, or `UNSUPPORTED`.
   - Explicit heuristic metric labeling: `grounding_confidence_heuristic` and `unsupported_claim_rate_heuristic`.

6. **Deterministic Offline Fallback**
   - If local Ollama or LLM services are unreachable, the engine gracefully transitions to an offline deterministic synthesizer that surfaces verbatim evidence snippets and document citations without hallucination or pipeline failure.

---

## Architectural Overview

```
                      ┌───────────────────────────────────────┐
                      │    Client (Web UI / React + Vite)     │
                      │       Bound to 127.0.0.1:3000         │
                      └──────────────────┬────────────────────┘
                                         │ REST / SSE
                                         ▼
                      ┌───────────────────────────────────────┐
                      │   FastAPI Server (backend/main.py)    │
                      │       Bound to 127.0.0.1:8093         │
                      └──────────────────┬────────────────────┘
                                         │
               ┌─────────────────────────┴─────────────────────────┐
               ▼                                                   ▼
┌──────────────────────────────┐                   ┌──────────────────────────────┐
│     Privacy Guard Engine     │                   │       Audit Ledger           │
│  HIPAA 18-Category Redaction │                   │   SHA-256 Append-Only Chain  │
└──────────────┬───────────────┘                   └──────────────┬───────────────┘
               │ (Sanitized Query)                                │ (Commitment)
               ▼                                                   │
┌─────────────────────────────────────────────────────────────┐   │
│                 RAGEngine Orchestrator                      │◄──┘
│  ┌────────────────────────┐     ┌────────────────────────┐  │
│  │    Dense Embedding     │     │      Sparse Lexical    │  │
│  │ (384-D FAISS / Cosine) │     │     (BM25 from scratch)│  │
│  └───────────┬────────────┘     └───────────┬────────────┘  │
│              └──────────────┬───────────────┘               │
│                             ▼                               │
│                Reciprocal Rank Fusion (RRF k=60)            │
│                             │                               │
│                             ▼                               │
│             Top-K Evidence Context Chunks                   │
└─────────────────────────────┬───────────────────────────────┘
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│    Local Ollama Inference    │ │ Offline Verbatim Synthesizer │
│    (127.0.0.1:11434)         │ │ (Deterministic Citation Pill)│
└──────────────┬───────────────┘ └──────────────┬───────────────┘
               └──────────────┬─────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│          Heuristic Claim & Grounding Evaluator              │
│       - Quote matching against retrieved evidence           │
│       - Claim status: VERIFIED / INFERRED / UNSUPPORTED     │
│       - Metrics: grounding_confidence_heuristic             │
└─────────────────────────────────────────────────────────────┘
```

---

## Air-Gap Verification Semantics & Regulatory Caveats

### Honest Network Verification Policy
- In compliance with strict engineering ethics, this platform **never** asserts unprovable absolutes such as "zero egress" or "guaranteed 100% HIPAA compliant".
- The system binds strictly to loopback (`127.0.0.1:8093`).
- Network verification scripts (`scripts/verify_air_gap.py`) inspect the active server process socket table (`lsof -a -p <pid> -i -n -P` on macOS, `ss -tnp` on Linux) and verify that **0 non-loopback connections** are established during query processing.
- The platform enforces Content Security Policy (CSP) headers restricting socket connections to `127.0.0.1:8093`.

### Heuristic Metric Caveats
- All output metrics representing evaluation, claim grounding, risk, or memory predictions are explicitly labeled with `heuristic` or `estimated` across both backend Pydantic models and user interfaces (e.g., `grounding_confidence_heuristic`, `risk_score_heuristic`, `total_memory_gib_estimate`).
- Memory modeling is mathematical and analytical; actual runtime memory fluctuates based on OS unified memory caching, kernel buffers, and model batching.

---

## Directory Structure

```
sovereign-rag/
├── README.md                          # Platform documentation & architecture
├── requirements.txt                   # Production Python dependencies
├── .env.example                       # Sample environment configuration
├── .gitignore                         # Data and cache ignores
│
├── backend/                           # Core Python backend engine
│   ├── __init__.py
│   ├── main.py                        # FastAPI entry point & REST/SSE routes
│   ├── config.py                      # Thread-safe settings & atomic persistence
│   ├── models.py                      # Strict Pydantic domain models
│   ├── errors.py                      # Custom error hierarchy
│   ├── storage.py                     # Atomic disk I/O & fsync utilities
│   ├── vector_math.py                 # Pure-Python cosine & DualIndex vector search
│   ├── document_loader.py             # 4-tier PDF & text file extraction
│   ├── chunker.py                     # Recursive bounded chunking with line tracking
│   ├── bm25.py                        # Lexical BM25 from scratch with stopwords
│   ├── rrf.py                         # Reciprocal Rank Fusion (k=60)
│   ├── privacy_guard.py               # HIPAA Safe Harbor 18-category engine
│   ├── audit_ledger.py                # SHA-256 tamper-evident cryptographic ledger
│   ├── telemetry.py                   # Analytical GiB memory & psutil host stats
│   ├── ollama_client.py               # Local streaming Ollama client
│   ├── gemini_client.py               # Cloud Gemini client (mode-gated)
│   ├── evaluation.py                  # Claim verification matrix & grounding heuristic
│   ├── fallback_synth.py              # Offline deterministic verbatim synthesizer
│   └── rag_engine.py                  # Central thread-safe RAG pipeline orchestrator
│
├── backend/tests/                     # Comprehensive Pytest test suite (100+ tests)
│   ├── __init__.py
│   ├── conftest.py                    # Isolated temporary test fixtures
│   ├── test_config.py
│   ├── test_document_loader.py
│   ├── test_chunker.py
│   ├── test_vector_math.py
│   ├── test_bm25.py
│   ├── test_rrf.py
│   ├── test_privacy_guard.py
│   ├── test_audit_ledger.py
│   ├── test_telemetry.py
│   ├── test_ollama_client.py
│   ├── test_evaluation.py
│   ├── test_errors.py
│   └── test_end_to_end.py
│
├── frontend/                          # Vite + React 18 + TypeScript + Tailwind UI
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx                    # Multi-tab layout shell
│       ├── types.ts                   # Strict TypeScript models mirroring backend
│       ├── api.ts                     # REST client for 127.0.0.1:8093
│       ├── store.ts                   # Zustand state management
│       ├── index.css                  # Tailwind styles
│       ├── components/
│       │   ├── AirGapBadge.tsx        # Pulsing air-gap status badge & audit modal
│       │   ├── TelemetryHUD.tsx       # Live host resource & engine telemetry
│       │   ├── ChatInterface.tsx      # SSE streaming chat & citation cards
│       │   ├── RagVault.tsx           # Document library & drag-and-drop ingest
│       │   ├── ChunkLab.tsx           # Boundary inspector for chunk partitions
│       │   ├── QuantizationMatrix.tsx # INT4 model/memory sliders in GiB
│       │   ├── PiiInspector.tsx       # HIPAA redaction workbench & risk meter
│       │   ├── ComplianceAuditLedger.tsx # Merkle-chained SHA-256 audit table
│       │   ├── DiagnosticsView.tsx    # Subsystem status matrix & psutil metrics
│       │   └── ErrorBanner.tsx        # Visible error alert banner
│       └── hooks/
│           └── useSSE.ts              # EventSource / ReadableStream SSE hook
│
├── sample_data/                       # Sample evaluation datasets
│   ├── clinical_ehr_cardiology.txt    # De-identified cardiology patient discharge note
│   ├── financial_audit_q3.txt         # Master fund Q3 valuation & audit memorandum
│   ├── legal_msa.txt                  # Master Services Agreement with liability caps
│   └── defense_radar.txt              # Spectre-9 AESA radar technical data sheet
│
├── scripts/                           # Operational and verification scripts
│   ├── verify.py                      # 22-step full verification test runner
│   ├── benchmark.py                   # 20-query empirical perf_counter benchmark
│   ├── verify_air_gap.py              # Process socket inspection for loopback enforcement
│   └── merge_codebase.py              # Single-file text consolidator for airgap audits
│
└── data/                              # Local database state (gitignored)
    ├── faiss.index
    ├── chunks.pkl
    ├── manifest.json
    ├── audit_ledger.json
    └── uploads/
```

---

## Quickstart Guide

### 1. Backend Setup & Virtual Environment

```bash
# Navigate to repository root
cd sovereign-rag

# Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt
```

### 2. Run Verification & Test Suite

```bash
# Execute Pytest test suite with code coverage
pytest backend/tests/ -v --cov=backend

# Run the 22-step platform verification script
python scripts/verify.py

# Run the socket inspection air-gap verifier
python scripts/verify_air_gap.py

# Execute empirical 20-query benchmark
python scripts/benchmark.py
```

### 3. Launch Backend Server

```bash
# Launch FastAPI server bound strictly to loopback
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8093
```
API documentation is available at `http://127.0.0.1:8093/docs`.

### 4. Launch Frontend Web UI

```bash
# In a new terminal:
cd sovereign-rag/frontend

# Install node dependencies
npm install

# Build production assets
npm run build

# Start local dev server
npm run dev
```
Access the SovereignRAG dashboard at `http://127.0.0.1:3000`.

---

## API Reference Summary

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Subsystem status, loopback binding, CSP enforcement, audit integrity |
| `GET` | `/api/mode` | Returns active engine mode (`airgap` or `cloud`) |
| `POST` | `/api/mode` | Toggles engine mode (`airgap` or `cloud`) |
| `POST` | `/api/rag/ingest` | Multipart file upload with category tagging and chunk indexing |
| `GET` | `/api/rag/documents`| Returns all ingested documents and chunk metadata |
| `POST` | `/api/rag/query` | RAG retrieval, PII redaction, synthesis, and claim verification |
| `POST` | `/api/chat` | Server-Sent Events (SSE) streaming query endpoint |
| `POST` | `/api/privacy/redact` | HIPAA Safe Harbor 18-category de-identification |
| `POST` | `/api/privacy/restore`| Exact round-trip token rehydration |
| `GET` | `/api/audit/logs` | Fetches chained SHA-256 audit ledger records |
| `POST` | `/api/audit/verify` | Validates complete cryptographic hash chain integrity |
| `GET` | `/api/telemetry/memory` | Analytical GiB memory calculation for specified model & quant |
| `GET` | `/api/telemetry/host` | Live host CPU, RAM, and disk utilization via `psutil` |
| `GET` | `/api/telemetry/models` | List of supported local model families and quantization formats |

---

## Benchmark Results (Empirical)

Measured on Apple Silicon (`arm64`) using `time.perf_counter()` over $N=20$ queries against the sample enterprise corpus:

- **Retrieval Latency (RRF + FAISS + BM25)**: $\text{P50} = 0.51 \text{ ms}$, $\text{P95} = 2.59 \text{ ms}$, $\text{Mean} = 0.69 \text{ ms}$
- **End-to-End Latency (Offline Fallback)**: $\text{P50} = 21.35 \text{ ms}$, $\text{P95} = 58.48 \text{ ms}$, $\text{Mean} = 24.04 \text{ ms}$
- **Doc Match Accuracy**: $100.0\%$ (20/20 top-1 retrieved documents matched expected ground truth)
- **Grounding Confidence**: $1.000$ (heuristic)
- **Unsupported Claim Rate**: $0.000$ (heuristic)

---

## License

MIT License. Designed and engineered for high-assurance confidential computing.
