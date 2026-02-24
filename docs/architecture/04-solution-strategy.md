# 4. Solution Strategy

## 4.1 Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Python 3.11+ | Best geospatial ecosystem; strong CLI testing tools |
| Raster engine | GDAL (via subprocess + rasterio) | Industry standard; deterministic; OSGeo-maintained |
| Geometry | Shapely 2.x (GEOS) | Robust planar geometry ops; tolerance-aware comparison |
| CRS transforms | pyproj (PROJ) | Authoritative CRS library; MIT-licensed |
| Tile discovery | pystac-client | Purpose-built for STAC API interaction |
| CLI framework | Typer | Type-hint CLI with built-in test runner |
| Testing | pytest + pytest-regressions + pytest-benchmark | Golden-file testing + performance regression tracking |
| Output format | GeoJSON | Human-readable; diff-friendly; widely supported |

## 4.2 Architectural Approach

**Two-layer separation** (per AGENTS.md):

- **Layer 1 (Engine)**: Pure processing pipeline. Deterministic, stateless functions.
  No orchestration logic. Tested at unit and integration level.

- **Layer 2 (Agent)**: Orchestration, evaluation, self-improvement loops.
  Composes engine skills. Not implemented in Milestone 1 CLI — the CLI is
  a thin adapter, not an agent.

**CLI as thin adapter**: The CLI (Typer) translates user input into engine
function calls and formats output. It contains zero business logic.

**GDAL-first processing**: Use GDAL command-line utilities (gdalbuildvrt,
gdalwarp, gdal_contour) as the primary processing engine. This provides
battle-tested, well-documented operations with predictable behaviour.

## 4.3 Quality Strategy

| Quality Goal | Strategy |
|-------------|----------|
| Determinism | Canonical output ordering; coordinate rounding; sorted keys |
| Testability | Synthetic DEMs for offline testing; CliRunner for E2E |
| Modularity | Each engine module has a single responsibility; no cross-dependencies |
| Developer UX | Default 2m resolution (~1MB/tile); clear error messages |
