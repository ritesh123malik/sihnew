# Sonaris changelog

This file records documented changes going forward. It does not reconstruct an unverified release history. See [commit history](https://github.com/ritesh123malik/sihnew/commits) for earlier work.

## Unreleased

### Cleanup

- Removed 37 frontend files unreachable from the application entry point and the unused Three.js dependency.
- Removed 9 unreferenced backend modules; retained mounted routes, tested services, and training implementations.
- Removed superseded audit snapshots/generators, legacy backend documentation, an empty root npm lockfile, an unreferenced 1×1 JPEG, and a redundant empty PostCSS config.
- Updated frontend configuration documentation to reflect active consumers and corrected the root setup's description of backend-only requirements.
- Recorded preservation decisions and before/after verification in [the cleanup audit](docs/cleanup.md).

### Documentation

- Rebuilt the README around the Sonaris name, operator workflow, actual routes, and configuration defaults.
- Added an SVG project banner, honest status badges, local demo instructions, and runnable upload/export examples.
- Expanded API, architecture, configuration, deployment, and model-artifact documentation.
- Added contribution guidance and a code of conduct.
- Replaced example cloud credentials with blank optional values and clarified frontend environment placement.
- Distinguished recorded model metrics, experimental modules, simulated outputs, and unverified performance claims.
- Documented missing project licensing and deployment gaps without assigning a license or claiming a release.
