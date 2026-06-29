from __future__ import annotations

from pathlib import Path

from django.conf import settings
import torch
from ultralytics import YOLO


class ModelRegistry:
    VIRTUAL_MODELS = {"danger_zone", "work_zone"}

    def __init__(self):
        self._loaded_models = {}
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.use_half = self.device.startswith("cuda")

    def get_model(self, model_key):
        if model_key in self.VIRTUAL_MODELS:
            return None
        if model_key not in self._loaded_models:
            model_path = Path(settings.SAFEFACTORY_MODEL_PATHS[model_key])
            if not model_path.exists():
                raise FileNotFoundError(f"Model weights not found for {model_key}: {model_path}")
            model = YOLO(str(model_path))
            model.to(self.device)
            self._loaded_models[model_key] = model
        return self._loaded_models[model_key]

    def get_public_model_paths(self):
        return {key: str(path) for key, path in settings.SAFEFACTORY_MODEL_PATHS.items()}

    def runtime_info(self):
        return {
            "device": self.device,
            "gpu_enabled": self.device.startswith("cuda"),
            "half_precision": self.use_half,
        }
