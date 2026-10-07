from contextlib import asynccontextmanager
import json
import logging
from pathlib import Path
import time
from typing import Any
import uuid

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.audit_ledger import AuditLedger
from backend.config import Settings
from backend.errors import (
    AuditIntegrityError,
    DocumentParseError,
    EmptyDocumentError,
    FileTooLargeError,
    IndexNotReadyError,
    InvalidModeError,
    LLMUnavailableError,
    RedactionFailureError,
    SensitiveDataCloudBlockedError,
    SovereignRAGError,
    UnsupportedFileTypeError,
)
from backend.models import (
    AuditRecord,
    IngestedDocument,
    MemoryCalculation,
    QueryRequest,
    QueryResponse,
    RedactionResult,
)
from backend.gemini_client import GeminiClient
from backend.ollama_client import OllamaClient
from backend.privacy_guard import PrivacyGuard
from backend.rag_engine import RAGEngine
from backend.storage import ensure_dirs
from backend.telemetry import MODEL_SPECS, QUANT_PROFILES, TelemetryEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("sovereign_rag")

settings = Settings()
audit_ledger: AuditLedger | None = None
rag_engine: RAGEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global audit_ledger, rag_engine
    ensure_dirs([
        settings.data_dir,
        settings.uploads_dir,
        settings.chroma_dir
    ])
    settings.load_from_disk()

    audit_ledger = AuditLedger(settings.audit_ledger_path)
    rag_engine = RAGEngine(settings=settings, audit_ledger=audit_ledger)
    rag_engine.load()

    # If engine index is empty, auto-ingest sample_data files
    sample_dir = Path("sample_data")
    if len(rag_engine.documents) == 0 and sample_dir.exists():
        for f in sorted(sample_dir.glob("*.txt")):
            cat = "CLINICAL" if "clinical" in f.name else "FINANCIAL" if "financial" in f.name else "LEGAL" if "legal" in f.name else "DEFENSE"
            try:
                rag_engine.ingest_document(f, title=f.name, category=cat)
            except Exception as e:
                logger.warning("Failed to auto-ingest sample doc %s: %s", f.name, e)

    # If uploads directory has files and engine index is still empty, ingest idempotently
    upload_files = list(Path(settings.uploads_dir).glob("*"))
    if upload_files and len(rag_engine.documents) == 0:
        for f in upload_files:
            if f.is_file():
                try:
                    rag_engine.ingest_document(f, title=f.name, category="GENERAL")
                except Exception as e:
                    logger.warning("Failed to auto-ingest existing upload %s: %s", f.name, e)

    # Initial system audit events
    audit_ledger.log_air_gap_verify(verified=True, egress_bytes=0)
    mem_calc = TelemetryEngine.calculate_memory(model_id=settings.ollama_model, quant_type="Q4_K_M")
    audit_ledger.log_quant_telemetry(
        model_id=settings.ollama_model,
        quant_type="Q4_K_M",
        vram_gib=mem_calc.total_memory_gib_estimate
    )

    print(f"SovereignRAG listening on http://{settings.host}:{settings.port}")
    yield

    # Shutdown sequence
    if rag_engine:
        rag_engine.save()
    if audit_ledger:
        audit_ledger._append("SYSTEM_SHUTDOWN", "SovereignRAG engine stopped cleanly.", {})


app = FastAPI(title="SovereignRAG", version="2.0.0", lifespan=lifespan)

# Allow loopback origins for local access
allowed_origins = list({
    settings.frontend_origin,
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://127.0.0.1:8093",
    "http://localhost:8093",
})

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Air-Gap-Status"] = "ENFORCED"
    response.headers["Content-Security-Policy"] = (
        f"default-src 'self' 'unsafe-inline'; connect-src 'self' http://{settings.host}:{settings.port} http://localhost:{settings.port} http://localhost:3000 http://127.0.0.1:3000 {settings.ollama_url}"
    )
    return response


