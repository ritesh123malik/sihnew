"""XTF waterfall tiling, coordinate translation, and cross-tile duplicate suppression."""

from __future__ import annotations

import logging
import os
from typing import Any

import cv2
import numpy as np

from app.schemas.ml import BBox, Detection, PredictionResult
from app.services.inference_service import InferenceService

logger = logging.getLogger(__name__)

DEFAULT_TILE_WIDTH = 640
DEFAULT_TILE_HEIGHT = 640
DEFAULT_TILE_OVERLAP = 0.20
DEFAULT_NMS_IOU = 0.45


def get_xtf_tiling_config() -> tuple[int, int, float]:
    """Read tiling configuration from environment with safe fallback to defaults."""
    tile_width = DEFAULT_TILE_WIDTH
    tile_height = DEFAULT_TILE_HEIGHT
    overlap = DEFAULT_TILE_OVERLAP

    raw_w = os.environ.get("XTF_TILE_WIDTH", "").strip()
    raw_h = os.environ.get("XTF_TILE_HEIGHT", "").strip()
    raw_ov = os.environ.get("XTF_TILE_OVERLAP", "").strip()

    if raw_w:
        try:
            val = int(raw_w)
            if val > 0:
                tile_width = val
        except ValueError:
            pass

    if raw_h:
        try:
            val = int(raw_h)
            if val > 0:
                tile_height = val
        except ValueError:
            pass

    if raw_ov:
        try:
            val = float(raw_ov)
            if 0.0 <= val < 1.0:
                overlap = val
        except ValueError:
            pass

    return tile_width, tile_height, overlap


def _compute_axis_offsets(length: int, tile_size: int, stride: int) -> list[int]:
    """Compute 1D tile start offsets ensuring edge coverage and no duplicates."""
    if length <= tile_size:
        return [0]

    offsets: set[int] = set()
    pos = 0
    while pos + tile_size <= length:
        offsets.add(pos)
        pos += stride

    # Ensure the final tile reaches the exact right/bottom edge
    offsets.add(length - tile_size)
    return sorted(list(offsets))


def generate_waterfall_tiles(
    waterfall_np: np.ndarray,
    tile_width: int = DEFAULT_TILE_WIDTH,
    tile_height: int = DEFAULT_TILE_HEIGHT,
    overlap: float = DEFAULT_TILE_OVERLAP,
) -> list[tuple[np.ndarray, int, int]]:
    """Slice waterfall into overlapping tiles.

    Returns:
        list of (tile_np, x_offset, y_offset)
    """
    h, w = waterfall_np.shape[:2]

    # Edge case: waterfall smaller than or equal to tile
    if h <= tile_height and w <= tile_width:
        return [(waterfall_np, 0, 0)]

    stride_x = max(1, int(round(tile_width * (1.0 - overlap))))
    stride_y = max(1, int(round(tile_height * (1.0 - overlap))))

    x_offsets = _compute_axis_offsets(w, tile_width, stride_x)
    y_offsets = _compute_axis_offsets(h, tile_height, stride_y)

    tiles: list[tuple[np.ndarray, int, int]] = []
    for y_off in y_offsets:
        tile_h = min(tile_height, h - y_off)
        for x_off in x_offsets:
            tile_w = min(tile_width, w - x_off)
            tile_slice = waterfall_np[y_off : y_off + tile_h, x_off : x_off + tile_w]
            tiles.append((tile_slice, x_off, y_off))

    return tiles


def translate_detection_to_global(det: Detection, x_offset: int, y_offset: int) -> Detection:
    """Translate tile-local coordinates of a detection into full waterfall coordinates."""
    if det.bbox is None:
        return det

    new_bbox = BBox(
        x=float(det.bbox.x + x_offset),
        y=float(det.bbox.y + y_offset),
        width=float(det.bbox.width),
        height=float(det.bbox.height),
    )
    return Detection(
        class_label=det.class_label,
        confidence=det.confidence,
        bbox=new_bbox,
        depth_m=det.depth_m,
        area_m2=det.area_m2,
        position_info=f"{int(new_bbox.x)},{int(new_bbox.y)}",
        raw_data=dict(det.raw_data),
    )


def _bbox_iou(a: BBox, b: BBox) -> float:
    """Standard bounding-box IoU (intersection / union)."""
    ax2, ay2 = a.x + a.width, a.y + a.height
    bx2, by2 = b.x + b.width, b.y + b.height
    ix1, iy1 = max(a.x, b.x), max(a.y, b.y)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = a.width * a.height + b.width * b.height - inter
    return inter / union if union > 0.0 else 0.0


def _normalize_class_name(label: str) -> str:
    return label.strip().lower().replace(" ", "_").replace("-", "_")


def global_tile_nms(detections: list[Detection], iou_threshold: float = DEFAULT_NMS_IOU) -> list[Detection]:
    """Perform per-class greedy NMS in global waterfall coordinates."""
    by_class: dict[str, list[Detection]] = {}
    for det in detections:
        key = _normalize_class_name(det.class_label)
        by_class.setdefault(key, []).append(det)

    final_kept: list[Detection] = []
    for cls_key, class_dets in by_class.items():
        ordered = sorted(class_dets, key=lambda d: d.confidence, reverse=True)
        kept: list[Detection] = []
        for det in ordered:
            if det.bbox is None:
                kept.append(det)
                continue
            if all(k.bbox is None or _bbox_iou(det.bbox, k.bbox) <= iou_threshold for k in kept):
                kept.append(det)
        final_kept.extend(kept)

    final_kept.sort(key=lambda d: d.confidence, reverse=True)
    return final_kept


def infer_waterfall_tiled(
    waterfall_np: np.ndarray,
    inference_service: InferenceService,
    tile_width: int | None = None,
    tile_height: int | None = None,
    overlap: float | None = None,
    iou_threshold: float = DEFAULT_NMS_IOU,
) -> PredictionResult:
    """Execute tiled inference across a waterfall and assemble global detections."""
    cfg_w, cfg_h, cfg_ov = get_xtf_tiling_config()
    tw = tile_width if tile_width is not None and tile_width > 0 else cfg_w
    th = tile_height if tile_height is not None and tile_height > 0 else cfg_h
    t_ov = overlap if overlap is not None and 0.0 <= overlap < 1.0 else cfg_ov

    tiles = generate_waterfall_tiles(waterfall_np, tile_width=tw, tile_height=th, overlap=t_ov)
    logger.info("Executing XTF tiled inference: %d tiles (%dx%d, overlap=%.2f)", len(tiles), tw, th, t_ov)

    all_detections: list[Detection] = []
    for tile_np, x_off, y_off in tiles:
        success, png_bytes = cv2.imencode(".png", tile_np)
        if not success:
            logger.warning("Failed to encode waterfall tile at offset (%d, %d)", x_off, y_off)
            continue
        tile_result = inference_service.predict(png_bytes.tobytes())
        for det in tile_result.detections:
            global_det = translate_detection_to_global(det, x_off, y_off)
            all_detections.append(global_det)

    merged_detections = global_tile_nms(all_detections, iou_threshold=iou_threshold)

    raw_scores: dict[str, float] = {}
    for d in merged_detections:
        raw_scores[d.class_label] = max(raw_scores.get(d.class_label, 0.0), d.confidence)

    if merged_detections:
        best = merged_detections[0]
        return PredictionResult(
            label=best.class_label,
            confidence=best.confidence,
            raw_scores=raw_scores,
            detections=merged_detections,
        )

    return PredictionResult(
        label="no_detection",
        confidence=0.0,
        raw_scores=raw_scores,
        detections=[],
    )
