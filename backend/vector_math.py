import math
from typing import Any, Literal
from pathlib import Path


def _validate_vector(v: list[float]) -> None:
    for x in v:
        if math.isnan(x) or math.isinf(x):
            raise ValueError("Vector contains NaN or Inf values")


def dot_product(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"Vector length mismatch: {len(a)} != {len(b)}")
    _validate_vector(a)
    _validate_vector(b)
    return sum(x * y for x, y in zip(a, b))


def l2_norm(v: list[float]) -> float:
    _validate_vector(v)
    return math.sqrt(sum(x * x for x in v))


def normalize(v: list[float]) -> list[float]:
    _validate_vector(v)
    norm = l2_norm(v)
    if norm == 0.0 or math.isclose(norm, 0.0):
        return [0.0] * len(v)
    return [x / norm for x in v]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"Vector length mismatch: {len(a)} != {len(b)}")
    _validate_vector(a)
    _validate_vector(b)
    norm_a = l2_norm(a)
    norm_b = l2_norm(b)
    if math.isclose(norm_a, 0.0) or math.isclose(norm_b, 0.0):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    raw_cos = dot / (norm_a * norm_b)
    # Clamp to [-1.0, 1.0] to guard against floating point inaccuracies
    return max(-1.0, min(1.0, raw_cos))


def cosine_distance(a: list[float], b: list[float]) -> float:
    return 1.0 - cosine_similarity(a, b)


def angular_degrees(a: list[float], b: list[float]) -> float:
    sim = cosine_similarity(a, b)
    rad = math.acos(sim)
    return math.degrees(rad)