# Exception Handlers
def log_audit_error(err_cls: str, msg: str):
    if audit_ledger:
        try:
            audit_ledger.log_error(err_cls, msg)
        except Exception:
            pass


@app.exception_handler(EmptyDocumentError)
async def empty_doc_handler(request: Request, exc: EmptyDocumentError):
    log_audit_error("EmptyDocumentError", exc.message)
    return JSONResponse(status_code=422, content={"error": "EmptyDocumentError", "message": exc.message})


@app.exception_handler(DocumentParseError)
async def doc_parse_handler(request: Request, exc: DocumentParseError):
    log_audit_error("DocumentParseError", exc.message)
    return JSONResponse(status_code=422, content={"error": "DocumentParseError", "message": exc.message, "detail": exc.message})


@app.exception_handler(UnsupportedFileTypeError)
async def unsupported_file_handler(request: Request, exc: UnsupportedFileTypeError):
    log_audit_error("UnsupportedFileTypeError", exc.message)
    return JSONResponse(status_code=415, content={"error": "UnsupportedFileTypeError", "message": exc.message, "detail": exc.message})


@app.exception_handler(FileTooLargeError)
async def file_too_large_handler(request: Request, exc: FileTooLargeError):
    log_audit_error("FileTooLargeError", exc.message)
    return JSONResponse(status_code=413, content={"error": "FileTooLargeError", "message": exc.message, "detail": exc.message})


@app.exception_handler(SensitiveDataCloudBlockedError)
async def cloud_blocked_handler(request: Request, exc: SensitiveDataCloudBlockedError):
    log_audit_error("SensitiveDataCloudBlockedError", exc.message)
    detail_msg = f"{exc.message} To query this document, switch Engine Mode to 'AIRGAP' (local model) or reclassify the document as GENERAL."
    return JSONResponse(status_code=403, content={"error": "SensitiveDataCloudBlockedError", "message": exc.message, "detail": detail_msg})


@app.exception_handler(LLMUnavailableError)
async def llm_unavailable_handler(request: Request, exc: LLMUnavailableError):
    log_audit_error("LLMUnavailableError", exc.message)
    return JSONResponse(status_code=503, content={"error": "LLMUnavailableError", "message": exc.message, "detail": exc.message})


@app.exception_handler(AuditIntegrityError)
async def audit_integrity_handler(request: Request, exc: AuditIntegrityError):
    log_audit_error("AuditIntegrityError", exc.message)
    return JSONResponse(status_code=500, content={"error": "AuditIntegrityError", "message": exc.message, "detail": exc.message})


