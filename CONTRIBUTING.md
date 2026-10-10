# Contributing to Sonaris

Start with the [README](README.md#quick-start) and [architecture guide](docs/architecture.md). For a substantial behavior change, open an issue explaining the problem and proposed scope before implementation.

## Development workflow

1. Fork or clone the repository and create a focused branch.
2. Install root Python requirements and frontend dependencies as documented.
3. Keep credentials in ignored `.env` files. Use blank cloud settings for local work.
4. Make the smallest coherent change; preserve unrelated behavior.
5. Run relevant regression tests. For frontend changes, run `npm run build` inside `frontend/` and inspect the affected screens.
6. Update docs, example configuration, and the changelog when behavior changes.
7. Submit a pull request describing the problem, resulting behavior, validation, and known limitations.

## Validation

```bash
python -m pytest backend/tests/ --tb=short -q
node frontend/test_launch_form_data.mjs
```

Coverage is optional locally: `python -m pytest backend/tests/ --cov=backend/app --cov-report=term-missing`.

Report what actually ran, including failures or missing dependencies. Do not claim a test result from old reports. For model changes, identify the artifact, class mapping, dataset split, device, input dimensions, thresholds, and preprocessing. Keep all threshold copies consistent or explicitly document why they differ.

## Pull-request checklist

- [ ] Scope and before/after behavior are clear.
- [ ] Relevant tests or manual checks are recorded.
- [ ] API contracts, environment settings, and README examples match the code.
- [ ] Simulated data and experimental features are labeled.
- [ ] No secrets, private survey data, or unneeded generated artifacts are included.
- [ ] Dataset and model provenance is recorded for any new artifacts.

## Reporting issues

Use [GitHub Issues](https://github.com/ritesh123malik/sihnew/issues). Include operating system, Python/Node versions, steps, expected/actual behavior, and sanitized logs. Follow the [Code of Conduct](CODE_OF_CONDUCT.md). The repository has no declared project license; contributions do not establish one.
