# Sonaris repository cleanup audit

[← README](../README.md) · [Changelog](../CHANGELOG.md)

Reviewed on 10 October 2026 against commit `d189600`. The audit inventoried all 477 tracked files, traced the frontend entry-point dependency graph, inspected Python imports (including training scripts), reviewed dynamic imports and route mounting, checked artifact references and duplicate hashes, and inspected serialized model class references.

## Removed

**60 tracked files** totaling **324,513 bytes**, plus the unused Three.js dependency. This is source-tree cleanup, not Git history rewriting; old files remain recoverable. The deleted files contained approximately 6,000 lines of source, styling, and stale documentation/report content.

| Category | Files | Evidence |
| :--- | ---: | :--- |
| Frontend source and styles | 37 | Unreachable from `frontend/src/main.jsx`; no glob-based component registration. Production output is byte-for-byte identical after removal. |
| Backend modules | 9 | No repository import consumers, dynamic registration, test consumers, or checkpoint class references. Mounted API schema remains identical. |
| Superseded audit snapshots, generators, and backend docs | 11 | Historical reports contain hard-coded findings and outdated architecture references; current maintained docs supersede them. Their generators are not runtime PDF export services. |
| Scaffolding and sample | 3 | Empty root npm lockfile with no root package; unreferenced 1×1 JPEG; empty PostCSS config superseded by Vite's inline configuration. |

The frontend removals include abandoned layout/report components, duplicate 3D viewers, unused map helpers, the unmounted streaming hook, unused audio utility, and unimported Supabase clients. The active launch/results/map/report/upload/live-survey screens remain intact.

Backend removals include unused schema definitions, old acoustic-filter helpers, an XTF wrapper, an unused WebSocket re-export, and alternate neural wrappers/layers. The active XTF parser, mounted waterfall router, trained detector, WERB training implementation, graph reasoning implementation, and physics-loss training implementation remain.

## Deliberately retained

- **All mounted routes and test files.** A feature being optional does not make its implementation unused.
- **Training, benchmark, dataset, replay, and export tools.** These have standalone entry points; they need not be imported by the web app.
- **`backend/best.pt` and `backend/best.onnx`.** Their hashes match `model/` copies, but backend-only build contexts, fallback discovery, verification, and packaging scripts depend on the backend paths. Consolidating them requires a separate deployment migration.
- **Dataset copies and showcase manifests.** They serve different curated bundles, generated-dataset verification, and documented upload workflows. Removing them merely because bytes repeat would break those uses.
- **`backend/requirements.txt`, backend Docker/Procfile/Nixpacks files.** They support the alternate backend-only deployment layout. The root README now correctly acknowledges that requirements file.
- **GAN weights and optional processing services.** They are referenced by actual processing implementations and tests.
- **Threshold copies.** Serving code searches multiple locations with different precedence; deleting copies could change behavior.

## Verification

Environment: macOS, Python 3.11.16, Node.js 22.23.2; repository dependency ranges and the frontend lockfile were used. CI's Node 20/container builds were not rerun locally.

| Check | Before | After |
| :--- | :--- | :--- |
| Backend test suite | 278 passed | 278 passed |
| Frontend production build | Passed, 134 modules | Passed, 134 modules |
| Frontend FormData script | 3 checks passed | 3 checks passed |
| Generated frontend files | Baseline SHA-256 hashes | All hashes identical |
| OpenAPI contract | Baseline JSON snapshot | Identical JSON |
| Retained Python syntax/import check | Dependency analysis | 166 files parsed; no imports of removed modules |

Both backend runs reported the same Rasterio deprecation warning. No tests were deleted or relaxed to obtain these results. Local documentation links and `git diff --check` were also checked. External hosting, physical sonar hardware, and cloud integrations were not exercised.

Reproduce the principal checks from the repository root:

```bash
PYTHONPATH=backend MPLCONFIGDIR=/tmp/sonaris-mpl YOLO_CONFIG_DIR=/tmp/sonaris-yolo \
  .venv/bin/python -m pytest backend/tests/ -q --tb=short
npm --prefix frontend ci
npm --prefix frontend run build
node frontend/test_launch_form_data.mjs
```

## Additional report cleanup

At the maintainer's request, the remaining static submission PDF and two standalone report generators were also removed:

- `SIH2026_Idea_Submission_SonarSentry_AI.pdf`
- `scripts/generate_sih_idea_submission_pdf.py`
- `scripts/generate_noaa_xtf_report_pdf.py`

