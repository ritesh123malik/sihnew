import pytest
from unittest.mock import patch
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.api.routes.detect import (
    _apply_detection_filters,
    _normalize_class_label,
    _get_per_class_thresholds,
)
from app.schemas.detection import DetectionItem, BoundingBox, RiskLevel
from app.services.result_normalizer import ResultNormalizer

VALID_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 100


def _make_item(class_label: str, confidence: float, size: float = 20.0) -> DetectionItem:
    return DetectionItem(
        detection_id="test-id",
        class_label=class_label,
        confidence=confidence,
        risk_level=RiskLevel.medium,
        bbox=BoundingBox(x=0.0, y=0.0, width=size, height=size),
    )


class TestClassNormalization:
    def test_known_labels(self):
        assert _normalize_class_label("Shipwreck") == "shipwreck"
        assert _normalize_class_label("Aircraft") == "aircraft"
        assert _normalize_class_label("Submarine Pipeline") == "submarine_pipeline"
        assert _normalize_class_label("Ghost Net") == "ghost_net"
        assert _normalize_class_label("Mine Munitions") == "mine_munitions"


class TestPerClassThresholdFiltering:
    def test_missing_confidence_uses_per_class_csv(self):
        normalizer = ResultNormalizer()
        items = [
            _make_item("Shipwreck", 0.32),          # below 0.3263 -> rejected
            _make_item("Shipwreck", 0.33),          # above 0.3263 -> accepted
            _make_item("Aircraft", 0.52),           # below 0.5265 -> rejected
            _make_item("Aircraft", 0.53),           # above 0.5265 -> accepted
            _make_item("Submarine Pipeline", 0.74), # below 0.7497 -> rejected
            _make_item("Submarine Pipeline", 0.75), # above 0.7497 -> accepted
            _make_item("Ghost Net", 0.80),          # below 0.8138 -> rejected
            _make_item("Ghost Net", 0.82),          # above 0.8138 -> accepted
            _make_item("Mine Munitions", 0.28),     # below 0.2893 -> rejected
            _make_item("Mine Munitions", 0.30),     # above 0.2893 -> accepted
            _make_item("Unknown Debris", 0.49),     # unknown class fallback 0.50 -> rejected
            _make_item("Unknown Debris", 0.51),     # unknown class fallback 0.50 -> accepted
        ]
        filtered, summary = _apply_detection_filters(
            detections=items,
            confidence_threshold=None,
            selected_classes="",
            min_object_size=0,
            normalizer=normalizer,
        )
        assert len(filtered) == 6
        assert {d.class_label for d in filtered} == {
            "Shipwreck",
            "Aircraft",
            "Submarine Pipeline",
            "Ghost Net",
            "Mine Munitions",
            "Unknown Debris",
        }
        for d in filtered:
            if d.class_label == "Shipwreck":
                assert d.confidence == 0.33
            elif d.class_label == "Aircraft":
                assert d.confidence == 0.53
            elif d.class_label == "Submarine Pipeline":
                assert d.confidence == 0.75
            elif d.class_label == "Ghost Net":
                assert d.confidence == 0.82
            elif d.class_label == "Mine Munitions":
                assert d.confidence == 0.30
            elif d.class_label == "Unknown Debris":
                assert d.confidence == 0.51

    def test_explicit_confidence_threshold_20(self):
        normalizer = ResultNormalizer()
        items = [
            _make_item("Shipwreck", 0.25),      # below CSV 0.326, but >= global 20% -> accepted
            _make_item("Mine Munitions", 0.19), # < global 20% -> rejected
        ]
        filtered, _ = _apply_detection_filters(
            detections=items,
            confidence_threshold=20,
            selected_classes="",
            min_object_size=0,
            normalizer=normalizer,
        )
        assert len(filtered) == 1
        assert filtered[0].class_label == "Shipwreck"
        assert filtered[0].confidence == 0.25

    def test_explicit_confidence_threshold_50(self):
        normalizer = ResultNormalizer()
        items = [
            _make_item("Mine Munitions", 0.40), # passes CSV 0.289, but < global 50% -> rejected
            _make_item("Shipwreck", 0.55),      # >= global 50% -> accepted
        ]
        filtered, _ = _apply_detection_filters(
            detections=items,
            confidence_threshold=50,
            selected_classes="",
            min_object_size=0,
            normalizer=normalizer,
        )
        assert len(filtered) == 1
        assert filtered[0].class_label == "Shipwreck"
        assert filtered[0].confidence == 0.55

    def test_missing_csv_fallback(self, monkeypatch):
        # Point to a nonexistent path and verify fallback to 0.50 without crashing
        import app.api.routes.detect as detect_module

        monkeypatch.setattr(detect_module, "_PER_CLASS_THRESHOLDS_CSV", Path("nonexistent.csv"))
        monkeypatch.setattr(detect_module, "_CACHED_PER_CLASS_THRESHOLDS", None)

        normalizer = ResultNormalizer()
        items = [
            _make_item("Shipwreck", 0.49),
            _make_item("Shipwreck", 0.51),
        ]
        filtered, _ = _apply_detection_filters(
            detections=items,
            confidence_threshold=None,
            selected_classes="",
            min_object_size=0,
            normalizer=normalizer,
        )
        assert len(filtered) == 1
        assert filtered[0].confidence == 0.51

        # Reset cached thresholds
        monkeypatch.setattr(detect_module, "_CACHED_PER_CLASS_THRESHOLDS", None)

    def test_class_filtering_and_min_size_intact(self):
        normalizer = ResultNormalizer()
        items = [
            _make_item("Shipwreck", 0.35, size=25.0), # correct class, size >= 20 -> accepted
            _make_item("Shipwreck", 0.35, size=10.0), # correct class, size < 20 -> rejected
            _make_item("Ghost Net", 0.85, size=25.0), # filtered out by selected_classes -> rejected
        ]
        filtered, _ = _apply_detection_filters(
            detections=items,
            confidence_threshold=None,
            selected_classes="shipwreck",
            min_object_size=20,
            normalizer=normalizer,
        )
        assert len(filtered) == 1
        assert filtered[0].class_label == "Shipwreck"
        assert filtered[0].bbox.width == 25.0


class TestDetectEndpointThresholdOptions:
    def test_detect_without_confidence_threshold_omitted(self):
        with TestClient(app) as c:
            resp = c.post(
                "/api/detect",
                files={"file": ("test.jpg", VALID_JPEG, "image/jpeg")},
                data={
                    "latitude": "12.9716",
                    "longitude": "80.2436",
                    "sonar_type": "Side-Scan",
                    "resolution": "0.5 m/px",
                    "depth_min": "4",
                    "depth_max": "38",
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True

    def test_detect_with_explicit_threshold_20(self):
        with TestClient(app) as c:
            resp = c.post(
                "/api/detect",
                files={"file": ("test.jpg", VALID_JPEG, "image/jpeg")},
                data={
                    "latitude": "12.9716",
                    "longitude": "80.2436",
                    "sonar_type": "Side-Scan",
                    "resolution": "0.5 m/px",
                    "depth_min": "4",
                    "depth_max": "38",
                    "confidence_threshold": "20",
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True

    def test_detect_with_explicit_threshold_50(self):
        with TestClient(app) as c:
            resp = c.post(
                "/api/detect",
                files={"file": ("test.jpg", VALID_JPEG, "image/jpeg")},
                data={
                    "latitude": "12.9716",
                    "longitude": "80.2436",
                    "sonar_type": "Side-Scan",
                    "resolution": "0.5 m/px",
                    "depth_min": "4",
                    "depth_max": "38",
                    "confidence_threshold": "50",
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
