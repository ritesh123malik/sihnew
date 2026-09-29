"""3D Bathymetry from Acoustic Shadow Inversion for Side-Scan Sonar.

Mathematical Foundation:
- Grazing Angle: theta_g = atan(H_s / R_s)
- Shadow Length: L_s = h_target * (R_s / H_s)
- Target Height: h_target = (L_s * H_s) / R_s
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import rasterio
from pyproj import CRS
from rasterio.transform import from_origin
from scipy.ndimage import binary_dilation, binary_erosion, gaussian_filter
from skimage.measure import label, regionprops


@dataclass
class ShadowRegion:
    """Represents a detected acoustic shadow region."""
    bbox: Tuple[int, int, int, int]  # (x_min, y_min, x_max, y_max)
    centroid: Tuple[float, float]    # (x, y) in image coordinates
    area: float                       # Area in pixels
    mean_intensity: float            # Mean backscatter (should be low)
    length: float                    # Shadow length in pixels
    target_centroid: Tuple[float, float]  # Estimated target position


@dataclass
class BathymetryPoint:
    """3D point with elevation from shadow inversion."""
    x: float          # Across-track coordinate (meters)
    y: float          # Along-track coordinate (meters)
    z: float          # Elevation/height (meters, negative = depression)
    intensity: float  # Original backscatter value


@dataclass
class BathymetryGrid:
    """2.5D elevation grid for 3D rendering."""
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    resolution: float            # meters per pixel
    elevation: np.ndarray        # 2D array of heights
    intensity: np.ndarray        # 2D array of backscatter
    shadows: List[ShadowRegion] = field(default_factory=list)  # Detected shadow regions


class SideScanBathymetry:
    """
    Convert 2D side-scan sonar waterfall to 3D bathymetry using acoustic shadow inversion.

    The algorithm:
    1. Detect high-backscatter targets (bright regions)
    2. Find acoustic shadows (dark regions) behind targets
    3. Measure shadow length (L_s) in pixels
    4. Convert to physical height using: h = (L_s * H_s * pixel_spacing) / R_s
    5. Generate elevation mesh for 3D visualization
    """

    def __init__(
        self,
        H_s: float = 15.0,            # Towfish altitude (meters)
        R_s: float = 50.0,            # Slant range at nadir (meters)
        sample_spacing: float = 0.1,  # Across-track sample spacing (meters)
        ping_interval: float = 0.5,   # Along-track ping interval (seconds)
        vessel_speed: float = 2.0,     # Vessel speed (m/s)
        shadow_threshold: float = 0.3, # Intensity threshold for shadow
        min_shadow_area: int = 50,     # Minimum shadow area in pixels
        gaussian_sigma: float = 2.0,   # Smoothing for intensity
    ):
        self.H_s = float(H_s)
        self.R_s = float(R_s)
        self.sample_spacing = float(sample_spacing)
        self.ping_interval = float(ping_interval)
        self.vessel_speed = float(vessel_speed)
        self.shadow_threshold = float(shadow_threshold)
        self.min_shadow_area = int(min_shadow_area)
        self.gaussian_sigma = float(gaussian_sigma)

        # Calculate derived parameters
        self.ping_spacing = self.vessel_speed * self.ping_interval  # meters per ping
        self.grazing_angle = float(np.arctan(self.H_s / max(0.1, self.R_s)))  # radians

    def detect_targets_and_shadows(
        self,
        waterfall: np.ndarray,
        intensity_normalized: bool = False
    ) -> Tuple[List[ShadowRegion], np.ndarray]:
        """
        Detect targets (high backscatter) and their acoustic shadows.

        Args:
            waterfall: 2D numpy array (pings x samples) of backscatter intensity
            intensity_normalized: Whether intensity is already 0-1 normalized

        Returns:
            List of ShadowRegion objects and processed intensity map
        """
        if waterfall is None or waterfall.size == 0:
            return [], np.zeros((0, 0), dtype=np.float32)

        raw_min = float(np.min(waterfall))
        raw_max = float(np.max(waterfall))
        if raw_max - raw_min <= 1e-4:
            # Completely uniform image -> no targets or shadows
            return [], waterfall.astype(np.float32)

        if not intensity_normalized:
            waterfall = self._normalize_intensity(waterfall)
        else:
            waterfall = waterfall.astype(np.float32)

        # Smooth to reduce speckle noise
        smoothed = gaussian_filter(waterfall, sigma=self.gaussian_sigma)

        # Detect targets: bright regions (high backscatter)
        target_mask = smoothed > 0.7

        # Detect shadows: dark regions behind targets
        shadow_mask = smoothed < self.shadow_threshold

        # If all uniform or no shadows, return empty
        if not np.any(shadow_mask) or np.all(shadow_mask):
            return [], smoothed

        # Clean up masks
        target_mask = binary_dilation(target_mask, iterations=2)
        shadow_mask = binary_erosion(shadow_mask, iterations=1)

        # Find connected components in shadow mask
        labeled_shadows = label(shadow_mask)
        regions = regionprops(labeled_shadows, intensity_image=smoothed)

        shadow_regions: List[ShadowRegion] = []
        for region in regions:
            if region.area < self.min_shadow_area:
                continue

            bbox = region.bbox  # (min_row, min_col, max_row, max_col)
            centroid = (float(region.centroid[1]), float(region.centroid[0]))  # (x, y)

            # Target search area in front of shadow (towards nadir / row direction)
            shadow_y_min, shadow_x_min, shadow_y_max, shadow_x_max = bbox
            search_y_min = max(0, shadow_y_min - 50)
            target_search_area = smoothed[search_y_min:shadow_y_min, shadow_x_min:shadow_x_max]

            if target_search_area.size > 0:
                brightest_idx = np.unravel_index(
                    np.argmax(target_search_area),
                    target_search_area.shape
                )
                target_y = float(search_y_min + brightest_idx[0])
                target_x = float(shadow_x_min + brightest_idx[1])
                target_centroid = (target_x, target_y)
            else:
                target_centroid = (centroid[0], max(0.0, centroid[1] - 20.0))

            # Calculate shadow length in pixels
            shadow_length_px = float(
                np.sqrt(
                    (centroid[0] - target_centroid[0]) ** 2
                    + (centroid[1] - target_centroid[1]) ** 2
                )
            )
            if shadow_length_px <= 0.0:
                shadow_length_px = float(bbox[2] - bbox[0])

            if hasattr(region, "intensity_mean"):
                mean_int = float(region.intensity_mean)
            elif hasattr(region, "mean_intensity"):
                mean_int = float(region.mean_intensity)
            else:
                mean_int = float(np.mean(smoothed[bbox[0]:bbox[2], bbox[1]:bbox[3]]))

            shadow_regions.append(
                ShadowRegion(
                    bbox=bbox,
                    centroid=centroid,
                    area=float(region.area),
                    mean_intensity=mean_int,
                    length=shadow_length_px,
                    target_centroid=target_centroid
                )
            )

        return shadow_regions, smoothed

    def _normalize_intensity(self, waterfall: np.ndarray) -> np.ndarray:
        """Normalize intensity to 0-1 range."""
        if waterfall is None or waterfall.size == 0:
            return np.zeros((0, 0), dtype=np.float32)

        waterfall = waterfall.astype(np.float32)
        min_val = float(np.percentile(waterfall, 1))
        max_val = float(np.percentile(waterfall, 99))
        denom = max_val - min_val
        if denom <= 1e-6:
            denom = 1.0
        waterfall = (waterfall - min_val) / denom
        return np.clip(waterfall, 0.0, 1.0)

    def calculate_target_height(
        self,
        shadow_length_px: float,
        range_px: float,
        H_s: Optional[float] = None,
        R_s: Optional[float] = None
    ) -> float:
        """
        Calculate target height from shadow length using similar triangles.

        h_target / H_s = L_s / R_s => h_target = (L_s * H_s) / R_s
        """
        H_s = float(H_s if H_s is not None else self.H_s)
        R_s = float(R_s if R_s is not None else self.R_s)

        L_s_physical = float(shadow_length_px) * self.ping_spacing
        if R_s <= 0.0:
            return 0.0

        h_target = (L_s_physical * H_s) / R_s
        return float(h_target)

    def generate_bathymetry_grid(
        self,
        waterfall: np.ndarray,
        shadow_regions: List[ShadowRegion],
        H_s: Optional[float] = None,
        R_s: Optional[float] = None
    ) -> BathymetryGrid:
        """Generate 2.5D elevation grid from waterfall and shadow regions."""
        if waterfall is None or waterfall.size == 0:
            return BathymetryGrid(
                x_min=0, x_max=0, y_min=0, y_max=0,
                resolution=self.sample_spacing,
                elevation=np.zeros((0, 0), dtype=np.float32),
                intensity=np.zeros((0, 0), dtype=np.float32),
                shadows=[]
            )

        H_s = H_s or self.H_s
        R_s = R_s or self.R_s

        h, w = waterfall.shape
        elevation = np.zeros((h, w), dtype=np.float32)
        intensity_map = self._normalize_intensity(waterfall)

        # Initialize with small seafloor roughness based on backscatter
        elevation += (intensity_map - 0.5) * 0.1  # +/-0.05m roughness

        # Process each shadow region
        for shadow in shadow_regions:
            h_target = self.calculate_target_height(
                shadow.length,
                range_px=shadow.centroid[0],
                H_s=H_s,
                R_s=R_s
            )

            tx, ty = int(shadow.target_centroid[0]), int(shadow.target_centroid[1])
            if 0 <= tx < w and 0 <= ty < h:
                elevation[ty, tx] = max(elevation[ty, tx], h_target)
                self._add_gaussian_bump(elevation, tx, ty, h_target, radius=10)

            sx_min, sy_min, sx_max, sy_max = shadow.bbox
            elevation[sx_min:sx_max, sy_min:sy_max] = np.maximum(
                elevation[sx_min:sx_max, sy_min:sy_max],
                -h_target * 0.3
            )

        return BathymetryGrid(
            x_min=0.0,
            x_max=float(w * self.sample_spacing),
            y_min=0.0,
            y_max=float(h * self.ping_spacing),
            resolution=self.sample_spacing,
            elevation=elevation,
            intensity=intensity_map,
            shadows=shadow_regions
        )

    def _add_gaussian_bump(
        self,
        elevation: np.ndarray,
        cx: int,
        cy: int,
        height: float,
        radius: int = 10
    ) -> None:
        """Add a Gaussian-shaped elevation bump centered at (cx, cy)."""
        h, w = elevation.shape
        y, x = np.ogrid[:h, :w]
        mask = (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2
        distance = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        bump = height * np.exp(-(distance ** 2) / (2.0 * ((radius / 3.0) ** 2) + 1e-6))
        elevation += (bump * mask).astype(np.float32)

    def generate_3d_point_cloud(
        self,
        bathymetry: BathymetryGrid,
        decimate: int = 5
    ) -> List[BathymetryPoint]:
        """Convert elevation grid to 3D point cloud."""
        points: List[BathymetryPoint] = []
        elevation = bathymetry.elevation
        intensity = bathymetry.intensity

        if elevation.size == 0:
            return points

        decimate = max(1, int(decimate))
        for y in range(0, elevation.shape[0], decimate):
            for x in range(0, elevation.shape[1], decimate):
                z = float(elevation[y, x])
                points.append(
                    BathymetryPoint(
                        x=round(float(x * self.sample_spacing), 3),
                        y=round(float(y * self.ping_spacing), 3),
                        z=round(z, 3),
                        intensity=round(float(intensity[y, x]), 3)
                    )
                )

        return points

    def export_to_geotiff(
        self,
        bathymetry: BathymetryGrid,
        output_path: str,
        crs: Optional[CRS] = None
    ) -> str:
        """Export elevation grid as GeoTIFF."""
        if crs is None:
            crs = CRS.from_epsg(4326)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        transform = from_origin(
            bathymetry.x_min,
            bathymetry.y_max,
            bathymetry.resolution,
            bathymetry.resolution
        )

        with rasterio.open(
            output_path,
            "w",
            driver="GTiff",
            height=bathymetry.elevation.shape[0],
            width=bathymetry.elevation.shape[1],
            count=1,
            dtype=bathymetry.elevation.dtype,
            crs=crs,
            transform=transform
        ) as dst:
            dst.write(bathymetry.elevation, 1)

        return output_path

    def create_height_colormap(
        self,
        elevation: np.ndarray,
        cmap: str = "viridis"
    ) -> np.ndarray:
        """Create RGBA colormap from elevation values."""
        import matplotlib

        if elevation.size == 0:
            return np.zeros((0, 0, 4), dtype=np.float32)

        elev_min = float(np.nanmin(elevation))
        elev_max = float(np.nanmax(elevation))
        denom = elev_max - elev_min
        if denom <= 1e-6:
            denom = 1.0

        elev_normalized = (elevation - elev_min) / denom
        if hasattr(matplotlib, "colormaps"):
            colormap = matplotlib.colormaps[cmap]
        else:
            import matplotlib.cm as cm
            colormap = cm.get_cmap(cmap)
        rgba = colormap(elev_normalized).astype(np.float32)
        return rgba

    def export_to_obj(self, bathymetry_grid: BathymetryGrid, output_path: str) -> str:
        """Export elevation grid as OBJ 3D mesh."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        elevation = bathymetry_grid.elevation
        h, w = elevation.shape

        vertices = []
        faces = []

        for y in range(h):
            for x in range(w):
                z = elevation[y, x]
                vertices.append(f"v {x * bathymetry_grid.resolution:.3f} {z:.3f} {-y * bathymetry_grid.resolution:.3f}")

        for y in range(h - 1):
            for x in range(w - 1):
                i0 = y * w + x
                i1 = y * w + x + 1
                i2 = (y + 1) * w + x
                i3 = (y + 1) * w + x + 1
                faces.append(f"f {i0+1} {i1+1} {i2+1}")
                faces.append(f"f {i1+1} {i3+1} {i2+1}")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# OBJ File - Bathymetry Mesh\n# Generated by SonarSentry\n")
            f.write("\n".join(vertices) + "\n")
            f.write("\n".join(faces) + "\n")

        return output_path

    def export_to_ply(self, bathymetry_grid: BathymetryGrid, output_path: str) -> str:
        """Export point cloud as PLY format."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        elevation = bathymetry_grid.elevation
        intensity = bathymetry_grid.intensity
        h, w = elevation.shape

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("ply\nformat ascii 1.0\n")
            f.write(f"element vertex {h * w}\n")
            f.write("property float x\nproperty float y\nproperty float z\nproperty float intensity\nend_header\n")
            for y in range(h):
                for x in range(w):
                    z = float(elevation[y, x])
                    i = float(intensity[y, x])
                    f.write(f"{x * bathymetry_grid.resolution:.3f} {z:.3f} {-y * bathymetry_grid.resolution:.3f} {i:.3f}\n")

        return output_path