Neither generator was imported or called by application code, tests, CI, or deployment scripts. Both embedded historical presentation/report text and workstation-specific output paths. No static PDF files remain tracked in the repository. Runtime PDF export services remain available for survey reports and dossiers.

This follow-up changes report artifacts and documentation only. References, Python syntax, and whitespace were checked; the backend suite was not rerun for these standalone-file deletions.

## Recovery

Removed content is available in [the pre-cleanup tree](https://github.com/ritesh123malik/sihnew/tree/d189600). To restore a particular file locally, run `git restore --source=d189600 -- path/to/file` and review it before committing. No force-push or history rewrite is needed.

<details>
<summary>Exact removal inventory</summary>

### Unreachable frontend source

```text
frontend/src/api/supabase.js
frontend/src/components/AnomalyModal/ShadowCurveChart.jsx
frontend/src/components/Bathymetry/Seabed3DViewer.jsx
frontend/src/components/BathymetryControls/BathymetryControls.jsx
frontend/src/components/DetectionCard/DetectionCard.jsx
frontend/src/components/ErrorBoundary/ErrorBoundary.jsx
frontend/src/components/ErrorBoundary/ErrorBoundary.module.css
frontend/src/components/GeoMap/DetectionMarkers.jsx
frontend/src/components/GeoMap/GeoMap.css
frontend/src/components/GeoMap/SwathOverlay.jsx
frontend/src/components/GeoMap/VesselTrack.jsx
frontend/src/components/Layout/Header.jsx
frontend/src/components/Layout/Sidebar.css
frontend/src/components/Layout/Sidebar.jsx
frontend/src/components/MetadataPanel/MetadataPanel.jsx
frontend/src/components/MetadataPanel/MetadataPanel.module.css
frontend/src/components/PipelineProgress/PipelineProgress.jsx
frontend/src/components/PipelineProgress/PipelineProgress.module.css
frontend/src/components/RealTimeWaterfall/RealTimeWaterfall.jsx
frontend/src/components/RealTimeWaterfall/RealTimeWaterfall.module.css
frontend/src/components/Reports/DetectionTable.jsx
frontend/src/components/Reports/GeoJSONViewer.jsx
frontend/src/components/Reports/PDFPreview.jsx
frontend/src/components/Reports/ReportExporter.css
frontend/src/components/Reports/ReportExporter.jsx
frontend/src/components/Seabed3DViewer/Seabed3DViewer.jsx
frontend/src/components/Stepper/Stepper.jsx
frontend/src/components/Stepper/Stepper.module.css
frontend/src/components/WaterfallPreview/WaterfallPreview.jsx
frontend/src/components/WaterfallPreview/WaterfallPreview.module.css
frontend/src/components/common/LoadingSpinner.jsx
frontend/src/components/common/Modal.jsx
frontend/src/components/common/SystemStatusBar.jsx
frontend/src/hooks/useWaterfallStream.js
frontend/src/lib/supabaseClient.js
frontend/src/styles/main.scss
frontend/src/utils/sonarAudio.js
```

### Unreferenced backend modules

```text
backend/app/api/routes/ws.py
backend/app/models/neural/gcn_layer.py
backend/app/models/neural/physics_loss.py
backend/app/models/neural/shadow_head.py
backend/app/models/neural/wavelet_layer.py
backend/app/preprocessing/acoustic_filters.py
backend/app/schemas/error.py
backend/app/schemas/upload.py
backend/app/services/xtf_service.py
```

### Obsolete audit snapshots and generators

```text
SIH2026_COMPREHENSIVE_AUDIT_REPORT.md
SIH2026_COMPREHENSIVE_AUDIT_REPORT.pdf
SonarSentry_Comprehensive_Pipeline_Audit_and_Dead_Code_Report.pdf
SonarSentry_Final_Verdict_SIH2026_Evaluation_Report.pdf
SonarShield_AI_Comprehensive_Status_and_Gap_Resolution_Report.pdf
report_final.pdf
scripts/generate_audit_pdf.py
scripts/generate_comprehensive_audit_pdf.py
scripts/generate_final_report_pdf.py
scripts/generate_final_verdict_pdf.py
backend/BACKEND_DOCS.md
```

### Unused scaffolding and sample

```text
package-lock.json
sample_sonar.jpg
frontend/postcss.config.js
```

</details>
