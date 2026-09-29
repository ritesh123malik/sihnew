"""Waterfall Tiler for Side-Scan Sonar (SSS) Survey Waterfall Sonograms.

Partitions large, multi-thousand-ping waterfall sonograms into windowed,
overlapping 2D tiles for high-resolution neural inference, and stitches
bounding box detections back into global survey coordinates using Global Seam NMS.
"""

from __future__ import annotations

from typing import Any, List, Tuple
import numpy as np

from app.schemas.ml import BBox, Detection


class WaterfallTiler:
    """Slices waterfall sonograms into overlapping tiles and stitches detections."""

    def __init__(self, tile_height: int = 640, tile_width: int = 640, overlap: float = 0.20):
        self.tile_height = max(64, int(tile_height))
        self.tile_width = max(64, int(tile_width))
        self.overlap = max(0.0, min(0.50, float(overlap)))
        self.stride_y = max(32, int(self.tile_height * (1.0 - self.overlap)))

    def slice_waterfall(self, waterfall: np.ndarray) -> List[Tuple[np.ndarray, int, int]]:
        """Partition waterfall into overlapping tiles along the trackline (Y-axis).
        
        Args:
            waterfall: 2D (H, W) or 3D (H, W, C) numpy array of the survey sonogram.

        Returns:
            List of (tile_image, start_ping_index, end_ping_index)
        """
        if waterfall is None or waterfall.size == 0:
            return []

        h, w = waterfall.shape[:2]
        slices: List[Tuple[np.ndarray, int, int]] = []

        if h <= self.tile_height:
            # If smaller or equal to one tile height, return as-is with 0..h bounds
            return [(waterfall, 0, h)]

        for start_y in range(0, h, self.stride_y):
            end_y = min(start_y + self.tile_height, h)
            tile = waterfall[start_y:end_y, :]

            # Zero-pad bottom if the final tile is shorter than tile_height
            if tile.shape[0] < self.tile_height:
                pad_h = self.tile_height - tile.shape[0]
                pad_width = ((0, pad_h), (0, 0)) if tile.ndim == 2 else ((0, pad_h), (0, 0), (0, 0))
                tile = np.pad(tile, pad_width, mode="constant", constant_values=0)

            slices.append((tile, start_y, end_y))
            if end_y >= h:
                break

        return slices

    @staticmethod
    def project_detections_to_global(
        detections: List[Detection],
        start_ping: int,
        orig_width: int,
        tile_width: int = 640,
    ) -> List[Detection]:
        """Project tile-local bounding box coordinates to global waterfall coordinates.
        
        Args:
            detections: List of Detection objects in tile-local pixel space.
            start_ping: The starting ping index (Y-offset) of this tile in the full survey.
            orig_width: Original full swath width in pixels.
            tile_width: Width of the tile during inference.
            
        Returns:
            List of Detection objects with bounding boxes projected to global coordinates.
        """
        import dataclasses
        scale_x = float(orig_width) / float(tile_width) if tile_width > 0 else 1.0
        global_detections: List[Detection] = []

        for det in detections:
            if det.bbox is None:
                global_detections.append(det)
                continue

            global_x = det.bbox.x * scale_x
            global_y = det.bbox.y + float(start_ping)
            global_w = det.bbox.width * scale_x
            global_h = det.bbox.height

            updated_bbox = BBox(
                x=round(global_x, 2),
                y=round(global_y, 2),
                width=round(global_w, 2),
                height=round(global_h, 2),
            )

            if hasattr(det, "model_copy"):
                global_detections.append(
                    det.model_copy(
                        update={
                            "bbox": updated_bbox,
                            "position_info": f"{int(global_x)},{int(global_y)}",
                        }
                    )
                )
            elif dataclasses.is_dataclass(det):
                global_detections.append(
                    dataclasses.replace(
                        det,
                        bbox=updated_bbox,
                        position_info=f"{int(global_x)},{int(global_y)}",
                    )
                )
            else:
                global_detections.append(
                    Detection(
                        class_label=det.class_label,
                        confidence=det.confidence,
                        bbox=updated_bbox,
                        depth_m=det.depth_m,
                        area_m2=det.area_m2,
                        position_info=f"{int(global_x)},{int(global_y)}",
                        raw_data=getattr(det, "raw_data", {}),
                    )
                )

        return global_detections

    @staticmethod
    def apply_global_seam_nms(detections: List[Detection], iou_threshold: float = 0.45) -> List[Detection]:
        """Apply Non-Maximum Suppression across overlapping tile seams."""
        if not detections:
            return []

        # Sort detections by confidence descending
        sorted_dets = sorted(detections, key=lambda d: d.confidence, reverse=True)
        kept: List[Detection] = []

        for det in sorted_dets:
            if det.bbox is None:
                kept.append(det)
                continue

            suppress = False
            for k in kept:
                if k.bbox is None or k.class_label != det.class_label:
                    continue
                # Calculate Intersection over Union
                ax2, ay2 = det.bbox.x + det.bbox.width, det.bbox.y + det.bbox.height
                bx2, by2 = k.bbox.x + k.bbox.width, k.bbox.y + k.bbox.height

                ix1, iy1 = max(det.bbox.x, k.bbox.x), max(det.bbox.y, k.bbox.y)
                ix2, iy2 = min(ax2, bx2), min(ay2, by2)

                inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
                union = (det.bbox.width * det.bbox.height) + (k.bbox.width * k.bbox.height) - inter
                iou = inter / union if union > 0 else 0.0

                if iou > iou_threshold:
                    suppress = True
                    break

            if not suppress:
                kept.append(det)

        return kept
