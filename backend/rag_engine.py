import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import re
import threading
import time
from typing import Any

from backend.audit_ledger import AuditLedger
from backend.bm25 import BM25Index
from backend.chunker import Chunker
from backend.config import Settings
from backend.document_loader import DocumentLoader
from backend.errors import (
    AuditIntegrityError,
    EmptyDocumentError,
    FileTooLargeError,
    IndexNotReadyError,
    LLMUnavailableError,
    SensitiveDataCloudBlockedError,
    SovereignRAGError,
)
from backend.evaluation import evaluate_grounding
from backend.fallback_synth import generate as fallback_generate
from backend.gemini_client import GeminiClient
from backend.models import (
    ClaimVerification,
    DocumentChunk,
    EvaluationReport,
    IngestedDocument,
    QueryRequest,
    QueryResponse,
    RedactionResult,
    RetrievedChunk,
)
from backend.ollama_client import OllamaClient, SOVEREIGN_SYSTEM_PROMPT
from backend.privacy_guard import PrivacyGuard
from backend.rrf import reciprocal_rank_fusion
from backend.storage import (
    atomic_write_bytes,
    atomic_write_json,
    atomic_write_pickle,
    ensure_dirs,
    read_json,
    read_pickle,
)
from backend.vector_math import DualIndex, normalize

logger = logging.getLogger(__name__)

SENSITIVE_CATEGORIES = {"CLINICAL", "FINANCIAL", "LEGAL", "DEFENSE"}


STOPWORDS = {
    "what", "is", "the", "a", "an", "of", "in", "to", "and", "or", "for", "on",
    "with", "as", "by", "at", "from", "it", "this", "that", "are", "was", "were",
    "be", "been", "have", "has", "had", "do", "does", "did", "how", "why", "when",
    "which", "who", "whom"
}


def deterministic_embed(text: str, dim: int) -> list[float]:
    """Generates a high-quality deterministic pseudo-semantic vector without network calls.

    Uses character n-grams and token hashing with cosine-compatible L2 normalization.
    """
    vec = [0.0] * dim
    raw_words = re.findall(r"\w+", text.lower())
    words = [w for w in raw_words if w not in STOPWORDS]
    if not words:
        words = raw_words
    if not words:
        return vec

    for idx, w in enumerate(words):
        h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
        slot = h % dim
        sign = 1.0 if ((h >> 8) & 1) else -1.0
        vec[slot] += sign * (1.0 + 1.0 / (idx + 1))

        # Bigrams for local phrase semantics
        if idx > 0:
            bigram = f"{words[idx - 1]}_{w}"
            h_bi = int(hashlib.sha1(bigram.encode("utf-8")).hexdigest(), 16)
            slot_bi = h_bi % dim
            sign_bi = 1.0 if ((h_bi >> 8) & 1) else -1.0
            vec[slot_bi] += sign_bi * 1.5

    return normalize(vec)


