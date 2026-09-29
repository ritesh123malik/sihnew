"""YOLOv8 sonar debris detector trained in Colab (sih2026_yolov8s_marine_debris)."""

from __future__ import annotations

import io
import logging
from pathlib import Path

from app.schemas.ml import BBox, Detection, ModelMetadata, PredictionResult, PreprocessedInput
from app.services.model_service import ModelService

logger = logging.getLogger(__name__)

_DEFAULT_NAMES = {
    0: "shipwreck",
    1: "aircraft",
    2: "submarine_pipeline",
    3: "ghost_net",
    4: "mine_munitions",
}

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_PROJECT_DIR = _BACKEND_DIR
_REPO_ROOT = _BACKEND_DIR.parent if _BACKEND_DIR.name == "backend" else _BACKEND_DIR

_CANDIDATE_WEIGHTS = [
    _REPO_ROOT / "model" / "best_yolo11s.pt",
    _BACKEND_DIR / "model" / "best_yolo11s.pt",
    _BACKEND_DIR / "best.pt",
    _REPO_ROOT / "best.pt",
    _BACKEND_DIR / "model" / "best.pt",
    _PROJECT_DIR / "model" / "best.pt",
    _REPO_ROOT / "model" / "best.pt",
    _REPO_ROOT / "weights" / "best_werb_dgrm_sadh.pt",
    _BACKEND_DIR / "weights" / "best_werb_dgrm_sadh.pt",
    _BACKEND_DIR / "yolov8s.pt",
    _REPO_ROOT / "yolov8s.pt",
]


_INFER_SIZES = (640, 960)
_MODEL_CONF = 0.12
_NMS_IOU = 0.45

# Load per-class optimal thresholds
_PER_CLASS_THRESHOLDS: dict[str, float] = {}
for _t_path in [
    _BACKEND_DIR / "app" / "configs" / "per_class_thresholds.csv",
    _REPO_ROOT / "configs" / "per_class_thresholds.csv",
    _BACKEND_DIR / "configs" / "per_class_thresholds.csv",
    _REPO_ROOT / "model" / "per_class_thresholds.csv",
    _BACKEND_DIR / "model" / "per_class_thresholds.csv",
]:
    if _t_path.is_file():
        try:
            with open(_t_path, mode="r", encoding="utf-8") as _f:
                for line in _f:
                    parts = line.strip().split(",")
                    if len(parts) == 2:
                        try:
                            _PER_CLASS_THRESHOLDS[parts[0].strip().lower()] = float(parts[1].strip())
                        except ValueError:
                            pass
            if _PER_CLASS_THRESHOLDS:
                break
        except Exception:
            pass


def get_class_threshold(class_name: str, default: float = _MODEL_CONF) -> float:
    """Get per-class confidence threshold with fallback."""
    if not class_name:
        return default
    normalized = class_name.lower().replace(" ", "_").strip()
    return _PER_CLASS_THRESHOLDS.get(normalized, _PER_CLASS_THRESHOLDS.get(class_name.lower(), default))


def _pretty_label(name: str) -> str:
    return name.replace("_", " ").strip().title()


def resolve_model_path(configured: str = "") -> Path:
    import os
    env_path = os.environ.get("MODEL_PATH", "").strip()
    check_paths = [configured, env_path]
    for cp in check_paths:
        if cp:
            p = Path(cp)
            if p.is_file():
                return p
            for root in (_REPO_ROOT, _BACKEND_DIR):
                if (root / cp).is_file():
                    return root / cp
    for candidate in _CANDIDATE_WEIGHTS:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "No trained YOLO weights found. Place best.pt in the project model/ folder "
        "or set MODEL_PATH."
    )


def _iou(a: BBox, b: BBox) -> float:
    ax2, ay2 = a.x + a.width, a.y + a.height
    bx2, by2 = b.x + b.width, b.y + b.height
    ix1, iy1 = max(a.x, b.x), max(a.y, b.y)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = a.width * a.height + b.width * b.height - inter
    return inter / union if union > 0 else 0.0


