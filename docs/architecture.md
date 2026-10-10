# Sonaris architecture

[← README](../README.md) · [API](api.md) · [Configuration](configuration.md)

## Application boundaries

Sonaris consists of a React/Vite single-page application and a FastAPI service. SQLAlchemy stores runs, detections, and reports in SQLite by default; file storage is local. Supabase integration is optional. The repository also contains research modules and historical evaluation artifacts that are not all part of the default serving path.

| Responsibility | Source |
| :--- | :--- |
| Lifecycle, middleware, router mounting | `backend/app/main.py` |
| Settings and database initialization | `backend/app/config.py`, `backend/app/database.py` |
| Upload validation and orchestration | `backend/app/api/routes/detect.py` |
| Preprocessor/model composition | `backend/app/services/factory.py` |
| Inference abstraction | `backend/app/services/inference_service.py` |
| ONNX/PyTorch serving | `backend/app/services/sonar_model_service.py` |
| XTF parsing and tiled inference | `backend/app/services/xtf_parser.py`, `waterfall_tiling.py` |
| Acoustic preprocessing | `backend/app/preprocessing/sonar_preprocessor.py` |
| Mapping and physics estimates | `backend/app/services/georeference.py`, `sadh_physics.py` |
| Persistence | `backend/app/models/orm.py`, `backend/app/repositories/` |
| HTTP frontend client | `frontend/src/api/client.js` |
| Screen routing | `frontend/src/App.jsx` |
| Streaming transport | `backend/app/api/routes/waterfall.py` |

## Upload-to-report lifecycle

1. The frontend sends a multipart file with scan metadata and optional filters.
2. `/api/detect` checks contents, MIME/signature, size, depth ordering, and accepted metadata labels.
3. The original file is saved and a database run is created with status `processing`.
4. Images enter inference directly. XTF files are parsed into a waterfall, cached as PNG, and split into overlapping tiles.
5. The factory-selected preprocessor applies enabled acoustic stages and prepares model input. The model service attempts available ONNX inference, with a PyTorch fallback path.
6. Model coordinates are remapped; tiled results are translated and merged with global NMS.
7. Results are normalized and filtered by confidence, class, and size. Georeferencing and heuristic shadow fields are added; patch generation is attempted.
8. Detections and run metadata are persisted. Automatic report creation is attempted independently; failure is logged without necessarily failing the completed scan.
9. Results, map points, report history, and export endpoints expose the stored information.

## Processing defaults

Beam-angle correction, stripe filtering, and sharpening are enabled. Shadow inpainting is disabled. The preprocessor target defaults to 640×640; the ONNX input shape and PyTorch inference call can use a different size (the latter uses 800 in the current service).

The factory supports `sonar` and `mock`. Mock predictions are development placeholders. D-GRM and model-level SADH are opt-in; separate route-level physics enrichment still runs. WERB, graph layers, GAN modules, and the six-class training YAML are research components, not proof that the shipped checkpoint was trained with all of them.

## Storage and optional cloud integration

The default SQLite database is relative to the process working directory. Uploads/outputs default to directories under `backend/data/`. Some export and patch services use separate root-relative output directories. Persisting only `data/` is therefore insufficient; see [deployment.md](deployment.md).

Database initialization creates tables and includes ad hoc SQLite column additions. There is no general versioned migration system configured. Supabase clients/sync helpers use optional credentials and the supplied SQL schema, but should be validated for the selected workflow; they are not an automatic replacement for all local persistence.

## Streaming boundary

The mounted waterfall router has an in-memory connection manager. It broadcasts producer JSON or decoded XTF rows to connected sockets. It does not invoke upload inference, persist streamed pings, or distribute messages across worker processes. The active Live Survey screen uses upload handling and demonstration displays. Its unused standalone streaming hook was removed during cleanup; static status labels do not prove a live sensor connection.

## Interpretation limits

Box-coordinate conventions and physical-unit assumptions differ between parts of the code. The detect route's shadow estimates use fixed image dimensions and metadata-derived altitude proxies. Survey-derived bathymetry generation and synthetic salvage visualization are different endpoints. Keep these distinctions visible when demonstrating the application or reporting evaluation results.

Preprocessing fallback improves resilience but does not guarantee every invalid input produces a successful response. Corrupt files, unavailable models, database failures, and export errors remain possible.
