# Sonaris configuration

[← README](../README.md) · [Deployment](deployment.md)

## Two environment-loading mechanisms

`backend/app/config.py` uses Pydantic Settings with `env_file=".env"`, relative to the working directory. The recommended launch directory is the repository root. Process environment values override dotenv values. Settings are cached: restart after changes.

Other modules read `os.environ` directly. Pydantic does not export dotenv values into that mapping. Set these in your process/container environment:

```bash
export XTF_TILE_WIDTH=640
export XTF_TILE_HEIGHT=640
export XTF_TILE_OVERLAP=0.20
export USE_DGRM=false
export USE_SADH=false
export WATCHDOG_DISABLE=1
python -m uvicorn app.main:app --app-dir backend --port 8000
```

PowerShell equivalent for a single switch: `$env:WATCHDOG_DISABLE = "1"`. Docker `--env-file .env` exports values into the container environment, unlike Pydantic's dotenv parsing alone.

Tile sizes must be positive integers. Overlap must be at least 0 and less than 1. Invalid values fall back to 640×640 and 0.20. The application sets `YOLO_OFFLINE=1` and `ULTRALYTICS_AUTOINSTALL=0` with `setdefault` at import time.

## Backend settings

See the [README table](../README.md#configuration) for common settings. Additional options:

| Setting | Default | Notes |
| :--- | :--- | :--- |
| `UPLOAD_DIR` | `<repo>/backend/data/uploads` | Original uploads. |
| `OUTPUT_DIR` | `<repo>/backend/data/outputs` | StorageService outputs; not all export paths. |
| `DEBUG` | `false` | SQLAlchemy SQL logging. |
| `SSS_SHADOW_THRESHOLD` | `0.15` | Shadow processing parameter. |
| `YOLO_TARGET_SIZE` | `[640,640]` | JSON tuple/list syntax for environment values. |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | Declared setting; current main app does not use it to restrict CORS. |
| `API_PREFIX` | `/api` | Declared setting; routes largely hard-code their paths. |
| `CORS_ORIGINS` | Local origins plus `*` | Declared setting; current middleware instead uses an HTTP(S)-wide regex. |

`DEFAULT_CONFIDENCE_THRESHOLD` and `DEFAULT_MIN_OBJECT_SIZE` exist in Settings, but `/api/detect` declares its own defaults. Use the route contract rather than assuming every Settings field controls endpoint behavior.

### Model selection

`MODEL_PATH` selects a PyTorch checkpoint, with fallback discovery when the configured path cannot be found. The service independently searches for ONNX files such as `model/best.onnx` and prefers an available ONNX session. Changing `MODEL_PATH` alone therefore does not ensure an existing ONNX artifact is replaced. Keep artifacts and class metadata aligned and inspect startup logs.

Thresholds also exist in several locations. The detect route reads `model/per_class_thresholds.csv`; the model service has its own candidate order starting with `backend/app/configs/per_class_thresholds.csv`. Consolidation is a roadmap item.

### Supabase

Local operation requires no cloud values. For backend integration, provide a full `https://…supabase.co` URL and the appropriate key in `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, or `SUPABASE_ANON_KEY`. Inspect the chosen service's key precedence and apply [supabase_schema.sql](../supabase_schema.sql) only after reviewing its tables and access policies.

Frontend clients are inconsistent: `frontend/src/api/supabase.js` and `frontend/src/lib/supabaseClient.js` use different client approaches/key settings. The latter reads `VITE_SUPABASE_KEY` and dynamically imports `@supabase/supabase-js`, which is not declared in the frontend package. The example retains the public `VITE_SUPABASE_ANON_KEY` setting used by the other client. That client also contains hard-coded fallback project settings, so blank frontend values do not disable it if it is imported. Neither client is currently imported by the active frontend source tree. Inspect and test the particular cloud path before enabling it; merely supplying credentials does not complete all integrations. Never expose service-role credentials through a `VITE_*` variable.

## Frontend configuration

Vite reads `frontend/.env` at development startup/build time. A root `.env` is not the frontend template.

- `VITE_API_URL`: browser-reachable HTTP(S) base, normally without a trailing slash.
- `VITE_WS_URL`: optional complete `ws://` or `wss://` URL including `/ws/waterfall`; otherwise derived from the API URL.
- Optional public Supabase settings: see above.

The HTTP client and waterfall hook override the API host when the browser hostname contains `render.com` or `onrender.com`, selecting `https://sihnew-backend.onrender.com`. A custom Render deployment must account for that code path; setting `VITE_API_URL` alone may not change its destination.