def _nms(detections: list[Detection], iou_thr: float = _NMS_IOU) -> list[Detection]:
    ordered = sorted(detections, key=lambda d: d.confidence, reverse=True)
    kept: list[Detection] = []
    for det in ordered:
        if det.bbox is None:
            kept.append(det)
            continue
        if all(k.bbox is None or _iou(det.bbox, k.bbox) < iou_thr for k in kept):
            kept.append(det)
    return kept


class SonarModelService(ModelService):
    """Ultralytics YOLOv8 wrapper around the Colab-trained sonar debris weights."""

    def __init__(self, model_path: str = "") -> None:
        self._configured_path = model_path
        self._resolved_path: Path | None = None
        self._pytorch_model = None
        self._loading_pytorch = False
        self._names: dict[int, str] = dict(_DEFAULT_NAMES)
        self._loaded = False
        self._onnx_session = None
        # ⭐ D-GRM feature extraction state
        self._hook_features: dict = {}
        self._backbone_hook_ref = None
        self._dgrm = None

    @property
    def _backbone_hook(self):
        if self._backbone_hook_ref is None and self._pytorch_model is None and not self._loading_pytorch:
            self._load_pytorch_model()
        return self._backbone_hook_ref

    @_backbone_hook.setter
    def _backbone_hook(self, val):
        self._backbone_hook_ref = val

    @property
    def _model(self):
        if self._pytorch_model is None and not self._loading_pytorch:
            self._load_pytorch_model()
        return self._pytorch_model

    @_model.setter
    def _model(self, val):
        self._pytorch_model = val

    def _load_pytorch_model(self) -> bool:
        """Lazily load PyTorch weights only if ONNX is unavailable or fails."""
        if self._pytorch_model is not None:
            return True
        if self._loading_pytorch:
            return False
        self._loading_pytorch = True
        try:
            from ultralytics import YOLO

            try:
                self._resolved_path = resolve_model_path(self._configured_path)
            except Exception:
                self._resolved_path = None

            candidate_list = ([self._resolved_path] if self._resolved_path else []) + _CANDIDATE_WEIGHTS
            for candidate in candidate_list:
                if candidate and candidate.is_file():
                    try:
                        self._pytorch_model = YOLO(str(candidate))
                        self._resolved_path = candidate
                        names = getattr(self._pytorch_model, "names", None)
                        if isinstance(names, dict) and names:
                            self._names = {int(k): str(v) for k, v in names.items()}
                        self._register_backbone_hook()
                        logger.warning("✅ PyTorch model loaded successfully from %s", candidate)
                        return True
                    except Exception as exc:
                        logger.warning("Could not load weights from %s: %s", candidate, exc)
        except Exception as e:
            logger.warning("Could not import or initialize Ultralytics PyTorch: %s", e)
        finally:
            self._loading_pytorch = False
        return False

    def load(self) -> None:
        # ⭐ Initialize ONNX Runtime session first for low-memory cloud deployments (Render 512MB RAM)
        self._onnx_session = None
        for candidate_onnx in [
            _REPO_ROOT / "model" / "best_yolo11s.onnx",
            _BACKEND_DIR / "model" / "best_yolo11s.onnx",
            _REPO_ROOT / "best.onnx",
            _BACKEND_DIR / "best.onnx",
            _BACKEND_DIR / "model" / "best.onnx",
        ]:
            if candidate_onnx.is_file():
                try:
                    import onnxruntime as ort

                    opts = ort.SessionOptions()
                    opts.intra_op_num_threads = 1
                    opts.inter_op_num_threads = 1
                    opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
                    opts.enable_cpu_mem_arena = False

                    self._onnx_session = ort.InferenceSession(
                        str(candidate_onnx),
                        sess_options=opts,
                        providers=["CPUExecutionProvider"],
                    )
                    logger.warning("✅ ONNX Runtime session loaded successfully from %s", candidate_onnx)
                    self._loaded = True
                    break
                except Exception as exc:
                    logger.warning("Could not load ONNX session from %s: %s", candidate_onnx, exc)

        # Only load PyTorch if ONNX is NOT present (saves ~350MB RAM on Render 512MB free tier)
        if self._onnx_session is None:
            if self._load_pytorch_model():
                self._loaded = True
            else:
                raise RuntimeError("Failed to load any valid ONNX model or YOLO weights.")
        else:
            self._loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._loaded and (self._onnx_session is not None or self._model is not None)

    # ⭐ Register forward hook on YOLO backbone's final feature layer (SPPF / C2f / C3k2 / C2PSA / WERBBlock)
    def _register_backbone_hook(self) -> None:
        """Register forward hook on backbone's feature layer for D-GRM."""
        try:
            if not hasattr(self._model, "model") or self._model.model is None:
                return

            model_layers = list(self._model.model.model)
            hook_index = 9

            # Prioritize SPPF layer in backbone (layer 9 in YOLO11 / YOLOv8)
            sppf_found = False
            for i, layer in enumerate(model_layers):
                if "SPPF" in layer.__class__.__name__:
                    hook_index = i
                    sppf_found = True
                    break
            if not sppf_found:
                for i, layer in enumerate(model_layers):
                    if any(k in layer.__class__.__name__ for k in ("C2f", "C3k2", "C2PSA", "WERBBlock")):
                        hook_index = i



            def _make_hook(name):
                def hook(module, inp, output):
                    tensor = output[0] if isinstance(output, (tuple, list)) else output
                    if hasattr(tensor, "ndim") and tensor.ndim == 4:
                        self._hook_features[name] = tensor.detach()
                return hook

            # Register hook on the backbone's feature layer
            if hook_index < len(model_layers):
                self._backbone_hook = model_layers[hook_index].register_forward_hook(
                    _make_hook("backbone_out")
                )
            else:
                logger.warning(
                    "Could not find valid backbone layer at index %d for D-GRM. "
                    "Falling back to zero features.",
                    hook_index,
                )

        except Exception as exc:
            logger.warning("Failed to register backbone hook for D-GRM: %s. Falling back to zero features.", exc)

    def cleanup(self) -> None:
        """Clean up hooks to avoid memory leaks."""
        if self._backbone_hook is not None:
            self._backbone_hook.remove()
            self._backbone_hook = None
        self._hook_features.clear()

    def _boxes_from_result(self, result, meta: dict | None = None) -> list[Detection]:
        detections: list[Detection] = []
        names = result.names or self._names
        boxes = result.boxes
        if boxes is None:
            return detections

        has_letterbox = bool(meta and "scale" in meta and meta.get("scale", 0) > 0)
        scale = float(meta["scale"]) if has_letterbox else 1.0
        pad_left = float(meta.get("pad_left", 0)) if has_letterbox else 0.0
        pad_top = float(meta.get("pad_top", 0)) if has_letterbox else 0.0
        orig_shape = meta.get("orig_shape") if has_letterbox else None
        orig_h = float(orig_shape[0]) if orig_shape else None
        orig_w = float(orig_shape[1]) if orig_shape else None

        for box in boxes:
            xyxy = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            raw_name = str(names.get(cls_id, self._names.get(cls_id, f"class_{cls_id}")))
            label = _pretty_label(raw_name)
            x1, y1, x2, y2 = xyxy

            if has_letterbox:
                x1 = (x1 - pad_left) / scale
                y1 = (y1 - pad_top) / scale
                x2 = (x2 - pad_left) / scale
                y2 = (y2 - pad_top) / scale
                if orig_w is not None and orig_h is not None:
                    x1 = max(0.0, min(orig_w, x1))
                    y1 = max(0.0, min(orig_h, y1))
                    x2 = max(0.0, min(orig_w, x2))
                    y2 = max(0.0, min(orig_h, y2))

            width = max(0.0, x2 - x1)
            height = max(0.0, y2 - y1)
            detections.append(
                Detection(
                    class_label=label,
                    confidence=round(conf, 4),
                    bbox=BBox(x=float(x1), y=float(y1), width=width, height=height),
                    area_m2=round((width * height) / 10000.0, 2),
                    position_info=f"{int(x1)},{int(y1)}",
                )
            )
        return detections

    def predict(self, input_data: PreprocessedInput) -> PredictionResult:
        if not self.is_loaded:
            raise RuntimeError("Model has not been loaded. Call load() first.")

        import numpy as np
        from PIL import Image

        raw = input_data.data
        meta = getattr(input_data, "metadata", {}) or {}
        if isinstance(raw, (bytes, bytearray)):
            source = Image.open(io.BytesIO(raw)).convert("RGB")
        elif isinstance(raw, np.ndarray):
            if raw.ndim == 3 and raw.shape[0] in (1, 3):
                # Convert CHW -> HWC
                source = np.transpose(raw, (1, 2, 0))
            else:
                source = raw
            if np.issubdtype(source.dtype, np.floating) and source.max() <= 1.05:
                source = np.clip(source * 255.0, 0, 255).astype(np.uint8)
            source = Image.fromarray(source)
        else:
            raise TypeError(
                f"SonarModelService expects image bytes or numpy array, got {type(raw).__name__}"
            )

        collected: list[Detection] = []
        scores: dict[str, float] = {}
        onnx_succeeded = False

        if getattr(self, "_onnx_session", None) is not None:
            tensor_in = None
            try:
                inp_shape = self._onnx_session.get_inputs()[0].shape
                target_h = int(inp_shape[2]) if len(inp_shape) > 2 and isinstance(inp_shape[2], (int, np.integer)) and inp_shape[2] > 0 else 800
                target_w = int(inp_shape[3]) if len(inp_shape) > 3 and isinstance(inp_shape[3], (int, np.integer)) and inp_shape[3] > 0 else 800

                # Fast direct passthrough if already a preprocessed (3, H, W) tensor
                if isinstance(raw, np.ndarray) and raw.ndim == 3 and raw.shape[0] == 3 and raw.shape[1] == target_h and raw.shape[2] == target_w:
                    tensor_in = np.expand_dims(raw, axis=0).astype(np.float32)
                else:
                    # Clean aspect-ratio letterbox
                    import cv2
                    img_np = np.array(source.convert("RGB"))
                    h_in, w_in = img_np.shape[:2]
                    scale = min(target_h / float(h_in), target_w / float(w_in))
                    nw = int(round(w_in * scale))
                    nh = int(round(h_in * scale))
                    pad_l = (target_w - nw) // 2
                    pad_t = (target_h - nh) // 2
                    resized = cv2.resize(img_np, (nw, nh), interpolation=cv2.INTER_LINEAR)
                    padded = cv2.copyMakeBorder(
                        resized,
                        pad_t,
                        target_h - nh - pad_t,
                        pad_l,
                        target_w - nw - pad_l,
                        cv2.BORDER_CONSTANT,
                        value=(114, 114, 114),
                    )
                    tensor_in = padded.transpose((2, 0, 1))[None].astype(np.float32) / 255.0
                    meta = {
                        "scale": scale,
                        "pad_left": pad_l,
                        "pad_top": pad_t,
                        "orig_shape": (h_in, w_in),
                    }

                input_name = self._onnx_session.get_inputs()[0].name
                onnx_out = self._onnx_session.run(None, {input_name: tensor_in})[0]

                boxes_data = onnx_out[0].T
                boxes = boxes_data[:, :4]
                class_scores = boxes_data[:, 4:]

                max_scores = np.max(class_scores, axis=1)
                max_classes = np.argmax(class_scores, axis=1)

                has_letterbox = meta and "scale" in meta and float(meta.get("scale", 0)) > 0
                scale = float(meta["scale"]) if has_letterbox else 1.0
                pad_left = float(meta.get("pad_left", 0)) if has_letterbox else 0.0
                pad_top = float(meta.get("pad_top", 0)) if has_letterbox else 0.0
                orig_shape = meta.get("orig_shape") if has_letterbox else None
                orig_h = float(orig_shape[0]) if orig_shape else None
                orig_w = float(orig_shape[1]) if orig_shape else None

                for i in range(len(max_scores)):
                    conf = float(max_scores[i])
                    cls_id = int(max_classes[i])
                    raw_name = self._names.get(cls_id, f"class_{cls_id}")
                    if conf < _MODEL_CONF:
                        continue

                    cx, cy, bw, bh = boxes[i]
                    if has_letterbox:
                        x1 = (cx - bw / 2.0 - pad_left) / scale
                        y1 = (cy - bh / 2.0 - pad_top) / scale
                        w_scaled = bw / scale
                        h_scaled = bh / scale
                        if orig_w is not None and orig_h is not None:
                            x1 = max(0.0, min(orig_w, x1))
                            y1 = max(0.0, min(orig_h, y1))
                            w_scaled = max(0.0, min(orig_w - x1, w_scaled))
                            h_scaled = max(0.0, min(orig_h - y1, h_scaled))
                    else:
                        x1 = cx - bw / 2.0
                        y1 = cy - bh / 2.0
                        w_scaled = bw
                        h_scaled = bh

                    label = _pretty_label(raw_name)
                    collected.append(
                        Detection(
                            class_label=label,
                            confidence=round(conf, 4),
                            bbox=BBox(x=float(x1), y=float(y1), width=float(w_scaled), height=float(h_scaled)),
                            area_m2=round((w_scaled * h_scaled) / 10000.0, 2),
                            position_info=f"{int(x1)},{int(y1)}",
                        )
                    )
                onnx_succeeded = True
            except Exception as onnx_exc:
                logger.warning("ONNX inference failed: %s. Falling back to PyTorch.", onnx_exc)
                onnx_succeeded = False
            finally:
                if tensor_in is not None:
                    del tensor_in
                import gc
                gc.collect()

        if not onnx_succeeded:
            self._load_pytorch_model()
            if self._model is not None:
                try:
                    import torch
                    ctx = torch.no_grad()
                except Exception:
                    from contextlib import nullcontext
                    ctx = nullcontext()

                with ctx:
                    for imgsz in [800]:
                        try:
                            results = self._model.predict(
                                source=source,
                                imgsz=imgsz,
                                conf=_MODEL_CONF,
                                verbose=False,
                            )
                            if results:
                                collected.extend(self._boxes_from_result(results[0], meta=meta))
                        except Exception as pt_err:
                            logger.warning("PyTorch predict failed: %s", pt_err)

        detections = _nms(collected)

        import os
        use_dgrm = os.environ.get("USE_DGRM", "false").lower() == "true"
        use_sadh = os.environ.get("USE_SADH", "false").lower() == "true"

        # ⭐ NEW: Extract real features from backbone for D-GRM
        dgrm_features = None
        if use_dgrm and len(detections) > 1:
            boxes = []
            for det in detections:
                if det.bbox:
                    boxes.append([det.bbox.x, det.bbox.y, det.bbox.x + det.bbox.width, det.bbox.y + det.bbox.height])

            backbone_feat = self._hook_features.get("backbone_out")
            if backbone_feat is not None and len(boxes) > 0:
                orig_shape = meta.get("orig_shape") if meta else None
                img_w = orig_shape[1] if orig_shape and len(orig_shape) > 1 else 640
                img_h = orig_shape[0] if orig_shape and len(orig_shape) > 0 else 640
                dgrm_features = self._extract_roi_features(backbone_feat, boxes, img_w, img_h)

            detections = self._apply_dgrm(detections, dgrm_features)
        if use_sadh and meta and ("altitude_m" in meta or "slant_range_m" in meta):
            detections = self._apply_sadh(detections, meta)

        for det in detections:
            scores[det.class_label] = max(scores.get(det.class_label, 0.0), det.confidence)

        if detections:
            best = max(detections, key=lambda d: d.confidence)
            return PredictionResult(
                label=best.class_label,
                confidence=best.confidence,
                raw_scores=scores,
                detections=detections,
            )

        return PredictionResult(
            label="no_detection",
            confidence=0.0,
            raw_scores=scores,
            detections=[],
        )

    # ⭐ Extract RoI features from backbone feature map
    def _extract_roi_features(self, backbone_feat_map, boxes_xyxy, img_w, img_h):
        """Extract RoI features from backbone feature map.

        Args:
            backbone_feat_map: shape [1, C, H_feat, W_feat]
            boxes_xyxy: list of [x1, y1, x2, y2] in pixel space
            img_w: original image width
            img_h: original image height

        Returns:
            Tensor[N, C] (e.g. Tensor[N, 512] for YOLO11s)
        """
        import torch
        if len(boxes_xyxy) == 0:
            c = backbone_feat_map.shape[1] if hasattr(backbone_feat_map, "shape") and len(backbone_feat_map.shape) > 1 else 512
            return torch.zeros(0, c)
        feat = backbone_feat_map[0]
        c, h_feat, w_feat = feat.shape
        roi_vecs = []
        for box in boxes_xyxy:
            x1, y1, x2, y2 = box
            fx1 = max(0, min(w_feat - 1, int((x1 / img_w) * w_feat)))
            fy1 = max(0, min(h_feat - 1, int((y1 / img_h) * h_feat)))
            fx2 = max(fx1 + 1, min(w_feat, int((x2 / img_w) * w_feat)))
            fy2 = max(fy1 + 1, min(h_feat, int((y2 / img_h) * h_feat)))

            roi_patch = feat[:, fy1:fy2, fx1:fx2]
            roi_vec = roi_patch.mean(dim=[1, 2])
            roi_vecs.append(roi_vec)
        return torch.stack(roi_vecs, dim=0)

    def _apply_dgrm(self, detections: list[Detection], dgrm_features=None) -> list[Detection]:
        """Apply Debris Graph Reasoning to correlate and refine detection confidence."""
        if len(detections) <= 1:
            return detections
        try:
            import torch
            from app.models.neural.debris_graph import DebrisGraphReasoningModule

            boxes = []
            for det in detections:
                if det.bbox:
                    boxes.append([det.bbox.x, det.bbox.y, det.bbox.x + det.bbox.width, det.bbox.y + det.bbox.height])
                else:
                    boxes.append([0.0, 0.0, 10.0, 10.0])
            boxes_tensor = torch.tensor(boxes, dtype=torch.float32)

            feature_dim = 512
            if dgrm_features is not None and len(dgrm_features) == len(detections):
                graph_features = dgrm_features
                if hasattr(graph_features, "shape") and len(graph_features.shape) > 1:
                    feature_dim = graph_features.shape[1]
            else:
                graph_features = torch.zeros(len(detections), feature_dim)

            if self._dgrm is None or getattr(self._dgrm, "_input_dim", None) != feature_dim:
                self._dgrm = DebrisGraphReasoningModule(input_dim=feature_dim)
                self._dgrm._input_dim = feature_dim
                self._dgrm.eval()

            with torch.no_grad():
                _, adj = self._dgrm(graph_features, boxes_tensor)
                adj_np = adj.cpu().numpy()
            updated_detections = list(detections)
            import dataclasses
            for i in range(len(detections)):
                connected = (adj_np[i] > 0.3).sum()
                if connected > 1:
                    new_conf = min(1.0, round(detections[i].confidence * 1.05, 4))
                    updated_detections[i] = dataclasses.replace(detections[i], confidence=new_conf)
            return updated_detections
        except Exception as exc:
            logger.debug("D-GRM post-processing skipped: %s", exc)
        return detections

    def _apply_sadh(self, detections: list[Detection], metadata: dict) -> list[Detection]:
        """Apply SADH physics verification (shadow-height geometry)."""
        alt_m = float(metadata.get("altitude_m", 10.0) or 10.0)
        range_m = float(metadata.get("slant_range_m", 50.0) or 50.0)
        for det in detections:
            h_m = float(getattr(det, "sadh_height_m", 0.0) or (det.bbox.height * 0.05 if det.bbox else 0.5))
            shadow_m = float(getattr(det, "shadow_length_m", 0.0) or (det.bbox.height * 0.1 if det.bbox else 1.0))
            theo_shadow = (h_m * range_m) / max(alt_m, 1e-3)
            violation = abs(shadow_m - theo_shadow) / max(theo_shadow, 1e-3)
            if violation > 0.4:
                det.confidence = max(0.1, round(det.confidence * 0.85, 4))
            elif violation < 0.15:
                det.confidence = min(1.0, round(det.confidence * 1.06, 4))
        return detections

    def metadata(self) -> ModelMetadata:
        return ModelMetadata(
            name="sih2026-yolov8s-marine-debris",
            version="colab-best",
            provider="sonar",
        )
