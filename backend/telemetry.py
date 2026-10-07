import os
import platform
import psutil
from backend.models import MemoryCalculation

MODEL_SPECS = {
    "llama3:8b": {"layers": 32, "heads": 32, "kv_heads": 8, "hidden_dim": 4096, "params_b": 8.03},
    "phi3:mini": {"layers": 32, "heads": 32, "kv_heads": 32, "hidden_dim": 3072, "params_b": 3.82},
    "mistral:7b": {"layers": 32, "heads": 32, "kv_heads": 8, "hidden_dim": 4096, "params_b": 7.25},
    "qwen2.5:7b": {"layers": 28, "heads": 28, "kv_heads": 4, "hidden_dim": 3584, "params_b": 7.61},
}

QUANT_PROFILES = {
    "FP16": {"bytes_per_weight_approx": 2.00, "accuracy_retention_approx": 100.0, "tps_estimate": 13.5, "ttft_ms_estimate": 380},
    "Q8_0": {"bytes_per_weight_approx": 1.06, "accuracy_retention_approx": 99.7, "tps_estimate": 26.2, "ttft_ms_estimate": 210},
    "Q4_K_M": {"bytes_per_weight_approx": 0.56, "accuracy_retention_approx": 98.4, "tps_estimate": 43.8, "ttft_ms_estimate": 115},
    "Q2_K": {"bytes_per_weight_approx": 0.33, "accuracy_retention_approx": 83.2, "tps_estimate": 56.4, "ttft_ms_estimate": 85},
}


class TelemetryEngine:
    @staticmethod
    def calculate_memory(
        model_id: str = "llama3:8b",
        quant_type: str = "Q4_K_M",
        context_length: int = 4096,
        batch_size: int = 1
    ) -> MemoryCalculation:
        if model_id not in MODEL_SPECS:
            model_id = "llama3:8b"
        if quant_type not in QUANT_PROFILES:
            quant_type = "Q4_K_M"

        spec = MODEL_SPECS[model_id]
        prof = QUANT_PROFILES[quant_type]

        # Weights in GiB (1024^3)
        weight_bytes = spec["params_b"] * 1e9 * prof["bytes_per_weight_approx"]
        weight_gib = weight_bytes / (1024 ** 3)

        # KV cache in GiB (2 bytes per FP16 element for K and V)
        head_dim = spec["hidden_dim"] // spec["heads"]
        kv_bytes = 2 * spec["layers"] * spec["kv_heads"] * head_dim * context_length * 2 * batch_size
        kv_gib = kv_bytes / (1024 ** 3)

        # Activation buffer estimate (heuristic 12% of weight size)
        act_gib = weight_gib * 0.12

        total_gib = weight_gib + kv_gib + act_gib

        fits_on_16gib = total_gib < 13.5
        fits_on_8gib = total_gib < 6.8

        recommended_hw = (
            "Any 8 GiB or 16 GiB Mac" if total_gib < 6.5
            else "16 GiB Mac" if total_gib < 13.5
            else "32 GiB+ Mac or RTX 3090+"
        )

        return MemoryCalculation(
            model_id=model_id,
            quant_type=quant_type,
            context_length=context_length,
            batch_size=batch_size,
            weight_memory_gib=round(weight_gib, 2),
            kv_cache_memory_gib=round(kv_gib, 2),
            activation_memory_gib_estimate=round(act_gib, 2),
            total_memory_gib_estimate=round(total_gib, 2),
            fits_on_16gib=fits_on_16gib,
            fits_on_8gib=fits_on_8gib,
            recommended_hardware=recommended_hw,
            notes="Values are heuristic estimates in GiB (1024^3). Actual usage depends on runtime and hardware."
        )

    @staticmethod
    def get_host_telemetry() -> dict:
        vmem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        gib_factor = 1024 ** 3
        tot_mem = round(vmem.total / gib_factor, 2)
        used_mem = round(vmem.used / gib_factor, 2)
        free_mem = round(vmem.available / gib_factor, 2)
        tot_disk = round(disk.total / gib_factor, 2)
        used_disk = round(disk.used / gib_factor, 2)
        free_disk = round(disk.free / gib_factor, 2)
        cpu_pct = psutil.cpu_percent(interval=None)

        return {
            "platform": f"{platform.system()} ({platform.machine()})",
            "arch": platform.machine(),
            "cpu_count": os.cpu_count() or 1,
            "cpu_model": platform.processor() or platform.machine(),
            "cpu_percent": cpu_pct,
            "total_memory_gib": tot_mem,
            "free_memory_gib": free_mem,
            "used_memory_gib": used_mem,
            "memory_usage_percent": vmem.percent,
            # Aliases for frontend flexibility
            "memory_total_gib": tot_mem,
            "memory_used_gib": used_mem,
            "memory_available_gib": free_mem,
            "memory_percent": vmem.percent,
            "disk_total_gib": tot_disk,
            "disk_used_gib": used_disk,
            "disk_free_gib": free_disk,
            "disk_percent": disk.percent,
        }
