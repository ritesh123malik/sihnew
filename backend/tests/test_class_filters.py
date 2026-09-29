from pathlib import Path
import pytest
from app.api.routes.detect import (
    CANONICAL_MODEL_CLASSES,
    _apply_detection_filters,
    _label_matches,
    _normalize_class_label,
)
from app.schemas.detection import BoundingBox, DetectionItem, RiskLevel
from app.services.result_normalizer import ResultNormalizer


def _make_item(label: str, conf: float = 0.90, size: float = 20.0) -> DetectionItem:
    return DetectionItem(
        detection_id="det-test",
        class_label=label,
        confidence=conf,
        risk_level=RiskLevel.medium,
        bbox=BoundingBox(x=0.5, y=0.5, width=size, height=size),
    )


class TestClassFilters:
    def test_canonical_classes_defined(self):
        expected = {
            "shipwreck",
            "aircraft",
            "submarine_pipeline",
            "ghost_net",
            "mine_munitions",
        }
        assert CANONICAL_MODEL_CLASSES == expected

    def test_normalize_class_labels(self):
        assert _normalize_class_label("Shipwreck") == "shipwreck"
        assert _normalize_class_label("Aircraft") == "aircraft"
        assert _normalize_class_label("Submarine Pipeline") == "submarine_pipeline"
        assert _normalize_class_label("Ghost Net") == "ghost_net"
        assert _normalize_class_label("Mine / Munitions") == "mine_munitions"
        assert _normalize_class_label("Mine/Munitions") == "mine_munitions"
        assert _normalize_class_label("mine_munitions") == "mine_munitions"
        assert _normalize_class_label(" submarine_pipeline ") == "submarine_pipeline"

    def test_all_five_model_classes_recognized(self):
        all_five_labels = [
            "Shipwreck",
            "Aircraft",
            "Submarine Pipeline",
            "Ghost Net",
            "Mine / Munitions",
        ]
        # Test with display labels
        for label in all_five_labels:
            assert _label_matches(label, all_five_labels)

        # Test with canonical model output labels
        canonical_labels = [
            "shipwreck",
            "aircraft",
            "submarine_pipeline",
            "ghost_net",
            "mine_munitions",
        ]
        for canon in canonical_labels:
            assert _label_matches(canon, all_five_labels)

    def test_each_individual_class_selection(self):
        classes = [
            ("Shipwreck", "shipwreck"),
            ("Aircraft", "aircraft"),
            ("Submarine Pipeline", "submarine_pipeline"),
            ("Ghost Net", "ghost_net"),
            ("Mine / Munitions", "mine_munitions"),
        ]
        for display_name, canon_name in classes:
            # Selecting display_name should match its canonical detection
            assert _label_matches(canon_name, [display_name])
            assert _label_matches(display_name, [display_name])

            # Selecting display_name should reject all other canonical classes
            for other_display, other_canon in classes:
                if other_canon != canon_name:
                    assert not _label_matches(other_canon, [display_name]), (
                        f"Selected {display_name} should not match {other_canon}"
                    )

    def test_multiple_classes_selection(self):
        selected = ["Shipwreck", "Mine / Munitions"]
        assert _label_matches("shipwreck", selected)
        assert _label_matches("mine_munitions", selected)
        assert not _label_matches("aircraft", selected)
        assert not _label_matches("submarine_pipeline", selected)
        assert not _label_matches("ghost_net", selected)

    def test_unknown_class_safely_rejected(self):
        # When user selects a known class, unknown detections are rejected
        assert not _label_matches("unknown_object", ["Shipwreck", "Aircraft"])
        assert not _label_matches("unidentified", ["Ghost Net"])

        # When user selects an unknown class, standard model detections are rejected
        assert not _label_matches("shipwreck", ["UFO"])
        assert not _label_matches("ghost_net", ["RandomClass"])

        # Rocks is not a model class
        assert not _label_matches("shipwreck", ["Rocks"])
        assert not _label_matches("aircraft", ["Rocks"])
        assert not _label_matches("submarine_pipeline", ["Rocks"])
        assert not _label_matches("ghost_net", ["Rocks"])
        assert not _label_matches("mine_munitions", ["Rocks"])

    def test_legacy_compatibility(self):
        # Legacy "Debris" matches ghost_net, submarine_pipeline, and literal debris
        assert _label_matches("ghost_net", ["Debris"])
        assert _label_matches("submarine_pipeline", ["Debris"])
        assert _label_matches("debris", ["Debris"])
        assert not _label_matches("shipwreck", ["Debris"])
        assert not _label_matches("aircraft", ["Debris"])

        # Empty selection allows all
        assert _label_matches("shipwreck", [])
        assert _label_matches("mine_munitions", [])

    def test_apply_detection_filters_pipeline(self):
        normalizer = ResultNormalizer()
        items = [
            _make_item("shipwreck", 0.90),
            _make_item("aircraft", 0.90),
            _make_item("submarine_pipeline", 0.90),
            _make_item("ghost_net", 0.90),
            _make_item("mine_munitions", 0.90),
            _make_item("unknown_junk", 0.90),
        ]
        # Filter for only Aircraft and Submarine Pipeline
        filtered, _ = _apply_detection_filters(
            detections=items,
            confidence_threshold=50,
            selected_classes="Aircraft,Submarine Pipeline",
            min_object_size=0,
            normalizer=normalizer,
        )
        labels = [item.class_label for item in filtered]
        assert labels == ["aircraft", "submarine_pipeline"]

    def test_frontend_default_selection_matches_model_classes(self):
        repo_root = Path(__file__).resolve().parents[2]

        launch_jsx = (repo_root / "frontend" / "src" / "pages" / "Launch" / "Launch.jsx").read_text(encoding="utf-8")
        settings_jsx = (
            repo_root / "frontend" / "src" / "components" / "DetectionSettings" / "DetectionSettings.jsx"
        ).read_text(encoding="utf-8")

        expected_classes = [
            "Shipwreck",
            "Aircraft",
            "Submarine Pipeline",
            "Ghost Net",
            "Mine / Munitions",
        ]

        # Verify Launch.jsx contains all 5 expected classes in selected
        for cls_name in expected_classes:
            assert f"'{cls_name}'" in launch_jsx or f'"{cls_name}"' in launch_jsx

        # Verify DetectionSettings.jsx CLASSES contains all 5 expected classes
        for cls_name in expected_classes:
            assert f"'{cls_name}'" in settings_jsx or f'"{cls_name}"' in settings_jsx

        # Verify neither exposes obsolete "Rocks" or "Debris" in filter selections
        assert "['Debris'" not in launch_jsx
        assert "'Rocks'" not in launch_jsx
        assert "'Rocks'" not in settings_jsx
