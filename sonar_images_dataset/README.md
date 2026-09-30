# 🎯 SONARIS — Official Sonar Images Showcase Dataset

Welcome to the **Official Sonar Images Showcase Dataset** for **SONARIS**. This directory contains real-world, high-definition side-scan sonar image captures formatted for live jury demonstration, target recognition benchmarking, and instant interactive testing.

---

## 📂 Image Catalog & Ground Truth

| File | Resolution | Target Category | Model Confidence | SADH Estimated Height | Recommended Use |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`01_Shipwreck_Hull_HighConfidence_88pct.png`** | 1024 × 768 | Shipwreck Hull & Keel Structure | **88% – 89%** | **~11.2m** (High Risk) | ⭐ **Primary Showcase File**: Highlights large shipwreck keel with deep acoustic shadow |
| **`02_Shipwreck_Keel_Acoustic_Shadow_75pct.png`** | 800 × 600 | Shipwreck Shadow Anomaly | **75%** | **~0.86m** (Medium Risk) | Excellent demonstration of acoustic shadow segmentation |
| **`03_Shipwreck_Wreckage_Structure_72pct.png`** | 1024 × 768 | Wreckage Hull Structural Scatter | **72%** | **~0.92m** (Medium Risk) | Shows high-relief backscatter against textured seabed |
| **`04_Shipwreck_Debris_Field_71pct.png`** | 800 × 600 | Shipwreck Target & Scatter | **71%** | **~0.76m** (Medium Risk) | Baseline prototype evaluation image |
| **`05_Dual_Anomaly_Marine_Debris_Field.png`** | 1024 × 768 | Multi-Target (Debris + Anomaly) | **70% & 53%** | **~0.85m** | Shows multi-target identification in a single swath |
| **`06_Towfish_Telemetry_RTSP_Capture.png`** | 1280 × 720 | Live Vessel Stream Telemetry | **70% & 22%** | **~1.05m** | RTSP towfish feed capture with telemetry overlay |
| **`07_Submerged_Pipeline_Infrastructure_Swath.png`** | 640 × 640 | Submerged Linear Pipeline | **60%** | **~10.1m** (Low Risk) | Continuous seafloor infrastructure demonstration |
| **`08_Benthic_Seafloor_Flat_Baseline.png`** | 640 × 640 | Flat Sandy Benthic Baseline | **Control Run (0 Targets)** | **0.0m** | True negative test; confirms zero false-alarm rate on clean seabed |
| **`09_Debris_Cylinder_Anomaly_Swath.png`** | 640 × 640 | Marine Debris Cylinder | **62%** | **~0.75m** | Munitions / debris hazard audit |
| **`10_HighRes_Seabed_Acoustic_Swath.png`** | 1280 × 720 | High-Definition Survey Swath | **62%** | **~0.68m** | Comprehensive full-swath bathymetry & georeferencing |

---

## 🚀 How to Showcase in Prototype

### Method 1: Instant Waterfall Rendering (Live Survey)
1. Open [https://sihnew-frontend.onrender.com/live-survey](https://sihnew-frontend.onrender.com/live-survey) (or `http://localhost:5173/live-survey`).
2. Click **"📂 Ingest XTF / Sonar Image"** in the survey toolbar.
3. Select **`01_Shipwreck_Hull_HighConfidence_88pct.png`** (or any file in this directory).
4. **Immediate Results**:
   - The entire image is rendered instantly onto the **Active Towfish Acoustic Waterfall** canvas.
   - The Port (50m) and Starboard (50m) swaths are divided by the central cyan dashed **Nadir Track** line.
   - Neon amber/red bounding boxes with corner reticles and confidence badges (`SHIPWRECK 88%`) overlay the target automatically.
   - Click **"View Mission Report →"** in the notification toast to view the complete hydrographic audit ledger, SADH physics calculations, and interactive 3D bathymetry.

### Method 2: Comprehensive Mission Audit (Launchpad)
1. Open [https://sihnew-frontend.onrender.com/launch](https://sihnew-frontend.onrender.com/launch).
2. Upload any image from this folder.
3. Adjust confidence threshold slider and click **"Execute Acoustic Pipeline →"**.
