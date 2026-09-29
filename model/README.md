# Model

This folder holds the Colab-trained YOLOv8s marine-debris checkpoint (original baseline).

- **Architecture:** Ultralytics YOLOv8s (`yolov8s`)
- **Source run:** `sih2026_yolov8s_marine_debris`
- **File:** `best.pt` / `best.onnx`
- **Input Resolution:** `640x640`
- **Classes in the checkpoint:** `shipwreck`, `pipe`, `cylinder`, `net`

The backend loads this file when `MODEL_PROVIDER=sonar`.