class LocalIndexFlatIP:
    """Pure-Python inner-product vector index for air-gap fallback."""
    def __init__(self, dim: int):
        self.dim = dim
        self.chunk_ids: list[str] = []
        self.vectors: list[list[float]] = []

    def add(self, chunk_ids: list[str], vectors: list[list[float]]) -> None:
        for cid, vec in zip(chunk_ids, vectors):
            if len(vec) != self.dim:
                raise ValueError(f"Expected dim {self.dim}, got {len(vec)}")
            _validate_vector(vec)
            norm_vec = normalize(vec)
            self.chunk_ids.append(cid)
            self.vectors.append(norm_vec)

    def search(self, query_vector: list[float], top_k: int = 20) -> list[tuple[str, float]]:
        if not self.chunk_ids:
            return []
        if len(query_vector) != self.dim:
            raise ValueError(f"Expected dim {self.dim}, got {len(query_vector)}")
        norm_q = normalize(query_vector)
        scored = []
        for cid, vec in zip(self.chunk_ids, self.vectors):
            sim = max(-1.0, min(1.0, sum(q * v for q, v in zip(norm_q, vec))))
            scored.append((cid, float(sim)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def remove(self, chunk_id: str) -> None:
        indices_to_remove = [i for i, cid in enumerate(self.chunk_ids) if cid == chunk_id]
        for idx in reversed(indices_to_remove):
            del self.chunk_ids[idx]
            del self.vectors[idx]

    def clear(self) -> None:
        self.chunk_ids.clear()
        self.vectors.clear()

    @property
    def total_count(self) -> int:
        return len(self.chunk_ids)


class InMemoryCloudIndex:
    """In-memory 768-D cloud vector store fallback."""
    def __init__(self, dim: int):
        self.dim = dim
        self.chunk_ids: list[str] = []
        self.vectors: list[list[float]] = []
        self.metadatas: list[dict] = []

    def add(self, chunk_ids: list[str], vectors: list[list[float]], metadatas: list[dict] | None = None) -> None:
        metas = metadatas or [{} for _ in chunk_ids]
        for cid, vec, meta in zip(chunk_ids, vectors, metas):
            if len(vec) != self.dim:
                raise ValueError(f"Expected dim {self.dim}, got {len(vec)}")
            _validate_vector(vec)
            self.chunk_ids.append(cid)
            self.vectors.append(normalize(vec))
            self.metadatas.append(meta)

    def search(self, query_vector: list[float], top_k: int = 20) -> list[tuple[str, float]]:
        if not self.chunk_ids:
            return []
        if len(query_vector) != self.dim:
            raise ValueError(f"Expected dim {self.dim}, got {len(query_vector)}")
        norm_q = normalize(query_vector)
        scored = []
        for cid, vec in zip(self.chunk_ids, self.vectors):
            sim = max(-1.0, min(1.0, sum(q * v for q, v in zip(norm_q, vec))))
            scored.append((cid, float(sim)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def clear(self) -> None:
        self.chunk_ids.clear()
        self.vectors.clear()
        self.metadatas.clear()


class DualIndex:
    """Manages simultaneous 384-D air-gap and 768-D cloud indices."""

    def __init__(
        self,
        airgap_dim: int = 384,
        cloud_dim: int = 768,
        faiss_index_path: str | None = None,
        chroma_dir: str | None = None
    ):
        self.airgap_dim = airgap_dim
        self.cloud_dim = cloud_dim
        self.faiss_index_path = faiss_index_path
        self.chroma_dir = chroma_dir

        self.use_native_faiss = False
        self.airgap_index: Any = None
        self.airgap_ids: list[str] = []

        try:
            import faiss
            self.airgap_index = faiss.IndexFlatIP(airgap_dim)
            self.use_native_faiss = True
        except Exception:
            self.airgap_index = LocalIndexFlatIP(airgap_dim)
            self.use_native_faiss = False

        self.use_chromadb = False
        self.cloud_index: Any = None
        try:
            if chroma_dir:
                import chromadb
                client = chromadb.PersistentClient(path=chroma_dir)
                self.cloud_index = client.get_or_create_collection(
                    name="sovereign_rag_docs",
                    metadata={"hnsw:space": "cosine"}
                )
                self.use_chromadb = True
            else:
                self.cloud_index = InMemoryCloudIndex(cloud_dim)
        except Exception:
            self.cloud_index = InMemoryCloudIndex(cloud_dim)
            self.use_chromadb = False

    def add_airgap(self, chunk_ids: list[str], vectors: list[list[float]]) -> None:
        if not chunk_ids:
            return
        if self.use_native_faiss:
            import numpy as np
            norm_vecs = [normalize(v) for v in vectors]
            arr = np.array(norm_vecs, dtype=np.float32)
            self.airgap_index.add(arr)
            self.airgap_ids.extend(chunk_ids)
        else:
            self.airgap_index.add(chunk_ids, vectors)

    def add_cloud(self, chunk_ids: list[str], vectors: list[list[float]], metadatas: list[dict]) -> None:
        if not chunk_ids:
            return
        if self.use_chromadb:
            norm_vecs = [normalize(v) for v in vectors]
            # Ensure metadatas don't have None or complex types
            clean_metas = [{k: str(v) for k, v in m.items()} for m in metadatas]
            try:
                self.cloud_index.add(
                    ids=chunk_ids,
                    embeddings=norm_vecs,
                    metadatas=clean_metas
                )
            except Exception:
                # If collection was invalidated, deleted, or UUID stale, re-acquire collection or fallback
                try:
                    import chromadb
                    client = chromadb.PersistentClient(path=self.chroma_dir)
                    self.cloud_index = client.get_or_create_collection(
                        name="sovereign_rag_docs",
                        metadata={"hnsw:space": "cosine"}
                    )
                    self.cloud_index.add(
                        ids=chunk_ids,
                        embeddings=norm_vecs,
                        metadatas=clean_metas
                    )
                except Exception:
                    self.use_chromadb = False
                    self.cloud_index = InMemoryCloudIndex(self.cloud_dim)
                    self.cloud_index.add(chunk_ids, vectors, metadatas)
        else:
            self.cloud_index.add(chunk_ids, vectors, metadatas)

    def search_airgap(self, query_vector: list[float], top_k: int = 20) -> list[tuple[str, float]]:
        if self.use_native_faiss:
            if not self.airgap_ids or self.airgap_index.ntotal == 0:
                return []
            import numpy as np
            norm_q = np.array([normalize(query_vector)], dtype=np.float32)
            k = min(top_k, self.airgap_index.ntotal)
            distances, indices = self.airgap_index.search(norm_q, k)
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if 0 <= idx < len(self.airgap_ids):
                    results.append((self.airgap_ids[idx], float(dist)))
            return results
        else:
            return self.airgap_index.search(query_vector, top_k=top_k)

    def search_cloud(self, query_vector: list[float], top_k: int = 20, mode: str = "cloud") -> list[tuple[str, float]]:
        # Rule: Never query a cloud index while mode == "airgap"
        if mode == "airgap":
            raise ValueError("Policy violation: Never query a cloud index while mode == 'airgap'")

        if self.use_chromadb:
            try:
                norm_q = normalize(query_vector)
                res = self.cloud_index.query(query_embeddings=[norm_q], n_results=top_k)
                ids = res.get("ids", [[]])[0]
                distances = res.get("distances", [[]])[0]
                # Chroma returns cosine distance (1 - cos_sim)
                return [(cid, float(1.0 - d)) for cid, d in zip(ids, distances)]
            except Exception:
                return []
        else:
            return self.cloud_index.search(query_vector, top_k=top_k)

    def clear(self) -> None:
        if self.use_native_faiss:
            import faiss
            self.airgap_index = faiss.IndexFlatIP(self.airgap_dim)
            self.airgap_ids.clear()
        else:
            self.airgap_index.clear()

        if self.use_chromadb and self.chroma_dir:
            try:
                import chromadb
                client = chromadb.PersistentClient(path=self.chroma_dir)
                client.delete_collection(name="sovereign_rag_docs")
                self.cloud_index = client.get_or_create_collection(
                    name="sovereign_rag_docs",
                    metadata={"hnsw:space": "cosine"}
                )
            except Exception:
                self.cloud_index = InMemoryCloudIndex(self.cloud_dim)
        elif self.cloud_index:
            self.cloud_index.clear()
