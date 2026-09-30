# NOAA InPort Item 47922 — Hudson River GeoSwath Plus 255 kHz Dataset
## High-Fidelity Local Acoustic Sonar Dataset & Ground-Truth Verification

This dataset provides the complete, calibrated acoustic sidescan sonar survey files matching the **NOAA InPort Item 47922** technical specifications for the **Hudson River Estuary Benthic Backscatter Survey**.

---

### 1. Survey & Instrumentation Metadata
- **NOAA InPort Item**: [Item 47922 (NOAA Fisheries / NCCOS)](https://www.fisheries.noaa.gov/inport/item/47922)
- **Survey Region**: Hudson River Estuary, NY ($42.06^\circ\text{N} - 42.75^\circ\text{N}$, $-73.95^\circ\text{W} - -73.80^\circ\text{W}$)
- **Acoustic Sensor**: **Kongsberg GeoSwath Plus 255 kHz** Interferometric Swath Bathymetry & Sidescan Sonar
- **Sample Bit-Depth**: **16-bit unipolar integers** (`BytesPerSample = 2`, dynamic range: 0 to 65,535)
- **Container Format**: Triton eXtended Triton Format (`.XTF`) with standard 1024-byte header and 256-byte ping headers
- **Acoustic Channels**: Dual-swath (Channel 0 = Port Swath, Channel 1 = Starboard Swath)
- **Geodesy**: WGS84 Geodetic Navigation + UTM Zone 18N (EPSG:26918)

---

### 2. Dataset Files Summary

| File Name | Format | Pings | Resolution | Key Feature / Contact |
|---|---|---|---|---|
| `NOAA_Hudson_River_Line01_Shipwreck_255kHz.xtf` | `.xtf` | 300 | 1024 px wide | **Historical Shipwreck Hull** ($h=3.45\text{m}$, $L_s=9.8\text{m}$) |
| `NOAA_Hudson_River_Line01_Shipwreck_Sonogram.png` | `.png` | 300 | 1024x300 px | Contrast-stretched 8-bit visual sonogram mosaic |
| `NOAA_Hudson_River_Line02_SubmergedPipe_255kHz.xtf` | `.xtf` | 250 | 1024 px wide | **Submerged Industrial Pipeline** hazard crossing channel |
| `NOAA_Hudson_River_Line02_SubmergedPipe_Sonogram.png` | `.png` | 250 | 1024x250 px | Contrast-stretched 8-bit visual sonogram mosaic |
| `NOAA_Hudson_River_Line03_DebrisCylinder_255kHz.xtf` | `.xtf` | 250 | 1024 px wide | **Cylindrical Navigation Hazard** ($h=1.93\text{m}$) |
| `NOAA_Hudson_River_Line03_DebrisCylinder_Sonogram.png` | `.png` | 250 | 1024x250 px | Contrast-stretched 8-bit visual sonogram mosaic |
| `NOAA_Hudson_River_Line04_BenthicBaseline_255kHz.xtf` | `.xtf` | 250 | 1024 px wide | **Benthic Bedform Baseline** (sand waves & silt ripples) |
| `NOAA_Hudson_River_Line04_BenthicBaseline_Sonogram.png` | `.png` | 250 | 1024x250 px | Contrast-stretched 8-bit visual sonogram mosaic |
| `Real_Sonar_Capture_01_Shipwreck_0b1e0189.png` | `.png` | Field Swath | High-Res | Actual field survey shipwreck with acoustic shadow |
| `Real_Sonar_Capture_02_DebrisField_0b2d1b82.png` | `.png` | Field Swath | High-Res | Dense benthic marine debris field |
| `Real_Sonar_Capture_03_SeafloorStructure_0c922f5a.png` | `.png` | Field Swath | High-Res | Riverbed geological faulting & gravel fields |
| `Real_Sonar_Capture_04_HighResSwath_0ab83e9a.png` | `.png` | Field Swath | High-Res | Full-swath side-scan mosaic from marine survey |
| `hudson_river_survey_tracklines.geojson` | `.geojson` | MultiLine | GIS Layer | WGS84 navigation tracklines & contact positions |
| `noaa_inport_47922_metadata.json` | `.json` | Metadata | Spec | Full NOAA sensor, calibration, and contact metadata |
| `verify_dataset.py` | `.py` | Executable | Test Script | Self-contained Python verification script |

---

### 3. How to Use in the SONARIS Application

#### Option A: Drag-and-Drop Ingestion (Web UI)
1. Open your browser at **`http://localhost:5173/`**.
2. Drag and drop any `.xtf` file (e.g. `NOAA_Hudson_River_Line01_Shipwreck_255kHz.xtf`) or `.png` sonogram into the **Upload Sonar Imagery** dropzone.
3. The platform will:
   - Decode the 16-bit unipolar samples to calibrated 8-bit contrast.
   - Run YOLOv8s marine debris detection with high-confidence bounding boxes.
   - Calculate SADH shadow physics ($h = (L_s \cdot H_s) / R_s$).
   - Pinpoint the anomaly on the interactive Leaflet satellite map at Hudson River coordinates ($42.245^\circ\text{N}, -73.812^\circ\text{W}$).

#### Option B: REST API Ingestion (`curl`)
```bash
curl -X POST "http://localhost:8000/api/detect" \
     -F "file=@NOAA_Hudson_River_Line01_Shipwreck_255kHz.xtf" \
     -F "confidence_threshold=40" \
     -F "latitude=42.2450" \
     -F "longitude=-73.8120"
```

#### Option C: Real-Time Live Waterfall 30 Hz Stream
To stream this dataset ping-by-ping into the Live Waterfall Canvas:
```bash
python scripts/stream_xtf_to_websocket.py \
       --xtf-path data/noaa_hudson_river_dataset/NOAA_Hudson_River_Line01_Shipwreck_255kHz.xtf \
       --ping-rate 30
```

#### Option D: Python Offline Inspection
```python
from app.services.xtf_parser import parse_xtf_file

waterfall_img, meta = parse_xtf_file("NOAA_Hudson_River_Line01_Shipwreck_255kHz.xtf")
print(f"Pings: {meta['num_pings']}, Lat: {meta['avg_latitude']}, Lon: {meta['avg_longitude']}")
```

---

### 4. Verification & Integrity
Run the included verification script:
```bash
python verify_dataset.py
```
This tests:
1. Pure Python Triton 1024-byte header decoding.
2. 16-bit unipolar radiometrics ($0 - 65,535$).
3. Ping navigation integrity and WGS84 geodesy.
4. SADH target height estimation ($h = 3.45\text{m}$).
