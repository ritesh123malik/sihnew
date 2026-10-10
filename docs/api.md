# Sonaris API reference

[← README](../README.md) · [Configuration](configuration.md)

Local base: `http://localhost:8000`. Interactive schemas: [/docs](http://localhost:8000/docs); machine-readable schema: [/openapi.json](http://localhost:8000/openapi.json).

The API currently has no application authentication. Do not expose administrative and deletion routes publicly without access controls. A process-local HTTP rate limiter is configured at 200 requests per 60 seconds; it is not a distributed quota system.

## Analyze a scan

`POST /api/detect` accepts `multipart/form-data`. XTF convenience aliases are `POST /api/detect/xtf` and `POST /api/xtf/upload`.

| Field | Default on `/api/detect` | Behavior |
| :--- | :--- | :--- |
| `file` | Required for processing | JPEG, PNG, TIFF, or `.xtf`; 500 MB default maximum. |
| `latitude` | `12.9716` | Scan origin; provide actual metadata for meaningful locations. |
| `longitude` | `80.2520` | Scan origin. |
| `sonar_type` | `Side-Scan` | `Side-Scan`, `Multibeam`, `Synthetic Aperture`, `SSS-Dual`. These labels do not guarantee equivalent validation across sensor types. |
| `resolution` | `0.1 m/px` | `0.1 m/px`, `0.5 m/px`, `1 m/px`, `0.05 m/px`, or legacy `1024x768`. Prefer physical units for georeferencing. |
| `depth_min` / `depth_max` | `10` / `50` | Minimum must be less than maximum. |
| `confidence_threshold` | Omitted | Omission uses per-class CSV thresholds. A supplied integer is clamped to 0–100 for final filtering. |
| `selected_classes` | Empty | Comma-separated labels; empty means no class restriction. |
| `min_object_size` | `10` | Compares the larger box dimension directly; use `0` to disable. See unit caveat below. |

The XTF aliases default to `SSS-Dual`, `1024x768`, depths `0`–`30`, and minimum size `5`. Override resolution with known physical sampling metadata rather than interpreting `1024x768` as meters per pixel.

```bash
curl --fail-with-body http://localhost:8000/api/detect \
  -F 'file=@demo_data/0b1e0189-vlcsnap-2025-12-09-20h50m42s408.png;type=image/png' \
  -F 'selected_classes=shipwreck,ghost_net' \
  -F 'confidence_threshold=50' \
  -F 'min_object_size=0'
```

Response fields include `success`, `run_id`, `mission_id`, `status`, `scan_metadata`, `detection_summary`, `detections`, `model`, `timestamps`, and `waterfall_url`. Each detection can include a class label, confidence in `[0,1]`, risk level, box, estimated dimensions, coordinates, physics fields, and patch/mask URLs. Empty detections are valid. A completed detection does not guarantee automatic report creation succeeded; report generation failures are logged separately.

### Coordinate and filter notes

The response schema defines `bbox` as `x`, `y`, `width`, `height`, but does not declare a universal unit. Model, tiling, and downstream display/georeference paths contain differing assumptions. Do not blindly interpret all returned boxes as normalized coordinates or all as pixels without validating the active path. The size filter compares raw box dimensions, which can remove small or normalized boxes. The README examples use `min_object_size=0` to avoid this ambiguity.

Georeferencing uses box offsets, scan origin, resolution, and available heading. The legacy resolution `1024x768` is accepted, but the numeric parser reads its leading number; this is not calibrated meters-per-pixel input. Shadow-height fields in `/api/detect` use heuristics and fixed image assumptions. Check these values against survey ground truth before interpreting them as measurements.

## Route directory

Paths below are mounted by `backend/app/main.py`.

| Method | Path | Purpose |
| :--- | :--- | :--- |
| POST | `/api/predict` | JPEG/PNG upload; compact `prediction`, `model`, `request_id` response. |
| GET | `/api/runs` | Run history; `page`, `page_size`, optional `status`. |
| GET | `/api/runs/{run_id}` | Run details and detections. |
| GET | `/api/runs/{run_id}/file` | Original/rendered file. |
| GET | `/api/waterfall/{run_id}` | Waterfall preview. |
| POST | `/api/runs/{run_id}/instances` | New report instance with JSON `confidence_threshold`. |
| DELETE | `/api/runs/{run_id}` | Delete a run. |
| GET | `/api/detections` | Detection query. |
| GET | `/api/map/points` | Map point data. |
| GET | `/api/anomalies` | Anomaly list; alias `/api/get_anomalies`. |
| GET | `/api/anomalies/{anomaly_id}` | Anomaly details. |
| GET | `/api/anomaly/{anomaly_id}/patch` | Detection patch. |
| GET | `/api/anomaly/{anomaly_id}/mask` | Detection mask. |
| GET | `/api/reports` | Reports; `page`, `page_size`, `search`, `status`. |
| GET | `/api/reports/{report_id}` | Report details. |
| GET | `/api/reports/{report_id}/export` | Report export; inspect `/docs` for format parameters. |
| DELETE | `/api/reports/{report_id}` | Delete a report. |
| GET | `/api/models` | Model manager inventory. |
| POST | `/api/models/{name}/reload` | Reload a model-manager entry. |
| GET | `/api/ab/tests` | Defined A/B experiments. |
| GET | `/api/ab/tests/{test}/variant` | Variant selection; optional `session_id`. |

The `/v1` aggregator re-mounts detect, runs, waterfall, health, reports, predict, and anomalies routers. For example, the versioned detect URL is `/v1/api/detect`, **not** `/api/v1/detect`. Export, salvage, bathymetry, models, and A/B routers are not included in that aggregator.

### Export routes

| Method | Path | Result |
| :--- | :--- | :--- |
| GET | `/api/export/detections/csv` | CSV; alias `/api/export/csv`. |
| GET | `/api/export/detections/json` | JSON download. |
| GET | `/api/export/runs/{run_id}/report` | Structured report; currently `fmt=json` only. |
| GET | `/api/export/geojson` | GeoJSON. |
| GET | `/api/export/dossier` | PDF dossier. |
| GET | `/api/export/swath` | Swath export. |
| GET | `/api/export/kml` | KML. |
| GET | `/api/export/heatmap` | Heatmap. |
| GET | `/api/export/detection/{detection_id}` | Individual detection export. |
| POST | `/api/export/mosaic` | Mosaic; JSON list of run IDs; alias `/api/export/geotiff/mosaic`. |
| GET | `/api/export/geotiff/{detection_id}/bounds` | GeoTIFF bounds. |
| GET | `/api/export/geotiff/{detection_id}/render` | GeoTIFF render. |

GeoJSON, dossier, swath, KML, and heatmap have `/api/export/runs/{run_id}/…` aliases. CSV/JSON accept optional `run_id`, `limit` (default 1000), and `offset` (default 0). Specialized exports require suitable stored data; endpoint presence alone does not guarantee geospatial accuracy.

### Experimental survey endpoints

- `GET /api/salvage/route` and `/api/salvage/runs/{run_id}/route`: recovery planning; `cruising_speed` defaults to 8 knots. With no detections, returns `source: simulated_tactical_scenario`.
- `GET /api/salvage/bathymetry/mesh` and `/api/salvage/runs/{run_id}/bathymetry`: synthetic terrain generated from random waterfall values, even when a run ID is supplied.
- `POST /api/bathymetry/generate`: multipart `file` plus query parameters `H_s=15`, `R_s=50`, `sample_spacing=0.1`, `ping_interval=0.5`, `vessel_speed=2`. Returns metadata, shadow estimates, a point cloud capped at 5000 points, and grid statistics.
- `POST /api/bathymetry/export-geotiff/{survey_id}`: writes an export and returns its filesystem path and a URL. No static `/exports` mount is configured in the main app, so that returned URL is not automatically downloadable. The implementation also has a synthetic fallback for an undecodable image.

## WebSocket transport

Connect to `ws://localhost:8000/ws/waterfall`; aliases are `/ws` and `/api/waterfall`. HTTPS deployments require `wss://`.

The server sends a `type: status` welcome message. A producer can then send JSON:

```json
{"type":"ping","ping_number":1,"waterfall_chunk":[18,42,98,210,74,23],"detections":[]}
```

The handler broadcasts a `type: ping` message with the supplied row/detections and a server timestamp to connected clients. Binary messages are passed to the XTF parser and broadcast as rows; arbitrary partial byte fragments are not guaranteed to parse. There is no per-ping detector call, durable stream store, mission isolation, or cross-process broadcast broker in this handler.

## Health and errors

- `/api/health` and `/health`: service health.
- `/api/health/detailed` and `/health/detailed`: detailed state.
- `/api/health/ready` and `/health/ready`: readiness.
- `/api/health/live` and `/health/live`: liveness.
- `/metrics`: Prometheus text exposition.

Detection-specific errors use an envelope like:

```json
{"success":false,"error":{"code":"MODEL_UNAVAILABLE","message":"The prediction service is currently unavailable."}}
```

Common codes are `NO_FILE`, `INVALID_FILE_TYPE`, `FILE_TOO_LARGE`, `INVALID_METADATA` (400), `RUN_NOT_FOUND` / `REPORT_NOT_FOUND` (404), `MODEL_UNAVAILABLE` (503), and `INFERENCE_FAILED` (500). FastAPI validation and other route exceptions can use different shapes. Certain invalid-XTF branches pass a message to an exception class that does not accept one, so malformed XTF may yield a server error rather than the intended client error.
