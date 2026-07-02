from __future__ import annotations

import threading
from pathlib import Path

from django.conf import settings
import torch
from ultralytics import YOLO


class ModelRegistry:
    """Process-wide singleton — all SessionManagers share the same loaded YOLO weights.

    GPU inference is serialised via _infer_lock so concurrent threads don't OOM
    during CUDA kernel JIT compilation or activation allocation.
    """

    VIRTUAL_MODELS = {"danger_zone", "work_zone", "fall_detection", "running_detection", "inactivity_detection"}

    # Class-level shared state
    _loaded_models: dict = {}
    _lock = threading.Lock()
    _infer_lock = threading.Lock()   # one GPU inference at a time
    _device: str | None = None
    _use_half: bool = False

    def __init__(self):
        if ModelRegistry._device is None:
            with ModelRegistry._lock:
                if ModelRegistry._device is None:
                    ModelRegistry._device = "cuda:0" if torch.cuda.is_available() else "cpu"
                    ModelRegistry._use_half = (
                        ModelRegistry._device.startswith("cuda") and settings.SAFEFACTORY_USE_HALF_PRECISION
                    )

    @property
    def device(self) -> str:
        return ModelRegistry._device or "cpu"

    @property
    def use_half(self) -> bool:
        return ModelRegistry._use_half

    def get_model(self, model_key: str) -> YOLO:
        if model_key in self.VIRTUAL_MODELS:
            return None
        if model_key not in ModelRegistry._loaded_models:
            with ModelRegistry._lock:
                if model_key not in ModelRegistry._loaded_models:
                    model_path = Path(settings.SAFEFACTORY_MODEL_PATHS[model_key])
                    if not model_path.exists():
                        raise FileNotFoundError(
                            f"Model weights not found for {model_key}: {model_path}"
                        )
                    # Loading + first predict() call touches CUDA (alloc, module JIT, fuse).
                    # Serialise with _infer_lock too, or a concurrent load from another
                    # camera-slot thread can race the GPU context and crash the driver.
                    with ModelRegistry._infer_lock:
                        model = YOLO(str(model_path))
                        model.to(self.device)
                    ModelRegistry._loaded_models[model_key] = model
        return ModelRegistry._loaded_models[model_key]

    def get_public_model_paths(self):
        return {key: str(path) for key, path in settings.SAFEFACTORY_MODEL_PATHS.items()}

    def runtime_info(self):
        return {
            "device": self.device,
            "gpu_enabled": self.device.startswith("cuda"),
            "half_precision": self.use_half,
        }
