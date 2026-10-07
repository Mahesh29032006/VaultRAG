from backend.telemetry import TelemetryEngine


def test_telemetry_llama3_q4_memory_estimate_range():
    calc = TelemetryEngine.calculate_memory(
        model_id="llama3:8b",
        quant_type="Q4_K_M",
        context_length=4096,
        batch_size=1
    )
    assert 4.5 <= calc.total_memory_gib_estimate <= 6.5
    assert calc.fits_on_16gib is True
    assert calc.fits_on_8gib is True


def test_telemetry_fp16_vs_q4_compression_ratio():
    fp16 = TelemetryEngine.calculate_memory(model_id="llama3:8b", quant_type="FP16")
    q4 = TelemetryEngine.calculate_memory(model_id="llama3:8b", quant_type="Q4_K_M")
    ratio = fp16.weight_memory_gib / q4.weight_memory_gib
    assert 3.0 <= ratio <= 4.0


def test_telemetry_batch_size_kv_cache_scaling():
    b1 = TelemetryEngine.calculate_memory(model_id="llama3:8b", batch_size=1, context_length=4096)
    b2 = TelemetryEngine.calculate_memory(model_id="llama3:8b", batch_size=2, context_length=4096)
    assert round(b2.kv_cache_memory_gib, 2) == round(b1.kv_cache_memory_gib * 2, 2)


def test_telemetry_fits_on_flags():
    small = TelemetryEngine.calculate_memory(model_id="phi3:mini", quant_type="Q4_K_M", context_length=2048)
    assert small.fits_on_8gib is True
    assert small.fits_on_16gib is True


def test_telemetry_host_stats_structure():
    stats = TelemetryEngine.get_host_telemetry()
    assert "platform" in stats
    assert "arch" in stats
    assert "cpu_count" in stats
    assert "total_memory_gib" in stats
    assert stats["total_memory_gib"] > 0