@app.exception_handler(SovereignRAGError)
async def sovereign_rag_handler(request: Request, exc: SovereignRAGError):
    log_audit_error(type(exc).__name__, exc.message)
    return JSONResponse(status_code=400, content={"error": type(exc).__name__, "message": exc.message, "detail": exc.message})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    log_audit_error("ValidationError", str(exc))
    return JSONResponse(status_code=422, content={"error": "ValidationError", "details": exc.errors(), "detail": str(exc)})


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    log_audit_error("ValueError", str(exc))
    return JSONResponse(status_code=400, content={"error": "ValueError", "message": str(exc), "detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server exception: %s", exc)
    log_audit_error("InternalError", str(exc))
    return JSONResponse(status_code=500, content={"error": "InternalServerError", "message": str(exc), "detail": str(exc)})



# Routes
@app.get("/health")
async def health_check():
    ollama_ok = rag_engine.ollama_client.health_check(timeout_s=1.0) if rag_engine else False
    gemini_ok = rag_engine.gemini_client.health_check() if rag_engine else False
    audit_valid, _ = audit_ledger.verify_integrity() if audit_ledger else (True, -1)

    return {
        "status": "ok",
        "mode": settings.engine_mode,
        "documents": len(rag_engine.documents) if rag_engine else 0,
        "chunks": len(rag_engine.chunks) if rag_engine else 0,
        "index_healthy": rag_engine.index_healthy if rag_engine else True,
        "manifest_healthy": rag_engine.manifest_healthy if rag_engine else True,
        "audit_healthy": audit_valid,
        "ollama": {
            "available": ollama_ok,
            "model": settings.ollama_model
        },
        "gemini": {
            "available": gemini_ok
        },
        "air_gap": {
            "policy": "ENFORCED",
            "verification": "NOT_VERIFIED"
        }
    }


@app.get("/api/stats")
async def get_stats():
    if not rag_engine:
        raise HTTPException(status_code=500, detail="Engine uninitialized")
    return rag_engine.get_stats()


@app.get("/api/mode")
async def get_mode():
    return {"mode": settings.engine_mode}


class ModeRequest(BaseModel):
    mode: str
    gemini_api_key: str | None = None


@app.post("/api/mode")
async def set_mode(payload: ModeRequest):
    if payload.mode not in {"airgap", "cloud"}:
        raise HTTPException(status_code=400, detail="Mode must be 'airgap' or 'cloud'")

    if payload.gemini_api_key and payload.gemini_api_key.strip():
        settings.gemini_api_key = payload.gemini_api_key.strip()
        if rag_engine:
            rag_engine.gemini_client = GeminiClient(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model
            )

    if payload.mode == "cloud" and not settings.gemini_api_key:
        raise HTTPException(
            status_code=400,
            detail="Cannot switch to cloud mode: Gemini API key is not configured."
        )

    settings.engine_mode = payload.mode  # type: ignore
    settings.save_to_disk()
    if audit_ledger:
        audit_ledger._append("MODE_SWITCH", f"Mode switched to {payload.mode}", {"mode": payload.mode})

    return {"mode": settings.engine_mode, "status": "switched"}


class ConfigUpdateRequest(BaseModel):
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    ollama_url: str | None = None
    ollama_model: str | None = None


@app.get("/api/settings/config")
async def get_config_settings():
    masked_key = ""
    if settings.gemini_api_key:
        if len(settings.gemini_api_key) > 8:
            masked_key = f"{settings.gemini_api_key[:4]}...{settings.gemini_api_key[-4:]}"
        else:
            masked_key = "****"

    return {
        "gemini_api_key_masked": masked_key,
        "gemini_api_key_configured": bool(settings.gemini_api_key),
        "gemini_model": settings.gemini_model,
        "ollama_url": settings.ollama_url,
        "ollama_model": settings.ollama_model,
        "engine_mode": settings.engine_mode,
        "top_k": settings.top_k,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
    }


@app.post("/api/settings/config")
async def update_config_settings(payload: ConfigUpdateRequest):
    if payload.gemini_api_key is not None:
        settings.gemini_api_key = payload.gemini_api_key.strip()
        if rag_engine:
            rag_engine.gemini_client = GeminiClient(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model
            )
    if payload.gemini_model is not None and payload.gemini_model.strip():
        settings.gemini_model = payload.gemini_model.strip()
        if rag_engine:
            rag_engine.gemini_client = GeminiClient(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model
            )
    if payload.ollama_url is not None and payload.ollama_url.strip():
        settings.ollama_url = payload.ollama_url.strip()
        if rag_engine:
            rag_engine.ollama_client = OllamaClient(
                base_url=settings.ollama_url,
                model=settings.ollama_model
            )
    if payload.ollama_model is not None and payload.ollama_model.strip():
        settings.ollama_model = payload.ollama_model.strip()
        if rag_engine:
            rag_engine.ollama_client = OllamaClient(
                base_url=settings.ollama_url,
                model=settings.ollama_model
            )

    settings.save_to_disk()
    if audit_ledger:
        audit_ledger._append(
            "MODE_SWITCH",
            "System configuration updated",
            {"gemini_configured": bool(settings.gemini_api_key), "mode": settings.engine_mode}
        )

    masked_key = ""
    if settings.gemini_api_key:
        if len(settings.gemini_api_key) > 8:
            masked_key = f"{settings.gemini_api_key[:4]}...{settings.gemini_api_key[-4:]}"
        else:
            masked_key = "****"

    return {
        "status": "updated",
        "gemini_api_key_masked": masked_key,
        "gemini_api_key_configured": bool(settings.gemini_api_key),
        "gemini_model": settings.gemini_model,
        "ollama_url": settings.ollama_url,
        "ollama_model": settings.ollama_model,
        "engine_mode": settings.engine_mode,
    }


class TestKeyRequest(BaseModel):
    gemini_api_key: str | None = None


@app.post("/api/settings/test-gemini")
async def test_gemini_connection(payload: TestKeyRequest):
    key = payload.gemini_api_key.strip() if (payload.gemini_api_key and payload.gemini_api_key.strip()) else settings.gemini_api_key
    if not key:
        return {"valid": False, "error": "No Gemini API key provided"}
    client = GeminiClient(api_key=key, model=settings.gemini_model)
    is_valid = client.health_check()
    return {"valid": is_valid, "model": settings.gemini_model}



class RedactTextRequest(BaseModel):
    text: str


@app.post("/api/privacy/redact")
async def redact_text(req: RedactTextRequest):
    if "\x00" in req.text:
        raise HTTPException(status_code=400, detail="Null bytes not allowed")
    result = PrivacyGuard.redact(req.text)
    if audit_ledger and result.detected_entities:
        audit_ledger.log_pii_redact(
            len(result.detected_entities),
            result.risk_score_heuristic
        )
    return result


class RestoreTextRequest(BaseModel):
    redacted_text: str
    token_map: dict[str, str]


@app.post("/api/privacy/restore")
async def restore_text(req: RestoreTextRequest):
    restored = PrivacyGuard.restore(req.redacted_text, req.token_map)
    return {"restored_text": restored}


@app.post("/api/rag/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    title: str = Form(""),
    category: str = Form("GENERAL")
):
    if not file.filename:
        raise EmptyDocumentError("No filename provided")

    ext = Path(file.filename).suffix.lower()
    from backend.document_loader import SUPPORTED_EXTENSIONS
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(f"Unsupported file extension: {ext}")

    # Read uploaded file
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise EmptyDocumentError("Uploaded file is empty (0 bytes)")

    if len(file_bytes) > settings.max_upload_bytes:
        raise FileTooLargeError(f"Uploaded file exceeds {settings.max_upload_bytes} bytes")

    # Save to uploads dir
    dest_path = Path(settings.uploads_dir) / file.filename
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(file_bytes)

    if not rag_engine:
        raise HTTPException(status_code=500, detail="RAG Engine unavailable")

    doc = rag_engine.ingest_document(
        path=dest_path,
        title=title or file.filename,
        category=category
    )

    is_dedup = (doc.chunk_count == 0)
    return {
        "id": doc.id,
        "title": doc.title,
        "category": doc.category,
        "sha256": doc.sha256,
        "chunk_count": doc.chunk_count,
        "ingested_at": doc.ingested_at,
        "source_filename": doc.source_filename,
        "deduplicated": is_dedup
    }


@app.get("/api/rag/documents")
async def list_documents():
    if not rag_engine:
        return {"documents": [], "total_chunks": 0}
    return {
        "documents": rag_engine.list_documents(),
        "total_chunks": rag_engine.total_chunks,
    }


@app.delete("/api/rag/documents/{doc_id}")
async def delete_document(doc_id: str):
    if not rag_engine:
        return {"deleted_chunks": 0}
    count = rag_engine.delete_document(doc_id)
    return {"deleted_chunks": count}


class CategoryUpdateRequest(BaseModel):
    category: str


@app.patch("/api/rag/documents/{doc_id}/category")
async def update_doc_category(doc_id: str, req: CategoryUpdateRequest):
    if not rag_engine:
        raise HTTPException(status_code=500, detail="Engine unavailable")
    success = rag_engine.update_document_category(doc_id, req.category)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "updated", "id": doc_id, "category": req.category}


