"""Integration tests for Bathymetry API routes."""

import cv2
import io
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_generate_bathymetry_endpoint():
    client = TestClient(app)

    # Create synthetic sonar image
    img = np.ones((100, 200), dtype=np.uint8) * 128
    img[40:60, 80:120] = 240  # bright target
    img[40:60, 120:180] = 20  # dark shadow

    _, png_bytes = cv2.imencode(".png", img)

    response = client.post(
        "/api/bathymetry/generate",
        params={"H_s": 15.0, "R_s": 50.0},
        files={"file": ("sonar.png", io.BytesIO(png_bytes.tobytes()), "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert "metadata" in data
    assert "shadows" in data
    assert "point_cloud" in data
    assert "elevation_grid" in data
    assert data["metadata"]["H_s"] == 15.0
    assert len(data["shadows"]) >= 1
    assert len(data["point_cloud"]) > 0
