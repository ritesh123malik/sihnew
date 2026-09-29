# Sonar Anomaly Detection Model

- **Architecture:** Ultralytics YOLO11s (`yolo11s`)
- **Author:** Sanyam (`2007sanyam@gmail.com`)
- **Training Run:** `yolo11s_sonar_20260928_140551` (Google Colab GPU)
- **Input Resolution:** `800x800`
- **Classes (5):** `shipwreck`, `aircraft`, `submarine_pipeline`, `ghost_net`, `mine_munitions`
- **Files:**
  - `best_yolo11s.onnx` — Production ONNX runtime engine (low memory, high speed)
  - `best_yolo11s.pt` / `best.pt` — PyTorch checkpoint weights

