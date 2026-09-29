import numpy as np
import pytest

from app.schemas.ml import BBox, Detection, PredictionResult
from app.services.waterfall_tiling import (
    _bbox_iou,
    generate_waterfall_tiles,
    get_xtf_tiling_config,
    global_tile_nms,
    infer_waterfall_tiled,
    translate_detection_to_global,
)


class TestWaterfallTilingConfig:
    def test_default_config(self, monkeypatch):
        monkeypatch.delenv("XTF_TILE_WIDTH", raising=False)
        monkeypatch.delenv("XTF_TILE_HEIGHT", raising=False)
        monkeypatch.delenv("XTF_TILE_OVERLAP", raising=False)
        w, h, ov = get_xtf_tiling_config()
        assert w == 640
        assert h == 640
        assert ov == 0.20

    def test_custom_env_config(self, monkeypatch):
        monkeypatch.setenv("XTF_TILE_WIDTH", "800")
        monkeypatch.setenv("XTF_TILE_HEIGHT", "500")
        monkeypatch.setenv("XTF_TILE_OVERLAP", "0.25")
        w, h, ov = get_xtf_tiling_config()
        assert w == 800
        assert h == 500
        assert ov == 0.25

    def test_invalid_env_fallback(self, monkeypatch):
        monkeypatch.setenv("XTF_TILE_WIDTH", "-50")
        monkeypatch.setenv("XTF_TILE_HEIGHT", "invalid")
        monkeypatch.setenv("XTF_TILE_OVERLAP", "1.5")
        w, h, ov = get_xtf_tiling_config()
        assert w == 640
        assert h == 640
        assert ov == 0.20


class TestTileGeneration:
    def test_1_small_waterfall_smaller_than_tile(self):
        # 1. Smaller than tile: exactly one tile, offset (0, 0)
        wf = np.zeros((300, 400), dtype=np.uint8)
        tiles = generate_waterfall_tiles(wf, tile_width=640, tile_height=640, overlap=0.20)
        assert len(tiles) == 1
        tile_np, x_off, y_off = tiles[0]
        assert x_off == 0
        assert y_off == 0
        assert tile_np.shape == (300, 400)

    def test_2_exact_tile_sized_waterfall(self):
        # 2. Exact tile-sized waterfall: exactly one tile
        wf = np.zeros((640, 640), dtype=np.uint8)
        tiles = generate_waterfall_tiles(wf, tile_width=640, tile_height=640, overlap=0.20)
        assert len(tiles) == 1
        tile_np, x_off, y_off = tiles[0]
        assert x_off == 0
        assert y_off == 0
        assert tile_np.shape == (640, 640)

    def test_3_larger_waterfall_coverage(self):
        # 3. Larger waterfall: multiple tiles, complete coverage
        H, W = 1500, 2000
        wf = np.arange(H * W, dtype=np.uint8).reshape((H, W))
        tiles = generate_waterfall_tiles(wf, tile_width=640, tile_height=640, overlap=0.20)
        assert len(tiles) > 1

        # Verify complete coverage by checking a coverage mask
        coverage = np.zeros((H, W), dtype=bool)
        for tile_np, x_off, y_off in tiles:
            th, tw = tile_np.shape
            coverage[y_off : y_off + th, x_off : x_off + tw] = True
        assert np.all(coverage), "All pixels of the waterfall must be covered by at least one tile"

    def test_4_adjacent_tiles_overlap(self):
        # 4. Overlap: adjacent tiles actually overlap
        wf = np.zeros((1000, 1000), dtype=np.uint8)
        tw, th, ov = 640, 640, 0.20
        tiles = generate_waterfall_tiles(wf, tile_width=tw, tile_height=th, overlap=ov)

        # Check horizontal overlap between first two tiles with same y_off
        row0_tiles = [t for t in tiles if t[2] == 0]
        assert len(row0_tiles) >= 2
        t0_x, t1_x = row0_tiles[0][1], row0_tiles[1][1]
        overlap_px = (t0_x + tw) - t1_x
        assert overlap_px >= tw * ov, f"Horizontal overlap {overlap_px} must be >= expected {tw * ov}"

        # Check vertical overlap
        col0_tiles = [t for t in tiles if t[1] == 0]
        assert len(col0_tiles) >= 2
        t0_y, t1_y = col0_tiles[0][2], col0_tiles[1][2]
        overlap_y_px = (t0_y + th) - t1_y
        assert overlap_y_px >= th * ov, f"Vertical overlap {overlap_y_px} must be >= expected {th * ov}"

    def test_5_boundary_reach(self):
        # 5. Boundary: final tile reaches the right and bottom edges
        H, W = 1234, 1876
        wf = np.zeros((H, W), dtype=np.uint8)
        tiles = generate_waterfall_tiles(wf, tile_width=640, tile_height=640, overlap=0.20)

        max_right = max(x_off + tile_np.shape[1] for tile_np, x_off, _ in tiles)
        max_bottom = max(y_off + tile_np.shape[0] for tile_np, _, y_off in tiles)
        assert max_right == W
        assert max_bottom == H


