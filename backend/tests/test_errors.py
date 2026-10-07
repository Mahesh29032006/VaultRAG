import pytest
from fastapi.testclient import TestClient
from backend.errors import (
    AuditIntegrityError,
    DocumentParseError,
    EmptyDocumentError,
    FileTooLargeError,
    LLMUnavailableError,
    SensitiveDataCloudBlockedError,
    SovereignRAGError,
    UnsupportedFileTypeError,
)
from backend.main import app


def test_errors_hierarchy():
    err = EmptyDocumentError("Empty text")
    assert isinstance(err, SovereignRAGError)
    assert isinstance(err, Exception)
    assert err.message == "Empty text"


def test_errors_api_empty_query_validation():
    client = TestClient(app)
    # Empty query string
    res = client.post("/api/rag/query", json={"query": ""})
    assert res.status_code == 422


def test_errors_api_whitespace_query_validation():
    client = TestClient(app)
    res = client.post("/api/rag/query", json={"query": "     "})
    assert res.status_code == 400


def test_errors_api_null_byte_query():
    client = TestClient(app)
    res = client.post("/api/rag/query", json={"query": "test\x00query"})
    assert res.status_code == 400


def test_errors_api_unsupported_file_upload():
    client = TestClient(app)
    files = {"file": ("malicious.exe", b"MZbinary", "application/octet-stream")}
    res = client.post("/api/rag/ingest", files=files, data={"title": "Malware"})
    assert res.status_code == 415


def test_errors_api_empty_file_upload():
    client = TestClient(app)
    files = {"file": ("empty.txt", b"", "text/plain")}
    res = client.post("/api/rag/ingest", files=files, data={"title": "Empty"})
    assert res.status_code == 422