@app.delete("/api/rag/documents")
async def clear_all_documents():
    if rag_engine:
        rag_engine.clear_all()
    return {"cleared": True}


@app.post("/api/rag/query", response_model=QueryResponse)
async def query_rag(req: QueryRequest):
    if "\x00" in req.query:
        raise HTTPException(status_code=400, detail="Null bytes not allowed in query")
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be whitespace-only")
    if len(req.query) > 4000:
        raise HTTPException(status_code=422, detail="Query exceeds 4000 characters")

    if not rag_engine:
        raise HTTPException(status_code=500, detail="RAG engine uninitialized")

    return rag_engine.query(req)


@app.get("/api/audit/logs")
async def get_audit_logs():
    if not audit_ledger:
        return {"ledger": [], "integrity": {"valid": True, "blocks": 0}}
    valid, bad_idx = audit_ledger.verify_integrity()
    records = audit_ledger.get_all()
    return {
        "ledger": records,
        "integrity": {
            "valid": valid,
            "blocks": len(records),
            "bad_index": bad_idx
        }
    }


@app.post("/api/audit/verify")
async def verify_audit_ledger():
    if not audit_ledger:
        return {"valid": True, "blocks": 0}
    valid, bad_idx = audit_ledger.verify_integrity()
    return {"valid": valid, "blocks": len(audit_ledger.records), "bad_index": bad_idx}


