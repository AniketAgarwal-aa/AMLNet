"""Hardware-aware compute device selection and resource monitoring for Apple Silicon / Mac."""
import os
import sys
import platform
import resource
import logging
import torch

logger = logging.getLogger("amlnet.device")

def get_process_memory_mb() -> float:
    """Return the peak resident set size (RSS) in MB for the current process."""
    # On macOS, ru_maxrss is in bytes; on Linux, in kilobytes.
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == "Darwin":
        return usage / (1024.0 * 1024.0)
    return usage / 1024.0

def get_device(prefer_mps: bool = True) -> torch.device:
    """
    Select the optimal available device:
    1. MPS if on macOS Apple Silicon and compatible
    2. CPU fallback for incompatible operations or if MPS is unavailable
    3. CUDA if running on NVIDIA hardware (never forced on Apple Silicon)
    """
    if prefer_mps and platform.system() == "Darwin":
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() and torch.backends.mps.is_built():
            try:
                # Test basic allocation
                test_tensor = torch.zeros(1, device="mps")
                del test_tensor
                return torch.device("mps")
            except Exception as e:
                logger.warning(f"MPS available but failed test tensor allocation: {e}. Falling back to CPU.")
                return torch.device("cpu")
        return torch.device("cpu")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")

class ResourceProfile:
    LIGHT = "light"
    BALANCED = "balanced"
    FULL = "full"

    PROFILES = {
        LIGHT: {
            "name": "Light",
            "description": "Fast local development, tests, and small graph subsets. Minimal memory (<1 GB).",
            "max_transactions": 25_000,
            "max_accounts": 5_000,
            "max_scan_rows": 2_000_000,
            "batch_size": 256,
            "epochs": 40,
            "target_memory_mb": 1024,
            "num_workers": 0,
        },
        BALANCED: {
            "name": "Balanced",
            "description": "Meaningful research experiments on Apple Silicon 8GB unified memory. (~2-3 GB budget).",
            "max_transactions": 250_000,
            "max_accounts": 25_000,
            "max_scan_rows": 5_000_000,
            "batch_size": 512,
            "epochs": 80,
            "target_memory_mb": 2500,
            "num_workers": 0,
        },
        FULL: {
            "name": "Full",
            "description": "Process complete datasets at maximum feasible scale using bounded streaming & mini-batching.",
            "max_transactions": None,  # Complete dataset
            "max_accounts": None,
            "max_scan_rows": None,
            "batch_size": 1024,
            "epochs": 100,
            "target_memory_mb": 3500,
            "num_workers": 0,
        }
    }

    @classmethod
    def get(cls, profile_name: str = "balanced") -> dict:
        return cls.PROFILES.get(profile_name.lower(), cls.PROFILES[cls.BALANCED])
