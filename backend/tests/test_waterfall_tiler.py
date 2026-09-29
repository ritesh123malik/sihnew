"""Unit tests for WaterfallTiler and global seam NMS."""

import numpy as np
import pytest

from app.preprocessing.waterfall_tiler import WaterfallTiler
from app.schemas.ml import BBox, Detection


def test_waterfall_tiler_small_image():
    tiler = WaterfallTiler(tile_height=640, tile_width=640, overlap=0.20)
    img = np.zeros((400, 800), dtype=np.uint8)
    slices = tiler.slice_waterfall(img)
    assert len(slices) == 1
    tile, start_y, end_y = slices[0]
    assert start_y == 0
    assert end_y == 400
    assert tile.shape == (400, 800)


def test_waterfall_tiler_large_image_overlap():
    tiler = WaterfallTiler(tile_height=640, tile_width=640, overlap=0.20)
    # 2000 pings along track
    img = np.zeros((2000, 1024), dtype=np.uint8)
    slices = tiler.slice_waterfall(img)
    assert len(slices) > 1

    # Check stride calculation: 640 * 0.8 = 512
    assert tiler.stride_y == 512
    assert slices[0][1] == 0
    assert slices[1][1] == 512

    # Check padding of last slice
    last_tile, last_start, last_end = slices[-1]
    assert last_tile.shape[0] == 640
    assert last_end == 2000


def test_project_detections_and_seam_nms():
    tiler = WaterfallTiler(tile_height=640, tile_width=640, overlap=0.20)

    # Simulate detection in tile 1 (start_ping=512)
    det1 = Detection(
        class_label="Ghost Net",
        confidence=0.85,
        bbox=BBox(x=100.0, y=50.0, width=80.0, height=60.0),
        area_m2=0.48,
    )

    proj = tiler.project_detections_to_global([det1], start_ping=512, orig_width=1280, tile_width=640)
    assert len(proj) == 1
    assert proj[0].bbox.y == 562.0  # 50 + 512
    assert proj[0].bbox.x == 200.0  # 100 * (1280/640)
    assert proj[0].bbox.width == 160.0

    # Simulate duplicate detection in overlapping tile
    det2 = Detection(
        class_label="Ghost Net",
        confidence=0.80,
        bbox=BBox(x=202.0, y=560.0, width=158.0, height=62.0),
        area_m2=0.48,
    )

    merged = WaterfallTiler.apply_global_seam_nms([proj[0], det2], iou_threshold=0.45)
    # Higher confidence det1 should suppress det2
    assert len(merged) == 1
    assert merged[0].confidence == 0.85