class RAGEngine:
    def __init__(self, settings: Settings, audit_ledger: AuditLedger | None = None):
        self.settings = settings
        self.audit_ledger = audit_ledger or AuditLedger(settings.audit_ledger_path)
        self.lock = threading.RLock()

        self.documents: dict[str, IngestedDocument] = {}
        self.documents_by_sha: dict[str, IngestedDocument] = {}
        self.chunks: dict[str, DocumentChunk] = {}
        self.bm25_index = BM25Index(k1=settings.bm25_k1, b=settings.bm25_b)
        self.dual_index = DualIndex(
            airgap_dim=settings.airgap_embedding_dim,
            cloud_dim=settings.cloud_embedding_dim,
            faiss_index_path=settings.faiss_index_path,
            chroma_dir=settings.chroma_dir
        )

        self.ollama_client = OllamaClient(
            base_url=settings.ollama_url,
            model=settings.ollama_model
        )
        self.gemini_client = GeminiClient(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model
        )

        self.index_healthy = True
        self.manifest_healthy = True
        self.load()

    @property
    def total_chunks(self) -> int:
        return len(self.chunks)

    def _embed(self, text: str, mode: str) -> list[float]:
        dim = self.settings.cloud_embedding_dim if mode == "cloud" else self.settings.airgap_embedding_dim
        return deterministic_embed(text, dim)

    def ingest_document(
        self,
        path: Path,
        title: str,
        category: str = "GENERAL"
    ) -> IngestedDocument:
        path = Path(path)
        with open(path, "rb") as f:
            file_bytes = f.read()

        # Step 1: sha256_raw
        sha256_raw = hashlib.sha256(file_bytes).hexdigest()

        with self.lock:
            # Step 2: Duplicate check
            if sha256_raw in self.documents_by_sha:
                existing = self.documents_by_sha[sha256_raw]
                return IngestedDocument(
                    id=existing.id,
                    title=existing.title,
                    category=existing.category,
                    sha256=existing.sha256,
                    chunk_count=0,
                    ingested_at=existing.ingested_at,
                    source_filename=existing.source_filename
                )

            # Step 3: DocumentLoader.load
            extracted_text, doc_type = DocumentLoader.load(
                path,
                max_upload_bytes=self.settings.max_upload_bytes,
                max_extracted_chars=self.settings.max_extracted_chars
            )

            # Step 4: Empty text check
            if not extracted_text or not extracted_text.strip():
                raise EmptyDocumentError(f"Document {path.name} contains 0 extractable text.")

            # Step 5: PII Redaction
            safe_text = extracted_text.replace("\x00", " ")
            redaction = PrivacyGuard.redact(safe_text)
            clean_text = redaction.redacted_text

            # Step 6: Chunker.chunk
            doc_id = f"doc_{hashlib.md5(sha256_raw.encode('utf-8')).hexdigest()[:10]}"
            valid_category = category if category in {"CLINICAL", "FINANCIAL", "LEGAL", "DEFENSE", "GENERAL"} else "GENERAL"

            chunks = Chunker.chunk(
                text=clean_text,
                chunk_size=self.settings.chunk_size,
                overlap=self.settings.chunk_overlap,
                doc_name=path.name,
                category=valid_category,  # type: ignore
                doc_id=doc_id
            )

            # Step 7: Chunks limit check
            if len(chunks) > self.settings.max_chunks_per_doc:
                raise FileTooLargeError(
                    f"Generated {len(chunks)} chunks exceeds max limit of {self.settings.max_chunks_per_doc}"
                )

            # Steps 8 & 9: Embeddings in airgap and cloud spaces
            airgap_vecs = [self._embed(c.content, "airgap") for c in chunks]
            cloud_vecs = [self._embed(c.content, "cloud") for c in chunks]
            chunk_ids = [c.id for c in chunks]

            # Steps 10, 11, 12: Index additions
            self.dual_index.add_airgap(chunk_ids, airgap_vecs)

            cloud_metas = [
                {
                    "doc_name": c.doc_name,
                    "category": c.category,
                    "page_number": c.page_number,
                    "start_line": c.start_line,
                    "end_line": c.end_line
                }
                for c in chunks
            ]
            self.dual_index.add_cloud(chunk_ids, cloud_vecs, cloud_metas)

            bm25_items = [(c.id, c.content) for c in chunks]
            self.bm25_index.add_batch(bm25_items)

            for c in chunks:
                self.chunks[c.id] = c

            ts = datetime.now(timezone.utc).isoformat()
            ingested_doc = IngestedDocument(
                id=doc_id,
                title=title or path.name,
                category=valid_category,  # type: ignore
                sha256=sha256_raw,
                chunk_count=len(chunks),
                ingested_at=ts,
                source_filename=path.name
            )

            self.documents[doc_id] = ingested_doc
            self.documents_by_sha[sha256_raw] = ingested_doc

            # Step 13: Atomic Persistence
            self.save()

            # Step 14: Audit Ledger
            self.audit_ledger.log_document_ingest(ingested_doc)

            return ingested_doc

    def query(self, req: QueryRequest) -> QueryResponse:
        t0 = time.perf_counter()
        retrieval_t0 = t0

        # Step 2: Query Redaction
        redaction: RedactionResult | None = None
        effective_query = req.query
        if req.redact_pii:
            redaction = PrivacyGuard.redact(req.query)
            effective_query = redaction.redacted_text
            if redaction.detected_entities:
                self.audit_ledger.log_pii_redact(
                    len(redaction.detected_entities),
                    redaction.risk_score_heuristic
                )

        # Step 3: Retrieval
        retrieved_chunks: list[RetrievedChunk] = []
        if req.use_rag:
            with self.lock:
                q_vec = self._embed(effective_query, req.mode)
                if req.mode == "airgap":
                    dense_scored = self.dual_index.search_airgap(q_vec, top_k=20)
                else:
                    dense_scored = self.dual_index.search_cloud(q_vec, top_k=20, mode=req.mode)

                dense_ids = [cid for cid, _ in dense_scored]
                dense_score_map = {cid: score for cid, score in dense_scored}

                bm25_scored = self.bm25_index.search(effective_query, top_k=20)
                bm25_ids = [cid for cid, _ in bm25_scored]
                bm25_score_map = {cid: score for cid, score in bm25_scored}

                fused = reciprocal_rank_fusion([dense_ids, bm25_ids], k=self.settings.rrf_k)
                top_items = fused[:req.top_k]

                for cid, rrf_score in top_items:
                    if cid in self.chunks:
                        ch = self.chunks[cid]
                        sim_s = dense_score_map.get(cid, 0.0)
                        bm_s = bm25_score_map.get(cid, 0.0)
                        citation = f"Doc: {ch.doc_name}, Page {ch.page_number}, Line {ch.start_line}-{ch.end_line}"
                        retrieved_chunks.append(
                            RetrievedChunk(
                                chunk_id=ch.id,
                                doc_name=ch.doc_name,
                                category=ch.category,
                                page_number=ch.page_number,
                                start_line=ch.start_line,
                                end_line=ch.end_line,
                                text=ch.content,
                                similarity_score=round(sim_s, 4),
                                bm25_score=round(bm_s, 4),
                                rrf_score=round(rrf_score, 4),
                                citation_label=citation
                            )
                        )

        retrieval_latency_ms = round((time.perf_counter() - retrieval_t0) * 1000, 2)

        # Step 1: Cloud Sensitivity Rule Enforcement
        if req.mode == "cloud":
            for c in retrieved_chunks:
                if c.category in SENSITIVE_CATEGORIES:
                    self.audit_ledger.log_error(
                        "SensitiveDataCloudBlockedError",
                        f"Chunk {c.chunk_id} from category {c.category} is sensitive and cannot be sent to cloud."
                    )
                    raise SensitiveDataCloudBlockedError(
                        f"Query blocked: Retrieved chunk '{c.doc_name}' belongs to sensitive category '{c.category}'. "
                        "Transfer to external cloud model is prohibited."
                    )

        # Step 4: Empty context check
        if not retrieved_chunks and req.use_rag:
            total_lat = round((time.perf_counter() - t0) * 1000, 2)
            eval_rep = evaluate_grounding("No relevant documents found in the local knowledge base.", [])
            self.audit_ledger.log_local_query(
                model=self.settings.ollama_model if req.mode == "airgap" else self.settings.gemini_model,
                chunk_count=0,
                grounded=False
            )
            return QueryResponse(
                query=req.query,
                answer="No relevant documents found in the local knowledge base.",
                retrieved_chunks=[],
                evaluation=eval_rep,
                redaction=redaction,
                latency_ms=total_lat,
                retrieval_latency_ms=retrieval_latency_ms,
                generation_latency_ms=0.0,
                mode=req.mode,
                model_name=self.settings.ollama_model if req.mode == "airgap" else self.settings.gemini_model,
                air_gapped=(req.mode == "airgap"),
                offline_fallback=False
            )

        # Step 5: Build context string with explicit labels
        context_blocks = []
        for i, c in enumerate(retrieved_chunks, start=1):
            block = f"--- SOURCE {i} [{c.citation_label}] ---\n{c.text}\n"
            context_blocks.append(block)
        context_str = "\n".join(context_blocks)

        user_prompt = f"Context Blocks:\n{context_str}\n\nQuestion:\n{effective_query}"

        # Step 6: Call LLM (without holding lock)
        gen_t0 = time.perf_counter()
        answer = ""
        offline_fallback = False
        model_name = self.settings.ollama_model if req.mode == "airgap" else self.settings.gemini_model

        if req.mode == "cloud":
            if not self.settings.gemini_api_key:
                raise LLMUnavailableError("Gemini API key not configured")
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        answer = pool.submit(
                            asyncio.run,
                            self.gemini_client.generate(SOVEREIGN_SYSTEM_PROMPT, user_prompt)
                        ).result()
                else:
                    answer = asyncio.run(
                        self.gemini_client.generate(SOVEREIGN_SYSTEM_PROMPT, user_prompt)
                    )
            except LLMUnavailableError:
                raise
            except Exception as e:
                raise LLMUnavailableError(f"Cloud generation failure: {e}") from e
        else:
            # Airgap mode: Check Ollama
            ollama_online = self.ollama_client.health_check(timeout_s=1.0)
            if ollama_online:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            answer = pool.submit(
                                asyncio.run,
                                self.ollama_client.chat(SOVEREIGN_SYSTEM_PROMPT, user_prompt)
                            ).result()
                    else:
                        answer = asyncio.run(
                            self.ollama_client.chat(SOVEREIGN_SYSTEM_PROMPT, user_prompt)
                        )
                except Exception as e:
                    logger.warning("Ollama call failed (%s); switching to deterministic fallback", e)
                    answer = fallback_generate(effective_query, retrieved_chunks)
                    offline_fallback = True
            else:
                answer = fallback_generate(effective_query, retrieved_chunks)
                offline_fallback = True

        generation_latency_ms = round((time.perf_counter() - gen_t0) * 1000, 2)

        # Restore PII tokens in answer if query had redactions
        if redaction and redaction.token_map:
            answer = PrivacyGuard.restore(answer, redaction.token_map)

        # Step 7: Grounding evaluation
        evaluation = evaluate_grounding(answer, retrieved_chunks)

        total_latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        # Step 8: Audit ledger
        self.audit_ledger.log_local_query(
            model=f"{model_name}{' (FALLBACK)' if offline_fallback else ''}",
            chunk_count=len(retrieved_chunks),
            grounded=evaluation.is_grounded
        )

        # Step 9: Return response
        return QueryResponse(
            query=req.query,
            answer=answer,
            retrieved_chunks=retrieved_chunks,
            evaluation=evaluation,
            redaction=redaction,
            latency_ms=total_latency_ms,
            retrieval_latency_ms=retrieval_latency_ms,
            generation_latency_ms=generation_latency_ms,
            mode=req.mode,
            model_name=model_name,
            air_gapped=(req.mode == "airgap"),
            offline_fallback=offline_fallback
        )

    def list_documents(self) -> list[IngestedDocument]:
        with self.lock:
            return list(self.documents.values())

    def delete_document(self, doc_id: str) -> int:
        with self.lock:
            if doc_id not in self.documents:
                return 0

            doc = self.documents[doc_id]
            del self.documents[doc_id]
            if doc.sha256 in self.documents_by_sha:
                del self.documents_by_sha[doc.sha256]

            # Remove chunks
            cids_to_del = [cid for cid, c in self.chunks.items() if c.doc_id == doc_id]
            for cid in cids_to_del:
                del self.chunks[cid]
                self.bm25_index.remove(cid)

            # Rebuild vector index
            self.dual_index.clear()
            if self.chunks:
                all_cids = list(self.chunks.keys())
                air_vecs = [self._embed(self.chunks[cid].content, "airgap") for cid in all_cids]
                cloud_vecs = [self._embed(self.chunks[cid].content, "cloud") for cid in all_cids]
                self.dual_index.add_airgap(all_cids, air_vecs)
                metas = [
                    {
                        "doc_name": self.chunks[cid].doc_name,
                        "category": self.chunks[cid].category,
                        "page_number": self.chunks[cid].page_number,
                        "start_line": self.chunks[cid].start_line,
                        "end_line": self.chunks[cid].end_line
                    }
                    for cid in all_cids
                ]
                self.dual_index.add_cloud(all_cids, cloud_vecs, metas)

            self.save()
            return len(cids_to_del)

    def update_document_category(self, doc_id: str, new_category: str) -> bool:
        valid_cat = new_category if new_category in {"CLINICAL", "FINANCIAL", "LEGAL", "DEFENSE", "GENERAL"} else "GENERAL"
        with self.lock:
            if doc_id not in self.documents:
                return False
            self.documents[doc_id].category = valid_cat  # type: ignore
            for c in self.chunks.values():
                if c.doc_id == doc_id:
                    c.category = valid_cat  # type: ignore

            if self.chunks:
                all_cids = list(self.chunks.keys())
                self.dual_index.clear()
                air_vecs = [self._embed(self.chunks[cid].content, "airgap") for cid in all_cids]
                cloud_vecs = [self._embed(self.chunks[cid].content, "cloud") for cid in all_cids]
                self.dual_index.add_airgap(all_cids, air_vecs)
                metas = [
                    {
                        "doc_name": self.chunks[cid].doc_name,
                        "category": self.chunks[cid].category,
                        "page_number": self.chunks[cid].page_number,
                        "start_line": self.chunks[cid].start_line,
                        "end_line": self.chunks[cid].end_line
                    }
                    for cid in all_cids
                ]
                self.dual_index.add_cloud(all_cids, cloud_vecs, metas)

            self.save()
            return True

    def clear_all(self) -> None:
        with self.lock:
            self.documents.clear()
            self.documents_by_sha.clear()
            self.chunks.clear()
            self.bm25_index.clear()
            self.dual_index.clear()
            self.save()

    def get_stats(self) -> dict:
        with self.lock:
            return {
                "document_count": len(self.documents),
                "chunk_count": len(self.chunks),
                "mode": self.settings.engine_mode,
                "airgap_embedding_model": self.settings.airgap_embedding_model,
                "airgap_embedding_dim": self.settings.airgap_embedding_dim,
                "cloud_embedding_model": self.settings.cloud_embedding_model,
                "cloud_embedding_dim": self.settings.cloud_embedding_dim,
                "index_healthy": self.index_healthy,
                "manifest_healthy": self.manifest_healthy
            }

    def save(self) -> None:
        with self.lock:
            ensure_dirs([self.settings.data_dir])
            # Save chunks
            atomic_write_pickle(self.settings.chunks_path, {
                "documents": self.documents,
                "documents_by_sha": self.documents_by_sha,
                "chunks": self.chunks
            })

            # Save Manifest
            sorted_cids = sorted(self.chunks.keys())
            c_hash = hashlib.sha256("".join(sorted_cids).encode("utf-8")).hexdigest()
            manifest = {
                "schema_version": "2.0",
                "embedding_model": self.settings.airgap_embedding_model,
                "embedding_dim": self.settings.airgap_embedding_dim,
                "document_count": len(self.documents),
                "chunk_count": len(self.chunks),
                "chunk_ids_sorted_hash": c_hash
            }
            atomic_write_json(self.settings.manifest_path, manifest)

    def load(self) -> None:
        with self.lock:
            chunks_data = read_pickle(self.settings.chunks_path)
            manifest = read_json(self.settings.manifest_path)

            if not chunks_data or not manifest:
                self.index_healthy = True
                self.manifest_healthy = True
                return

            self.documents = chunks_data.get("documents", {})
            self.documents_by_sha = chunks_data.get("documents_by_sha", {})
            self.chunks = chunks_data.get("chunks", {})

            # Verify manifest
            sorted_cids = sorted(self.chunks.keys())
            c_hash = hashlib.sha256("".join(sorted_cids).encode("utf-8")).hexdigest()

            is_valid = (
                manifest.get("document_count") == len(self.documents) and
                manifest.get("chunk_count") == len(self.chunks) and
                manifest.get("chunk_ids_sorted_hash") == c_hash
            )

            if not is_valid:
                logger.error("Manifest mismatch detected on startup. Resetting index.")
                self.audit_ledger.log_error("IndexIntegrityError", "Manifest does not match chunks index.")
                self.index_healthy = False
                self.manifest_healthy = False
                self.clear_all()
                return

            # Re-index into memory
            all_cids = list(self.chunks.keys())
            if all_cids:
                air_vecs = [self._embed(self.chunks[cid].content, "airgap") for cid in all_cids]
                cloud_vecs = [self._embed(self.chunks[cid].content, "cloud") for cid in all_cids]
                self.dual_index.clear()
                self.dual_index.add_airgap(all_cids, air_vecs)
                metas = [
                    {
                        "doc_name": self.chunks[cid].doc_name,
                        "category": self.chunks[cid].category,
                        "page_number": self.chunks[cid].page_number,
                        "start_line": self.chunks[cid].start_line,
                        "end_line": self.chunks[cid].end_line
                    }
                    for cid in all_cids
                ]
                self.dual_index.add_cloud(all_cids, cloud_vecs, metas)
                bm25_items = [(cid, self.chunks[cid].content) for cid in all_cids]
                self.bm25_index.add_batch(bm25_items)

            self.index_healthy = True
            self.manifest_healthy = True
