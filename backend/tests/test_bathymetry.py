"""Comprehensive Unit Tests for Side-Scan Sonar 3D Bathymetry from Acoustic Shadow Inversion."""

import pytest
import numpy as np

from app.services.bathymetry import (
    SideScanBathymetry,
    ShadowRegion,
    BathymetryPoint,
    BathymetryGrid,
)


class TestSideScanBathymetry:
    def test_bathymetry_initialization(self):
        bathymetry = SideScanBathymetry(
            H_s=15.0,
            R_s=50.0,
            sample_spacing=0.1,
            ping_interval=0.5,
            vessel_speed=2.0,
        )
        assert bathymetry.H_s == 15.0
        assert bathymetry.R_s == 50.0
        assert bathymetry.sample_spacing == 0.1
        assert bathymetry.ping_spacing == 1.0  # 2.0 m/s * 0.5 s
        assert bathymetry.grazing_angle == pytest.approx(np.arctan(15.0 / 50.0))

    def test_normalize_intensity(self):
        bathymetry = SideScanBathymetry()
        waterfall = np.random.rand(100, 200) * 255.0
        normalized = bathymetry._normalize_intensity(waterfall)
        assert normalized.min() >= 0.0
        assert normalized.max() <= 1.0

    def test_detect_targets_and_shadows(self):
        bathymetry = SideScanBathymetry(
            shadow_threshold=0.3,
            min_shadow_area=10,
        )

        # Create synthetic waterfall with target and shadow
        waterfall = np.ones((100, 200), dtype=np.float32) * 0.5
        # Add bright target (high backscatter)
        waterfall[40:60, 80:120] = 0.9
        # Add dark shadow behind target
        waterfall[40:60, 120:180] = 0.1

        shadow_regions, processed = bathymetry.detect_targets_and_shadows(
            waterfall,
            intensity_normalized=True,
        )

        assert len(shadow_regions) >= 1
        shadow = shadow_regions[0]
        assert shadow.mean_intensity < 0.35
        assert shadow.area >= 10

    def test_calculate_target_height(self):
        bathymetry = SideScanBathymetry(
            H_s=15.0,
            R_s=50.0,
            ping_interval=0.5,
            vessel_speed=2.0,
        )

        # Shadow length of 10 pixels
        # ping_spacing = 2.0 * 0.5 = 1.0 m/pixel
        # L_s_physical = 10 * 1.0 = 10 m
        # h_target = (10 * 15) / 50 = 3 m
        height = bathymetry.calculate_target_height(
            shadow_length_px=10.0,
            range_px=100.0,
            H_s=15.0,
            R_s=50.0,
        )
        assert height == pytest.approx(3.0)

    def test_generate_bathymetry_grid(self):
        bathymetry = SideScanBathymetry()
        waterfall = np.random.rand(100, 200).astype(np.float32)
        shadow_regions, _ = bathymetry.detect_targets_and_shadows(waterfall)

        grid = bathymetry.generate_bathymetry_grid(waterfall, shadow_regions)

        assert isinstance(grid, BathymetryGrid)
        assert grid.elevation.shape == waterfall.shape
        assert grid.intensity.shape == waterfall.shape

    def test_generate_3d_point_cloud(self):
        bathymetry = SideScanBathymetry()
        waterfall = np.random.rand(100, 200).astype(np.float32)
        shadow_regions, _ = bathymetry.detect_targets_and_shadows(waterfall)
        grid = bathymetry.generate_bathymetry_grid(waterfall, shadow_regions)

        points = bathymetry.generate_3d_point_cloud(grid, decimate=5)

        assert len(points) > 0
        assert all(isinstance(p, BathymetryPoint) for p in points)
        assert points[0].x >= 0.0
        assert points[0].y >= 0.0

    def test_create_height_colormap(self):
        bathymetry = SideScanBathymetry()
        elevation = np.random.rand(100, 200).astype(np.float32) * 10.0 - 5.0  # -5 to +5 meters

        colormap = bathymetry.create_height_colormap(elevation)

        assert colormap.shape == (100, 200, 4)  # RGBA
        assert colormap.dtype == np.float32

    def test_obj_and_ply_export(self, tmp_path):
        bathymetry = SideScanBathymetry()
        waterfall = np.random.rand(50, 50).astype(np.float32)
        shadow_regions, _ = bathymetry.detect_targets_and_shadows(waterfall)
        grid = bathymetry.generate_bathymetry_grid(waterfall, shadow_regions)

        obj_path = str(tmp_path / "bathymetry.obj")
        ply_path = str(tmp_path / "bathymetry.ply")
        geotiff_path = str(tmp_path / "bathymetry.tif")

        bathymetry.export_to_obj(grid, obj_path)
        bathymetry.export_to_ply(grid, ply_path)
        bathymetry.export_to_geotiff(grid, geotiff_path)

        assert (tmp_path / "bathymetry.obj").is_file()
        assert (tmp_path / "bathymetry.ply").is_file()
        assert (tmp_path / "bathymetry.tif").is_file()


class TestBathymetryEdgeCases:
    def test_empty_waterfall(self):
        bathymetry = SideScanBathymetry()
        waterfall = np.zeros((0, 0), dtype=np.float32)
        shadow_regions, processed = bathymetry.detect_targets_and_shadows(waterfall)
        assert len(shadow_regions) == 0

    def test_uniform_intensity(self):
        bathymetry = SideScanBathymetry()
        waterfall = np.ones((100, 200), dtype=np.float32) * 0.5
        shadow_regions, processed = bathymetry.detect_targets_and_shadows(waterfall)
        # No shadows in uniform intensity
        assert len(shadow_regions) == 0

    def test_small_shadows_filtered(self):
        bathymetry = SideScanBathymetry(min_shadow_area=100)
        waterfall = np.ones((100, 200), dtype=np.float32) * 0.5
        # Add small shadow
        waterfall[50:55, 100:110] = 0.1
        shadow_regions, _ = bathymetry.detect_targets_and_shadows(waterfall)
        # Small shadow should be filtered out
        assert len(shadow_regions) == 0
