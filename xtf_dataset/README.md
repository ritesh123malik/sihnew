# 🌊 SONARIS — Official XTF Benchmark Dataset

Welcome to the **Official eXtended Triton Format (`.xtf`) Benchmark Dataset** for **SONARIS**. This directory provides curated, verified side-scan sonar hydrographic survey lines ready for prototype evaluation, jury demonstration, and automated pipeline benchmarking.

---

## 📂 Dataset Manifest

| File | Size | Channels / Freq | Primary Target / Feature | Recommended Lat / Lon | Expected Result |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`01_NOAA_Shipwreck_Survey_Line01_255kHz.xtf`** | 713 KB | Port & Stbd (255 kHz) | Submerged Shipwreck Hull & Shadow | `40.7128°N, 74.0060°W` | **Target: Shipwreck** (~72–88% Conf), Height est: ~1.2m |
| **`02_Submerged_Pipeline_Corridor_Line02_255kHz.xtf`** | 595 KB | Port & Stbd (255 kHz) | Submarine Pipeline Infrastructure | `40.7140°N, 74.0080°W` | **Target: Pipeline / Anomaly** with acoustic shadow |
| **`03_Marine_Debris_Field_Line03_255kHz.xtf`** | 595 KB | Port & Stbd (255 kHz) | Industrial Cylinder Debris | `40.7155°N, 74.0110°W` | **Target: Marine Debris / Hazard**, Low/Medium Risk |
| **`04_Benthic_Seafloor_Baseline_Line04_255kHz.xtf`** | 595 KB | Port & Stbd (255 kHz) | Flat Sandy Silt Bed (Control Run) | `40.7180°N, 74.0150°W` | **0 False Positives** (Clean seabed clearance) |
| **`05_Deepwater_Towfish_Survey_Line05_300kHz.xtf`** | 29 KB | Dual Channel (300 kHz) | Rapid Survey Swath Ping Stream | `13.0827°N, 80.2707°W` | Real-time packet parsing & waterfall rendering |

---

## 🚀 How to Showcase in Prototype

### Method 1: Ingest via "Live Survey" Mode
1. Open the prototype website: [https://sihnew-frontend.onrender.com/live-survey](https://sihnew-frontend.onrender.com/live-survey) (or `http://localhost:5173/live-survey`).
2. In the top-right survey control bar, click **"📂 Ingest XTF / Sonar Image"**.
3. Select any `.xtf` file from this folder (e.g., `01_NOAA_Shipwreck_Survey_Line01_255kHz.xtf`).
4. Watch the pipeline:
   - Triton packet de-interleaving and slant range correction (BAC normalization) execute.
   - The generated acoustic waterfall swath renders across the **Active Towfish Acoustic Waterfall** canvas.
   - The real-time target detector logs anomalies directly into the **Real-Time Ping Detections** feed.
   - Click **"View Mission Report →"** on the notification toast to view the complete hydrographic audit.

### Method 2: Launch via "Mission Launchpad"
1. Navigate to [https://sihnew-frontend.onrender.com/launch](https://sihnew-frontend.onrender.com/launch).
2. Drag and drop any `.xtf` file into the upload zone.
3. Configure Towfish Depth range (`0.0m – 30.0m`) and Confidence Slider (`20%`).
4. Click **"Execute Acoustic Pipeline →"**.

---

## 🛠️ Technical Specifications
- **Format**: Triton Elics eXtended Triton Format (`.xtf`), Revision 1.23
- **Header**: Standard 1024-byte file header with ping packet headers
- **Physics**: Compatible with Shadow-Altitude-Depth-Height (`SADH`) equation:
  $$h = \frac{L_s \times H_s}{R_s}$$
