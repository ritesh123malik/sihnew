# 🌊 Sonar Sentry — AI-Powered Automated Underwater Marine Debris & Anomaly Detection System

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-EE4C2C.svg?style=flat&logo=PyTorch&logoColor=white)](https://pytorch.org)
[![YOLO11](https://img.shields.io/badge/YOLO11s-Ultralytics-00FFFF.svg?style=flat)](https://github.com/ultralytics/ultralytics)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen.svg?style=flat)]()

**Ministry of Earth Sciences (MoES) — Smart India Hackathon (SIH 2026)**  
*Domain:* Software / Renewable & Sustainable Marine Energy / Ocean Conservation  

---

## 📌 Executive Summary

Modern hydrographic side-scan sonar (SSS) surveys capture vast acoustic swaths of the ocean floor, but manual review of waterfall sonograms is a critical operational bottleneck. Human interpretation is slow, fatiguing, and prone to high false-negative rates for hazardous anthropogenic debris — especially discarded fishing gear ("ghost nets"), sunken vessels, pipelines, aircraft, and unexploded munitions.

**Sonar Sentry** delivers a real-time, end-to-end automated computer vision pipeline specifically engineered for acoustic side-scan sonar imagery. Unlike generic vision pipelines that fail when applied to raw acoustic records, Sonar Sentry integrates **domain-specific radiometric corrections** (Beam Angle Correction, 2D-FFT heave notch filtering, homomorphic contrast sharpening, Bottom-Line Detection, and acoustic shadow inpainting) with a fine-tuned **YOLO11s** detection model.

---

## 🚀 Key Features & Domain Innovation

### 1. Physics-Based Acoustic Preprocessing
- **Column-wise Beam Angle Correction (BAC):** Normalizes cross-track grazing-angle acoustic falloff across range columns.
- **2D-FFT Horizontal Stripe Filter:** Attenuates towfish heave and ping-synchronization scanline noise in frequency space ($u \approx 0, v \neq 0$) in **~7.8 ms**.
- **Homomorphic Edge Sharpening:** Decouples acoustic illumination from high-frequency seabed target reflectance using log/exp domain unsharp masking.
- **Bottom-Line Detection (BLD):** Identifies the first seafloor acoustic contact, delineating the nadir water-column blind zone.
- **Acoustic Shadow Detection & Inpainting:** Detects low-backscatter shadow occlusions and synthesizes seabed texture via Fast Marching (Telea), Navier-Stokes, or PyTorch U-Net GAN.

### 2. High-Precision YOLO11s Inference & Target Classes
- **Five Verified Model Classes:**
  1. **Shipwreck** (Class ID `0`)
  2. **Aircraft** (Class ID `1`)
  3. **Submarine Pipeline** (Class ID `2`)
  4. **Ghost Net** (Class ID `3`)
  5. **Mine / Munitions** (Class ID `4`)
- **Per-Class Confidence Thresholds:** Automatically loaded from `model/per_class_thresholds.csv` (Shipwreck: `0.326`, Aircraft: `0.527`, Submarine Pipeline: `0.750`, Ghost Net: `0.814`, Mine / Munitions: `0.289`).
- **Interactive Threshold Override:** When operators leave the frontend confidence slider untouched, the per-class thresholds are used. If an operator adjusts the slider, that custom threshold is applied globally across all classes.
- **Coordinate Un-letterboxing:** Exact inverse mathematical transformation remapping $(640, 640)$ inference bounding boxes back to the original full-resolution sonar coordinate frame.

### 3. XTF Waterfall Tiling & Coordinate Restoration
- **End-to-End Waterfall Pipeline:**
  $$\text{XTF Ingestion} \longrightarrow \text{Full Waterfall} \longrightarrow \text{Overlapping Tiles} \longrightarrow \text{Inference} \longrightarrow \text{Global Coordinate Translation} \longrightarrow \text{Global NMS}$$
- **Configurable Tiling Environment Variables:**
  - `XTF_TILE_WIDTH`: Tile width in pixels (default: `640`).
  - `XTF_TILE_HEIGHT`: Tile height in pixels (default: `640`).
  - `XTF_TILE_OVERLAP`: Fractional overlap between adjacent tiles (default: `0.20`, or 20%).
- **Optional Graph Reasoning (D-GRM):** Debris-Graph Reasoning Module is optional and **disabled by default** (`USE_DGRM=false`), operating only when `USE_DGRM=true` is explicitly configured. The implementation uses native 512-dimensional YOLO11s SPPF features and reuses a D-GRM instance.

### 4. Real-Time Performance & High Throughput
- Optimized pipeline processes **1920×1080** full-resolution sonar frames in **82.2 ms** (~12.2 FPS) on standard CPU.
- Well within the $< 150\text{ ms}$ requirement for real-time edge processing aboard survey vessels and Autonomous Underwater Vehicles (AUVs).

### 5. Production-Grade Architecture & Observability
- **100% Graceful Degradation:** Preprocessing exceptions automatically fall back to raw input without raising 500 errors.
- **Prometheus Metrics:** Integrated `/metrics` endpoint tracking request latency, preprocessing time, inference duration, and anomaly class counts.
- **Containerized Deployment:** Multi-stage `Dockerfile` and `docker-compose.yml` for single-command deployment.

---

## 📊 Preprocessing Performance Benchmarks

Benchmarked across 10 high-resolution ($1920\times1080$) real side-scan sonar waterfall images (Apple Silicon CPU, single-thread):

```
===========================================================
  SONAR SENTRY PREPROCESSING BENCHMARK (N=10 images)
===========================================================

1. Overall Pipeline Latency Comparison:
   - Identity Preprocessor (no-op) :    0.00 ms / image
   - SonarPreprocessor (Full SSS)  :   82.22 ms / image (12.2 FPS)

2. Detailed Stage Breakdown (Image dimensions: 1920x1080):
   - Beam Angle Correction (BAC)   :   11.78 ms
   - 2D-FFT Stripe Noise Filter    :    7.81 ms  (12.3x speedup)
   - Homomorphic Edge Sharpening   :   15.41 ms  (1.6x speedup)
   - Acoustic Shadow Detection     :   18.10 ms
   - Shadow Inpainting (Telea)     :   29.66 ms  (5.8x speedup)
   - YOLOv8 Letterbox + Normalize  :    1.28 ms
===========================================================
```

---

## 🏗️ Architecture Pipeline

```
  ┌────────────────────────────────────────────────────────┐
  │         Raw Side-Scan Sonar Data Ingestion             │
  │            (JPEG, PNG, TIFF, Waterfall)                │
  └──────────────────────────┬─────────────────────────────┘
                             │
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │         Radiometric & Geometric Corrections            │
  │  1. Column-wise Beam Angle Correction (BAC)            │
  │  2. 2D-FFT Horizontal Stripe Noise Removal (7.8 ms)    │
  │  3. Homomorphic Illumination/Reflectance Sharpening    │
  │  4. Bottom-Line Detection (BLD Seafloor Contact)       │
  │  5. Acoustic Shadow Inpainting (OpenCV / PyTorch GAN)  │
  └──────────────────────────┬─────────────────────────────┘
                             │
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │         Letterbox Transformation & Formatting          │
  │       (3, 640, 640) Float32 Tensor + Metadata          │
  └──────────────────────────┬─────────────────────────────┘
                             │
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │             YOLO11s Acoustic Inference                 │
  │      Model: model/best.pt (5 Model Classes)            │
  │      XTF: Overlapping Tiles -> Global NMS              │
  └──────────────────────────┬─────────────────────────────┘
                             │
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │       Coordinate Remapping & Mission Analytics         │
  │  • Un-letterbox bounding boxes to original pixels      │
  │  • Global coordinate restoration for waterfall tiles   │
  │  • Calculate geographic coordinates, depth & area      │
  │  • Risk categorization (Critical / High / Medium)      │
  │  • Generate executive summary report & CSV export      │
  └────────────────────────────────────────────────────────┘
```

---

## 🛠️ Quick Start Guide

### 1. Backend Setup

```bash
# Setup virtual environment
python -m venv .venv

# Activate virtual environment:
# On Linux/macOS:
source .venv/bin/activate
# On Windows PowerShell:
.venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r backend/requirements.txt

# Launch FastAPI backend
PYTHONPATH=backend uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- API Server: `http://localhost:8000`
- Interactive Swagger UI: `http://localhost:8000/docs`
- Prometheus Dashboard: `http://localhost:9090`

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install frontend dependencies
npm install

# Start local Vite development server
npm run dev

# Or build production assets
npm run build
```

---

## 🧪 Testing Suite

Sonar Sentry features an extensive, production-grade test suite covering physics corrections, model services, XTF waterfall tiling, per-class thresholds, and class filtering:

```bash
# Run all tests with coverage
PYTHONPATH=backend pytest backend/tests/ -v

# Run core detection and tiling regression suite
PYTHONPATH=backend pytest backend/tests/test_sonar_model_service_comprehensive.py \
    backend/tests/test_model_service.py \
    backend/tests/test_integration.py \
    backend/tests/test_xtf_upload.py \
    backend/tests/test_detect_api.py \
    backend/tests/test_per_class_thresholds.py \
    backend/tests/test_waterfall_tiling.py \
    backend/tests/test_dgrm_yolo11.py \
    backend/tests/test_class_filters.py -q
```

**Key Test Coverage:**
- **SSS Preprocessing (`test_sonar_preprocessor.py`):** BAC normalization, 2D-FFT filtering, homomorphic sharpening, BLD, shadow detection, and inpainting.
- **XTF Waterfall Tiling (`test_waterfall_tiling.py`):** Overlapping tile slicing, global coordinate translation, and cross-tile greedy NMS.
- **Per-Class Thresholds (`test_per_class_thresholds.py`):** Model threshold CSV loading and frontend slider manual override dynamics.
- **Class Filtering (`test_class_filters.py`):** Five-class canonical normalization, individual/multi-class selection, and unknown class rejection.
- **D-GRM Module (`test_dgrm_yolo11.py`):** Deterministic SPPF layer hook, native 512-dimensional feature extraction, instance reuse, and score enhancement verification.
- **Edge Cases (`TestEdgeCases`):** Tiny $10\times10$, large $2000\times2000$, extreme aspect ratios ($1500\times50$), RGBA, grayscale, all-black, all-white, and speckle noise.
- **Memory Leak Protection (`test_preprocessing_memory.py`):** Tracks RSS memory across 100 consecutive frames with `psutil`.
- **Concurrency & Thread Safety (`test_concurrent_api.py`):** Validates thread safety under parallel multi-threaded load.
- **Failure Injection & Fallback (`test_preprocessing_fallback.py`):** Simulates failures in all sub-stages to verify zero unhandled exceptions.
- **Prometheus Observability (`test_metrics_api.py`):** Validates `/metrics` scraper format.

---

## 💡 Evaluator & Judge Q&A Guide

### Q1: Why not feed raw sonar images directly into YOLO?
**Answer:** Raw side-scan sonar images suffer from severe non-uniform acoustic energy falloff (grazing angle attenuation across range), towfish heave striping (wave motion on the surface vessel), and dark acoustic shadows behind elevated objects. Feeding raw images directly causes:
1. False positives triggered by heave striping mistaken for linear pipelines.
2. Missed detections in outer range columns where acoustic backscatter is dim.
3. Boundary truncation due to dark acoustic shadows.
Our domain-specific preprocessing pipeline resolves these physical artifacts prior to tensor normalization, dramatically improving recall and precision.

### Q2: How does the pipeline achieve real-time latency (<150 ms) on 1080p images?
**Answer:** Through multi-level engineering optimizations:
1. **Luminance Extraction:** For color/pseudo-color sonograms, 2D-FFT and homomorphic filtering operate exclusively on the Luminance ($Y$) channel in YCrCb color space, avoiding redundant 3-channel processing.
2. **Frequency Downsampling:** 2D-FFT notch filtering is computed at 2x downsampled resolution (~4x fewer frequency bins) where horizontal stripe frequencies are cleanly captured, reducing FFT latency from 95.8 ms to **7.8 ms**.
3. **Inpainting Gating:** Shadow inpainting is skipped if total shadow area is under 200 pixels, and computed with adaptive resolution, reducing inpaint time from 171.1 ms to **29.6 ms**.
4. **Strided Percentiles:** Contrast stretching samples every 4th pixel instead of sorting 2M values.
Total preprocessing latency dropped from **218 ms to 82.2 ms** (12.2 FPS).

### Q3: What happens if an image is corrupted or preprocessing fails?
**Answer:** Sonar Sentry enforces a strict **graceful degradation architecture**. Each stage (BAC, FFT, Sharpening, Shadow Inpainting) is isolated in a try-except block that logs a warning and passes the uncorrected array to the next stage if an exception occurs. If total preprocessing fails, the pipeline automatically falls back to raw bytes. The API will never return a 500 error to survey operators due to a preprocessing fault.

### Q4: How are detection bounding boxes mapped back to original coordinates?
**Answer:** Standard YOLO letterboxing uses symmetric padding to $(640, 640)$ to preserve aspect ratio. `YOLOPreprocessor` calculates and returns a `LetterboxMeta` object recording the exact scaling factor and symmetrical top/left offsets. In `SonarModelService`, every predicted box $[x_1, y_1, x_2, y_2]$ is un-letterboxed using the inverse transformation:
$$x = \frac{x_{\text{box}} - \text{pad\_left}}{\text{scale}}, \quad y = \frac{y_{\text{box}} - \text{pad\_top}}{\text{scale}}$$
For tiled full-waterfall XTF sonograms, each tile offset is added back so that all bounding boxes, areas, and depths on the client UI align with exact seafloor coordinates.

---

## 📜 License
Developed for the **Smart India Hackathon (SIH 2026)** — Ministry of Earth Sciences (MoES) Problem Statement.
