"""Unit tests for per-class dynamic thresholding."""

from app.services.sonar_model_service import get_class_threshold


def test_get_class_threshold():
    # Test known classes from per_class_thresholds.csv
    assert get_class_threshold("mine_munitions") == 0.289
    assert get_class_threshold("shipwreck") == 0.326
    assert get_class_threshold("ghost_net") == 0.814
    assert get_class_threshold("Ghost Net") == 0.814
    assert get_class_threshold("Submarine Pipeline") == 0.450
    assert get_class_threshold("unknown_class", default=0.15) == 0.15