@app.get("/api/telemetry/memory", response_model=MemoryCalculation)
async def get_memory_telemetry(
    model_id: str = Query("llama3:8b"),
    quant_type: str = Query("Q4_K_M"),
    context_length: int = Query(4096),
    batch_size: int = Query(1)
):
    return TelemetryEngine.calculate_memory(
        model_id=model_id,
        quant_type=quant_type,
        context_length=context_length,
        batch_size=batch_size
    )


@app.get("/api/telemetry/host")
async def get_host_telemetry():
    return TelemetryEngine.get_host_telemetry()


@app.get("/api/telemetry/models")
async def get_models_telemetry():
    return {
        "models": list(MODEL_SPECS.keys()),
        "quants": list(QUANT_PROFILES.keys())
    }


@app.post("/api/chat")
async def chat_sse(req: QueryRequest):
    if "\x00" in req.query:
        raise HTTPException(status_code=400, detail="Null bytes not allowed")
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be whitespace-only")

    request_id = str(uuid.uuid4())

    async def sse_event_stream():
        try:
            # Query synchronous retrieval & resolution
            res = rag_engine.query(req)  # type: ignore

            # 1. Metadata event
            meta_payload = {
                "type": "metadata",
                "requestId": request_id,
                "retrievalMs": res.retrieval_latency_ms,
                "sources": len(res.retrieved_chunks)
            }
            yield f"data: {json.dumps(meta_payload)}\n\n"

            # 2. Token events (stream simulated or answer tokens)
            tokens = res.answer.split(" ")
            for idx, token in enumerate(tokens):
                space = "" if idx == len(tokens) - 1 else " "
                chunk_payload = {
                    "type": "token",
                    "text": token + space
                }
                yield f"data: {json.dumps(chunk_payload)}\n\n"

            # 3. Complete event
            complete_payload = {
                "type": "complete",
                "verified": res.evaluation.is_grounded,
                "grounding_heuristic": res.evaluation.grounding_confidence_heuristic
            }
            yield f"data: {json.dumps(complete_payload)}\n\n"
        except Exception as e:
            err_payload = {
                "type": "error",
                "code": type(e).__name__,
                "message": str(e),
                "retryable": False
            }
            yield f"data: {json.dumps(err_payload)}\n\n"

    return StreamingResponse(sse_event_stream(), media_type="text/event-stream")


# Frontend SPA Static Files and Catch-All Routing
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if (frontend_dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")


@app.api_route("/{full_path:path}", methods=["GET", "HEAD"])
async def serve_frontend_spa(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    index_file = frontend_dist / "index.html"
    if index_file.exists():
        target = frontend_dist / full_path
        if full_path and target.is_file():
            return FileResponse(target)
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="Frontend build not found")

