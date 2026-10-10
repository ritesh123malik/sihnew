# Deploying Sonaris

[← README](../README.md) · [Configuration](configuration.md)

## Static frontend and API service

Build the frontend from `frontend/` with `npm ci` and `npm run build`. Set `VITE_API_URL` to a browser-reachable HTTPS API base **before the build**. Serve `frontend/dist/` with an `index.html` fallback for React Router. The Vercel rewrite file is included.

Start the API from the repository root:

```bash
python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

For a reverse proxy, route HTTP and WebSocket upgrades, align upload/time limits with expected survey files, and use TLS. Start with one API process if using the in-memory stream broadcast manager; additional workers do not share its connections.

The repository's Procfiles/start scripts and Nixpacks configuration are deployment starting points. The frontend contains a hard-coded API override on Render hostnames; inspect [configuration.md](configuration.md#frontend-configuration) before selecting a different backend there.

## Backend Docker with persistent local storage

From the root, after creating `.env` from the template:

```bash
docker build -t sonaris:local .
mkdir -p runtime/uploads runtime/outputs runtime/exports runtime/patch-output
docker run --rm --name sonaris-api -p 8000:8000 --env-file .env \
  -e DATABASE_URL=sqlite:////app/runtime/sonaris.db \
  -e UPLOAD_DIR=/app/runtime/uploads \
  -e OUTPUT_DIR=/app/runtime/outputs \
  -v "$PWD/runtime:/app/runtime" \
  -v "$PWD/runtime/exports:/app/exports" \
  -v "$PWD/runtime/patch-output:/app/outputs" \
  sonaris:local
```

This covers the primary database, StorageService, and root-relative `exports/` and `outputs/` locations. Audit any additional paths used by the specific export workflow you enable. Keep `runtime/` out of commits; it contains user data. Back up both the database and its referenced files consistently. A SQLAlchemy URL for another database also requires the matching database driver and compatibility validation.

## Existing Compose caveats

`docker compose up --build` is available, but the supplied configuration has known limitations:

1. It reads root `.env.example`, not your `.env`. Change its `env_file` when deploying your own settings.
2. Frontend `VITE_*` values are supplied as runtime container environment, after `npm run build` has already run in the Dockerfile. They do not reconfigure the built bundle.
3. `http://backend:8000` is an internal Compose hostname, not normally reachable from the user's browser. The shipped bundle may instead fall back to localhost; this is only suitable for a local browser against a local API.
4. Default backend uploads are in `/app/backend/data/uploads` and SQLite is under `/app`; Compose mounts `/app/data`, `/app/models`, and `/app/logs`. These mounts do not persist all default application state.
5. The `model/` serving artifacts and `models/` auxiliary weights are different directories. The `models/` bind mount can hide the image's auxiliary checkpoint if the host directory is empty.
6. The frontend uses Vite preview. Use a production static server/host for a public deployment.

Adjust these points and verify persistence, browser connectivity, and restart behavior before treating Compose as a deployment recipe.

## Operational checks

```bash
curl --fail http://localhost:8000/api/health
curl --fail http://localhost:8000/api/health/ready
curl --fail http://localhost:8000/metrics
```

Then upload a known sample, reopen its run, download an export, and restart the service to confirm state survives. A successful health response alone does not prove every model, export, or cloud integration works.

Prometheus scrape configuration and alert rules are included in `prometheus.yml` and `monitoring/alert_rules.yml`. Deploy a Prometheus server separately; Compose has no Prometheus service.

## Public-service gaps

The current main app accepts broad HTTP(S) origins and exposes unauthenticated upload, deletion, export, and model-management routes. Add access controls, configure restrictive CORS in the actual middleware, and define retention/storage limits before public hosting. The existing process-local limiter does not replace authentication or a gateway policy. No production-readiness or availability guarantee is implied by the Docker health check.
