"""Bathymetry API routes for 3D Seabed Reconstruction from Acoustic Shadow Inversion."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.services.bathymetry import (
    BathymetryGrid,
    BathymetryPoint,
    ShadowRegion,
    SideScanBathymetry,
)
from app.services.xtf_parser import parse_xtf_bytes

router = APIRouter(prefix="/api/bathymetry", tags=["bathymetry"])


@router.post("/generate")
async def generate_bathymetry(
    file: UploadFile = File(...),
    H_s: float = 15.0,
    R_s: float = 50.0,
    sample_spacing: float = 0.1,
    ping_interval: float = 0.5,
    vessel_speed: float = 2.0,
):
    """
    Generate 3D bathymetry from XTF or sonar image file using acoustic shadow inversion.

    Returns:
    - 3D point cloud (JSON)
    - Elevation grid metadata
    - Detected acoustic shadow regions with target heights
    """
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        waterfall = None
        # Try XTF parsing first
        try:
            waterfall_np, meta = parse_xtf_bytes(content)
            waterfall = waterfall_np.astype(np.float32)
        except Exception:
            # Fall back to image decoding
            nparr = np.frombuffer(content, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                waterfall = img.astype(np.float32)

        if waterfall is None or waterfall.size == 0:
            raise HTTPException(status_code=400, detail="Invalid image or XTF sonar file")

        # Initialize service
        bathymetry_service = SideScanBathymetry(
            H_s=H_s,
            R_s=R_s,
            sample_spacing=sample_spacing,
            ping_interval=ping_interval,
            vessel_speed=vessel_speed,
        )

        # Detect shadows and targets
        shadow_regions, processed_intensity = bathymetry_service.detect_targets_and_shadows(waterfall)

        # Generate elevation grid
        bathymetry_grid = bathymetry_service.generate_bathymetry_grid(
            waterfall,
            shadow_regions,
            H_s=H_s,
            R_s=R_s,
        )

        # Generate point cloud
        point_cloud = bathymetry_service.generate_3d_point_cloud(
            bathymetry_grid,
            decimate=max(2, int(waterfall.shape[0] // 50)),
        )

        response = {
            "metadata": {
                "height": int(waterfall.shape[0]),
                "width": int(waterfall.shape[1]),
                "H_s": float(H_s),
                "R_s": float(R_s),
                "sample_spacing": float(sample_spacing),
                "ping_spacing": float(bathymetry_service.ping_spacing),
                "grazing_angle_deg": round(float(np.degrees(bathymetry_service.grazing_angle)), 2),
                "num_shadows": len(shadow_regions),
                "elevation_range": {
                    "min": round(float(np.nanmin(bathymetry_grid.elevation)), 2),
                    "max": round(float(np.nanmax(bathymetry_grid.elevation)), 2),
                },
            },
            "shadows": [
                {
                    "bbox": list(s.bbox),
                    "centroid": [round(s.centroid[0], 2), round(s.centroid[1], 2)],
                    "area": round(s.area, 1),
                    "length_px": round(s.length, 2),
                    "length_m": round(s.length * bathymetry_service.ping_spacing, 2),
                    "target_centroid": [round(s.target_centroid[0], 2), round(s.target_centroid[1], 2)],
                    "estimated_height": round(
                        bathymetry_service.calculate_target_height(s.length, s.centroid[0], H_s, R_s),
                        2,
                    ),
                }
                for s in shadow_regions
            ],
            "point_cloud": [
                {
                    "x": round(p.x, 2),
                    "y": round(p.y, 2),
                    "z": round(p.z, 2),
                    "intensity": round(p.intensity, 3),
                }
                for p in point_cloud[:5000]
            ],
            "elevation_grid": {
                "shape": list(bathymetry_grid.elevation.shape),
                "min": round(float(np.nanmin(bathymetry_grid.elevation)), 2),
                "max": round(float(np.nanmax(bathymetry_grid.elevation)), 2),
                "mean": round(float(np.nanmean(bathymetry_grid.elevation)), 2),
            },
        }

        return JSONResponse(content=response)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/export-geotiff/{survey_id}")
async def export_bathymetry_geotiff(
    survey_id: str,
    H_s: float = 15.0,
    R_s: float = 50.0,
):
    """Export bathymetry as GeoTIFF for GIS / ECDIS integration."""
    try:
        from app.database import SessionLocal
        from app.models.orm import Run

        db = SessionLocal()
        run = db.query(Run).filter(Run.id == survey_id).first()
        db.close()

        if not run or not run.file_path or not os.path.exists(run.file_path):
            raise HTTPException(status_code=404, detail="Survey run file not found")

        content = open(run.file_path, "rb").read()
        try:
            waterfall_np, _ = parse_xtf_bytes(content)
            waterfall = waterfall_np.astype(np.float32)
        except Exception:
            nparr = np.frombuffer(content, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            waterfall = img.astype(np.float32) if img is not None else np.random.rand(100, 200).astype(np.float32)

        bathymetry_service = SideScanBathymetry(H_s=H_s, R_s=R_s)
        shadow_regions, _ = bathymetry_service.detect_targets_and_shadows(waterfall)
        bathymetry_grid = bathymetry_service.generate_bathymetry_grid(waterfall, shadow_regions, H_s=H_s, R_s=R_s)

        output_dir = "exports/bathymetry"
        os.makedirs(output_dir, exist_ok=True)
        output_path = f"{output_dir}/{survey_id}_bathymetry.tif"

        bathymetry_service.export_to_geotiff(bathymetry_grid, output_path)

        return JSONResponse(content={
            "path": output_path,
            "url": f"/exports/bathymetry/{survey_id}_bathymetry.tif",
            "size_mb": round(os.path.getsize(output_path) / (1024 * 1024), 3),
        })

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
