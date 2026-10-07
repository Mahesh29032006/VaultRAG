import pytest
from pathlib import Path
from backend.config import Settings


def test_config_default_values_valid(tmp_settings: Settings):
    assert tmp_settings.host == "127.0.0.1"
    assert tmp_settings.port == 8093
    assert tmp_settings.engine_mode == "airgap"
    assert tmp_settings.airgap_embedding_dim == 384
    assert tmp_settings.cloud_embedding_dim == 768


def test_config_engine_mode_validation():
    with pytest.raises(ValueError, match="engine_mode"):
        Settings(engine_mode="invalid_mode")  # type: ignore


def test_config_port_range_validation():
    with pytest.raises(ValueError, match="port"):
        Settings(port=80)
    with pytest.raises(ValueError, match="port"):
        Settings(port=70000)


def test_config_bm25_parameter_validation():
    with pytest.raises(ValueError, match="bm25_k1"):
        Settings(bm25_k1=-0.5)
    with pytest.raises(ValueError, match="bm25_b"):
        Settings(bm25_b=1.5)


def test_config_chunk_overlap_validation():
    with pytest.raises(ValueError, match="chunk_overlap"):
        Settings(chunk_size=400, chunk_overlap=400)


def test_config_save_and_load_disk(tmp_path: Path):
    cfg_file = tmp_path / "cfg.json"
    s1 = Settings(config_path=str(cfg_file), top_k=7, engine_mode="airgap")
    s1.save_to_disk()
    assert cfg_file.exists()

    s2 = Settings(config_path=str(cfg_file))
    s2.load_from_disk()
    assert s2.top_k == 7


def test_config_persist_env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    cfg_file = tmp_path / "cfg.json"
    s = Settings(config_path=str(cfg_file), gemini_api_key="test-key-12345", engine_mode="cloud")
    s.persist_env_file()

    env_path = tmp_path / ".env"
    assert env_path.exists()
    content = env_path.read_text(encoding="utf-8")
    assert "GEMINI_API_KEY=test-key-12345" in content
    assert "ENGINE_MODE=cloud" in content

