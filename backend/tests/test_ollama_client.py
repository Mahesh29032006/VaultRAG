import pytest
from backend.errors import LLMUnavailableError
from backend.fallback_synth import generate as fallback_generate
from backend.models import RetrievedChunk
from backend.ollama_client import OllamaClient


def test_ollama_client_health_check_offline():
    client = OllamaClient(base_url="http://127.0.0.1:59999")
    # Non-existent port should return False without crashing
    assert client.health_check(timeout_s=0.2) is False


def test_ollama_client_stream_chat_connection_error_raises_llm_unavailable():
    import asyncio
    async def _test():
        client = OllamaClient(base_url="http://127.0.0.1:59999")
        async for _ in client.stream_chat("sys", "user"):
            pass

    with pytest.raises(LLMUnavailableError):
        asyncio.run(_test())


def test_fallback_synth_empty_chunks_returns_refusal():
    ans = fallback_generate("Any question", [])
    assert "do not contain information" in ans


def test_fallback_synth_with_chunks_generates_citations():
    chunk = RetrievedChunk(
        chunk_id="c1",
        doc_name="clinical_note.txt",
        category="CLINICAL",
        page_number=1,
        start_line=1,
        end_line=3,
        text="Patient prescribed Torsemide 20 mg oral daily for heart failure.",
        similarity_score=0.95,
        bm25_score=4.2,
        rrf_score=0.032,
        citation_label="Doc: clinical_note.txt, Page 1, Line 1-3"
    )
    ans = fallback_generate("What is the Torsemide dosage?", [chunk])
    assert "20 mg" in ans
    assert "[Doc: clinical_note.txt, Page 1, Line 1-3]" in ans
    assert "Note: Local LLM unavailable" in ans


def test_gemini_client_missing_key_raises_error():
    from backend.gemini_client import GeminiClient
    client = GeminiClient(api_key="", model="gemini-2.5-flash")
    assert client.health_check() is False
    import asyncio
    with pytest.raises(LLMUnavailableError, match="not set"):
        asyncio.run(client.generate("sys", "user"))
