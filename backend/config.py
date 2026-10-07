import json
import os
from pathlib import Path
from typing import Any, Literal
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    host: str = "127.0.0.1"
    port: int = 8093
    frontend_origin: str = "http://127.0.0.1:3000"

    data_dir: str = "data"
    faiss_index_path: str = "data/faiss.index"
    chunks_path: str = "data/chunks.pkl"
    manifest_path: str = "data/manifest.json"
    chroma_dir: str = "data/chromadb"
    audit_ledger_path: str = "data/audit_ledger.json"
    uploads_dir: str = "data/uploads"
    config_path: str = "data/config.json"

    airgap_embedding_model: str = "all-MiniLM-L6-v2"
    airgap_embedding_dim: int = 384
    cloud_embedding_model: str = "text-embedding-004"
    cloud_embedding_dim: int = 768

    top_k: int = 4
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    rrf_k: int = 60

    chunk_size: int = 450
    chunk_overlap: int = 60

    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:1.5b"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 1024

    engine_mode: Literal["airgap", "cloud"] = "airgap"

    max_upload_bytes: int = 50 * 1024 * 1024
    max_extracted_chars: int = 5_000_000
    max_chunks_per_doc: int = 10_000
    max_query_chars: int = 4000

    @field_validator("engine_mode")
    @classmethod
    def validate_engine_mode(cls, v: str) -> str:
        if v not in {"airgap", "cloud"}:
            raise ValueError("engine_mode must be 'airgap' or 'cloud'")
        return v

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not (1024 <= v <= 65535):
            raise ValueError("port must be between 1024 and 65535")
        return v

    @field_validator("bm25_k1")
    @classmethod
    def validate_bm25_k1(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("bm25_k1 must be > 0")
        return v

    @field_validator("bm25_b")
    @classmethod
    def validate_bm25_b(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("bm25_b must be between 0 and 1")
        return v

    @model_validator(mode="after")
    def validate_chunk_overlap(self) -> "Settings":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be strictly less than chunk_size")
        return self

    def save_to_disk(self) -> None:
        target_path = Path(self.config_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = target_path.with_suffix(".tmp")
        dump_data = self.model_dump()
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(dump_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target_path)
        try:
            os.chmod(target_path, 0o600)
        except OSError:
            pass
        self.persist_env_file()

    def persist_env_file(self) -> None:
        """Atomically persist configuration to .env with restrictive permissions."""
        env_path = Path(".env")
        lines: list[str] = []
        if env_path.is_file():
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        managed_keys = {
            "HOST": str(self.host),
            "PORT": str(self.port),
            "FRONTEND_ORIGIN": str(self.frontend_origin),
            "DATA_DIR": str(self.data_dir),
            "ENGINE_MODE": str(self.engine_mode),
            "OLLAMA_URL": str(self.ollama_url),
            "OLLAMA_MODEL": str(self.ollama_model),
            "GEMINI_API_KEY": str(self.gemini_api_key),
            "GEMINI_MODEL": str(self.gemini_model),
            "TOP_K": str(self.top_k),
            "CHUNK_SIZE": str(self.chunk_size),
            "CHUNK_OVERLAP": str(self.chunk_overlap),
        }

        updated_keys = set()
        new_lines: list[str] = []
        for line in lines:
            stripped = line.strip()
            if "=" in stripped and not stripped.startswith("#"):
                key, _ = stripped.split("=", 1)
                key_norm = key.strip().upper()
                if key_norm in managed_keys:
                    new_lines.append(f"{key_norm}={managed_keys[key_norm]}\n")
                    updated_keys.add(key_norm)
                    continue
            new_lines.append(line)

        for k, v in managed_keys.items():
            if k not in updated_keys:
                new_lines.append(f"{k}={v}\n")

        tmp_env = env_path.with_suffix(".tmp")
        with open(tmp_env, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_env, env_path)
        try:
            os.chmod(env_path, 0o600)
        except OSError:
            pass

    def load_from_disk(self) -> None:
        target_path = Path(self.config_path)
        if target_path.is_file():
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if hasattr(self, k):
                    setattr(self, k, v)

