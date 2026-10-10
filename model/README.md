# Sonaris model artifacts

[← README](../README.md#model-evidence-and-reproducibility)

The checked-in `run_config.json` identifies **YOLO11s** with classes `shipwreck`, `aircraft`, `submarine_pipeline`, `ghost_net`, and `mine_munitions`. Older YOLOv8/four-class comments elsewhere are historical; the serving model's own metadata is the authoritative class mapping at runtime.

| Artifact | Purpose |
| :--- | :--- |
| `best.pt` | Bundled PyTorch checkpoint. |
| `best.onnx` | Bundled ONNX serving artifact. |
| `run_config.json` | Training/evaluation metadata reconstructed after account migration. |
| `per_class_thresholds.csv` | Class confidence cutoffs and recorded precision/recall/F1 values. |
| `test_final_at_chosen_conf.json` | Recorded final test metrics at confidence 0.4765. |
| `speed_report.json` | Recorded latency/FPS at input size 800; hardware/runtime not specified. |
| `metrics.csv` | Additional recorded metrics. |

The source metadata contains Colab-specific paths. These are provenance, not paths to configure on your machine. Metadata alone does not establish a fully reproducible training run or prove the binary artifacts were regenerated from the current source.

## Serving

Set `MODEL_PROVIDER=sonar`. The service resolves a PyTorch checkpoint from `MODEL_PATH` and fallback candidates, then separately attempts ONNX discovery. An available ONNX model can take precedence over the selected PyTorch file. Keep both artifacts consistent when changing a model; inspect logs and actual labels. ONNX load/inference failure can fall back to PyTorch.

The standard preprocessor defaults to 640×640, while the serving code uses ONNX input dimensions or an 800-pixel PyTorch call. Do not assume the preprocessor setting overrides every inference size.

`USE_DGRM` and `USE_SADH` default to false and require process environment variables. Their presence does not prove they were used to train the checkpoint. The separate `configs/train_config.yaml` describes an experimental six-class WERB/D-GRM/SADH configuration; it is not the documented five-class YOLO11s run.

## Interpreting metrics

Recorded precision is 0.9436, recall 0.7573, mAP50 0.7468, and mAP50–95 0.6407. The speed artifact records 27.9 ms/image (35.8 FPS), not upload-to-report latency. Reproduce results with a documented dataset split, hardware/runtime, preprocessing, checkpoint hash, and confidence policy before making new performance claims.

Model and dataset redistribution terms are not established by a project license file; none is currently present. Preserve artifact provenance and review upstream terms when distributing weights or data.
