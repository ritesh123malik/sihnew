"""Central registry for all ML models. Load once, reuse everywhere."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_CONFIGS = {
    "default": {"path": "models/best.pt", "type": "yolo"},
    "100khz": {"path": "models/yolov8s_100khz.pt", "type": "yolo"},
    "400khz": {"path": "models/yolov8s_400khz.pt", "type": "yolo"},
    "900khz": {"path": "models/yolov8s_900khz.pt", "type": "yolo"},
}


def _resolve_model_cfg_path(cfg_path: str) -> Path | None:
    p = Path(cfg_path)
    if p.exists():
        return p
    for candidate in [
        Path("model/best_yolo11s.pt"),
        Path("model/best.pt"),
        Path("backend/best.pt"),
        Path("best.pt"),
    ]:
        if candidate.exists():
            return candidate
    return None


class ModelManager:
    def __init__(self) -> None:
        self._models: dict[str, Any] = {}

    def get(self, name: str = "default") -> Any | None:
        if name in self._models:
            return self._models[name]

        cfg = _CONFIGS.get(name) or _CONFIGS.get("default")
        if not cfg:
            return None

        resolved = _resolve_model_cfg_path(cfg["path"])
        if resolved is None:
            return None

        # Check if the exact resolved weights are already loaded under another key to save RAM
        resolved_key = str(resolved.resolve())
        for existing_name, existing_model in self._models.items():
            existing_cfg = _CONFIGS.get(existing_name)
            if existing_cfg:
                existing_res = _resolve_model_cfg_path(existing_cfg["path"])
                if existing_res and str(existing_res.resolve()) == resolved_key:
                    self._models[name] = existing_model
                    return existing_model

        try:
            from ultralytics import YOLO

            model = YOLO(str(resolved))
            self._models[name] = model
            logger.info("✅ Loaded model on-demand: %s (%s)", name, resolved)
            return model
        except Exception as e:
            logger.warning("⚠️  Failed to load model %s: %s", name, e)
            return None

    def reload(self, name: str) -> bool:
        cfg = _CONFIGS.get(name)
        if not cfg:
            return False
        resolved = _resolve_model_cfg_path(cfg["path"])
        if resolved is None:
            return False
        try:
            from ultralytics import YOLO

            self._models[name] = YOLO(str(resolved))
            logger.info(f"🔄 Reloaded model: {name}")
            return True
        except Exception as e:
            logger.error(f"❌ Reload failed for model {name}: {e}")
            return False

    def list(self) -> dict[str, Any]:
        return {
            name: {
                "loaded": name in self._models,
                "available": _resolve_model_cfg_path(cfg["path"]) is not None,
                **cfg,
            }
            for name, cfg in _CONFIGS.items()
        }


model_manager = ModelManager()
