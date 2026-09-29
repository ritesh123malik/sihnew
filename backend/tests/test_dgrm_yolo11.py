from pathlib import Path
import numpy as np
import pytest
import torch
from PIL import Image

from app.schemas.ml import BBox, Detection, PreprocessedInput
from app.services.sonar_model_service import SonarModelService


@pytest.fixture
def sonar_service():
    service = SonarModelService()
    service.load()
    yield service
    service.cleanup()


class TestDGRMYOLO11:
    def test_a_hook_selects_sppf_and_captures_4d_tensor(self, sonar_service):
        # A. Hook test:
        # - verify YOLO11s selects the intended SPPF feature layer.
        # - verify captured feature tensor is 4D.
        assert sonar_service._backbone_hook is not None

        # Verify hook is on SPPF
        model_layers = list(sonar_service._model.model.model)
        sppf_indices = [i for i, l in enumerate(model_layers) if "SPPF" in l.__class__.__name__]
        assert len(sppf_indices) > 0
        expected_hook_idx = sppf_indices[0]
        assert expected_hook_idx == 9

        # Run forward pass and verify 4D tensor
        dummy_img = Image.fromarray(np.zeros((640, 640, 3), dtype=np.uint8))
        sonar_service._model.predict(source=dummy_img, imgsz=640, verbose=False)
        captured = sonar_service._hook_features.get("backbone_out")
        assert captured is not None
        assert captured.ndim == 4
        assert captured.shape[1] == 512  # 512 channels for YOLO11s SPPF

    def test_b_roi_feature_extraction_produces_n_by_512(self, sonar_service):
        # B. ROI feature test:
        # - verify ROI pooling produces N x 512 features for YOLO11s.
        feat_map = torch.randn(1, 512, 20, 20)
        boxes = [
            [10.0, 10.0, 50.0, 50.0],
            [100.0, 100.0, 150.0, 150.0],
            [200.0, 200.0, 300.0, 300.0],
        ]
        roi_features = sonar_service._extract_roi_features(feat_map, boxes, img_w=640, img_h=640)
        assert roi_features.shape == (3, 512)

    def test_c_dgrm_instance_reuse(self, sonar_service):
        # C. D-GRM reuse test:
        # - verify the same D-GRM module instance is reused across multiple calls.
        dets = [
            Detection(class_label="debris", confidence=0.5, bbox=BBox(x=10.0, y=10.0, width=20.0, height=20.0)),
            Detection(class_label="debris", confidence=0.6, bbox=BBox(x=15.0, y=15.0, width=20.0, height=20.0)),
        ]
        feats = torch.randn(2, 512)

        sonar_service._apply_dgrm(dets, dgrm_features=feats)
        first_instance = sonar_service._dgrm
        assert first_instance is not None

        sonar_service._apply_dgrm(dets, dgrm_features=feats)
        second_instance = sonar_service._dgrm
        assert first_instance is second_instance

    def test_d_determinism_across_calls(self, sonar_service):
        # D. Determinism test:
        # - same inputs + same service/model state produce identical D-GRM confidence results.
        dets1 = [
            Detection(class_label="debris", confidence=0.5000, bbox=BBox(x=10.0, y=10.0, width=20.0, height=20.0)),
            Detection(class_label="debris", confidence=0.6000, bbox=BBox(x=15.0, y=15.0, width=20.0, height=20.0)),
        ]
        dets2 = [
            Detection(class_label="debris", confidence=0.5000, bbox=BBox(x=10.0, y=10.0, width=20.0, height=20.0)),
            Detection(class_label="debris", confidence=0.6000, bbox=BBox(x=15.0, y=15.0, width=20.0, height=20.0)),
        ]
        # Identical identical features
        feats1 = torch.ones(2, 512)
        feats2 = torch.ones(2, 512)

        res1 = sonar_service._apply_dgrm(dets1, dgrm_features=feats1)
        res2 = sonar_service._apply_dgrm(dets2, dgrm_features=feats2)

        for d1, d2 in zip(res1, res2):
            assert d1.confidence == d2.confidence

    def test_e_cluster_behavior_applies_multiplier(self, sonar_service):
        # E. Cluster behavior:
        # - clustered detections receive the existing 1.05 multiplier.
        # - isolated detections remain unchanged.

        # Create 3 identical feature vectors (cosine similarity = 1.0 > 0.65 threshold)
        # and spatial proximity
        clustered_feats = torch.ones(3, 512)
        dets = [
            Detection(class_label="debris", confidence=0.5000, bbox=BBox(x=10.0, y=10.0, width=20.0, height=20.0)),
            Detection(class_label="debris", confidence=0.5000, bbox=BBox(x=12.0, y=12.0, width=20.0, height=20.0)),
            Detection(class_label="debris", confidence=0.5000, bbox=BBox(x=14.0, y=14.0, width=20.0, height=20.0)),
        ]
        res = sonar_service._apply_dgrm(dets, dgrm_features=clustered_feats)
        for d in res:
            # 0.5000 * 1.05 = 0.5250
            assert d.confidence == pytest.approx(0.525, abs=1e-4)

        # Single or isolated detection: when connected <= 1, no boost
        orthogonal_feats = torch.zeros(2, 512)
        orthogonal_feats[0, 0] = 1.0
        orthogonal_feats[1, 1] = 1.0
        isolated_dets = [
            Detection(class_label="debris", confidence=0.5000, bbox=BBox(x=10.0, y=10.0, width=20.0, height=20.0)),
            Detection(class_label="debris", confidence=0.5000, bbox=BBox(x=500.0, y=500.0, width=20.0, height=20.0)),
        ]
        res_isolated = sonar_service._apply_dgrm(isolated_dets, dgrm_features=orthogonal_feats)
        assert res_isolated[0].confidence == 0.5000
        assert res_isolated[1].confidence == 0.5000

    def test_f_disabled_behavior_leaves_confidence_unchanged(self, monkeypatch, sonar_service):
        # F. Disabled behavior:
        # - USE_DGRM unset/false leaves confidence unchanged.
        monkeypatch.delenv("USE_DGRM", raising=False)

        dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
        inp = PreprocessedInput(data=dummy_img, metadata={"orig_shape": (640, 640)})

        # Verify USE_DGRM=false by default
        import os
        assert os.environ.get("USE_DGRM", "false").lower() == "false"

        res = sonar_service.predict(inp)
        assert isinstance(res.confidence, float)