class TestCoordinateTranslation:
    def test_6_coordinate_translation(self):
        # 6. Given local bbox = (10, 20, 30, 40) and tile offset (100, 200),
        # resulting global bbox must be (110, 220, 30, 40)
        local_det = Detection(
            class_label="Shipwreck",
            confidence=0.85,
            bbox=BBox(x=10.0, y=20.0, width=30.0, height=40.0),
            depth_m=12.0,
            area_m2=0.12,
        )
        global_det = translate_detection_to_global(local_det, x_offset=100, y_offset=200)

        assert global_det.bbox.x == 110.0
        assert global_det.bbox.y == 220.0
        assert global_det.bbox.width == 30.0
        assert global_det.bbox.height == 40.0
        assert global_det.class_label == "Shipwreck"
        assert global_det.confidence == 0.85
        assert global_det.depth_m == 12.0
        assert global_det.area_m2 == 0.12


class TestGlobalTileNMS:
    def test_7_nms_same_class_overlapping_keeps_highest(self):
        # Same class overlapping: IoU > 0.45 -> retain only highest confidence
        d1 = Detection(
            class_label="Shipwreck",
            confidence=0.90,
            bbox=BBox(x=100.0, y=100.0, width=50.0, height=50.0),
        )
        d2 = Detection(
            class_label="Shipwreck",
            confidence=0.75,
            bbox=BBox(x=105.0, y=105.0, width=50.0, height=50.0), # heavy overlap
        )
        assert _bbox_iou(d1.bbox, d2.bbox) > 0.45
        kept = global_tile_nms([d1, d2], iou_threshold=0.45)
        assert len(kept) == 1
        assert kept[0].confidence == 0.90

    def test_7_nms_same_class_non_overlapping_keeps_both(self):
        # Same class non-overlapping: retain both
        d1 = Detection(
            class_label="Shipwreck",
            confidence=0.90,
            bbox=BBox(x=100.0, y=100.0, width=50.0, height=50.0),
        )
        d2 = Detection(
            class_label="Shipwreck",
            confidence=0.85,
            bbox=BBox(x=300.0, y=300.0, width=50.0, height=50.0),
        )
        assert _bbox_iou(d1.bbox, d2.bbox) == 0.0
        kept = global_tile_nms([d1, d2], iou_threshold=0.45)
        assert len(kept) == 2

    def test_7_nms_different_class_overlapping_keeps_both(self):
        # Different class overlapping: do NOT suppress each other
        d1 = Detection(
            class_label="Shipwreck",
            confidence=0.90,
            bbox=BBox(x=100.0, y=100.0, width=50.0, height=50.0),
        )
        d2 = Detection(
            class_label="Ghost Net",
            confidence=0.80,
            bbox=BBox(x=100.0, y=100.0, width=50.0, height=50.0),
        )
        kept = global_tile_nms([d1, d2], iou_threshold=0.45)
        assert len(kept) == 2

    def test_7_nms_iou_threshold_boundary_behavior(self):
        # Construct boxes with exactly controlled IoU
        # Box A: 100x100 at (0,0) (Area = 10000)
        # Box B shifted along x: width 100, height 100.
        # Shift dx: Intersection = (100 - dx) * 100. Union = 20000 - (100 - dx)*100.
        # For IoU = 0.45:
        # (100 - dx) / (200 - (100 - dx)) = 0.45
        # 100 - dx = 0.45 * (100 + dx) = 45 + 0.45 dx
        # 55 = 1.45 dx => dx = 37.931
        box_a = BBox(x=0.0, y=0.0, width=100.0, height=100.0)

        # Shift dx = 40 -> IoU = 6000 / 14000 = 0.4285 <= 0.45 -> both kept
        box_b_kept = BBox(x=40.0, y=0.0, width=100.0, height=100.0)
        iou_kept = _bbox_iou(box_a, box_b_kept)
        assert iou_kept <= 0.45

        d_a = Detection(class_label="Mine Munitions", confidence=0.80, bbox=box_a)
        d_b = Detection(class_label="Mine Munitions", confidence=0.70, bbox=box_b_kept)
        assert len(global_tile_nms([d_a, d_b], iou_threshold=0.45)) == 2

        # Shift dx = 35 -> IoU = 6500 / 13500 = 0.4815 > 0.45 -> higher kept
        box_b_suppressed = BBox(x=35.0, y=0.0, width=100.0, height=100.0)
        iou_suppressed = _bbox_iou(box_a, box_b_suppressed)
        assert iou_suppressed > 0.45

        d_c = Detection(class_label="Mine Munitions", confidence=0.70, bbox=box_b_suppressed)
        kept_suppressed = global_tile_nms([d_a, d_c], iou_threshold=0.45)
        assert len(kept_suppressed) == 1
        assert kept_suppressed[0].confidence == 0.80


class TestTiledInferenceMock:
    def test_infer_waterfall_tiled_end_to_end(self):
        class MockInference:
            def predict(self, raw_bytes: bytes) -> PredictionResult:
                # Returns a mock detection in the center of the tile
                return PredictionResult(
                    label="Shipwreck",
                    confidence=0.88,
                    detections=[
                        Detection(
                            class_label="Shipwreck",
                            confidence=0.88,
                            bbox=BBox(x=50.0, y=50.0, width=40.0, height=40.0),
                        )
                    ],
                )

        wf = np.zeros((1000, 1000), dtype=np.uint8)
        result = infer_waterfall_tiled(
            waterfall_np=wf,
            inference_service=MockInference(),
            tile_width=640,
            tile_height=640,
            overlap=0.20,
        )
        assert isinstance(result, PredictionResult)
        assert result.confidence == 0.88
        assert len(result.detections) > 0
        # Check that coordinates were offset
        for d in result.detections:
            assert d.bbox.x >= 50.0
            assert d.bbox.y >= 50.0
