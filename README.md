# Keyline Planner

CLI-first Swiss contour generation engine for keyline design planning.

Generates topographic contour lines from [swissALTI3D](https://www.swisstopo.admin.ch/en/height-model-swissalti3d)
elevation data, designed for agricultural and landscape management workflows.

> **Status**: Milestone 1 — contour generation engine implemented.

### Capability Status

Implemented now (Milestone 1):
- CLI contour generation from bbox or GeoJSON AOI
- LV95/WGS84 input support with LV95 processing/output
- Tile discovery via swisstopo STAC + local tile caching
- GDAL-based DEM clipping and contour extraction
- Provenance manifest output (`manifest.json`)
- Deterministic offline-by-default test suite (unit/integration/E2E with mocks)

Planned/Future:
- Full offline runtime mode (run without live STAC access)
- Hydrology and vegetation layer integration (Milestone 2)
- Keyline pattern generation/planning tools (Milestone 3)

## Quick Start

### Prerequisites

- Python 3.11+
- GDAL 3.x (`gdal_contour`, `gdalwarp`, `gdalbuildvrt` must be on PATH)

```bash
# Ubuntu/Debian
sudo apt-get install gdal-bin libgdal-dev

# macOS (Homebrew)
brew install gdal
```

### Installation

```bash
# Clone and install in editable mode with dev dependencies
git clone https://github.com/dothackerman/keyline-planner.git
cd keyline-planner
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### Usage

```bash
# Generate contours from a bounding box (LV95 coordinates)
keyline contours --bbox "2600000,1200000,2601000,1201000"

# Generate contours from a GeoJSON parcel file
keyline contours --geojson parcel.geojson --interval 2.0

# High resolution (0.5m) with simplification
keyline contours --geojson parcel.geojson --resolution high --simplify 1.0

# WGS84 input coordinates
keyline contours --bbox "7.44,46.94,7.45,46.95" --crs wgs84

# See all options
keyline contours --help
```

### Output

Each run produces:
- `contours.geojson` — contour lines sorted by elevation
- `dem_clip.tif` — clipped DEM raster (optional, `--no-dem` to skip)
- `manifest.json` — provenance metadata (parameters, timing, tile IDs, attribution)

### Visual Inspection in QGIS

Install QGIS from the official download page:
- https://qgis.org/download/
- Installation guide: https://docs.qgis.org/latest/en/docs/user_manual/introduction/getting_started.html

To inspect generated contours on the Swiss national basemap:

1. Open QGIS and create a new project.
2. Set project CRS to `EPSG:2056`:
   `Project -> Properties -> CRS -> EPSG:2056`.
3. Add swisstopo WMS basemap:
   `Layer -> Add Layer -> Add WMS/WMTS Layer -> New`.
4. Configure WMS connection:
   - Name: `swisstopo WMS`
   - URL: `https://wms.geo.admin.ch/?Lang=en`
   - Version: `1.3.0`
   - Leave auth empty (public service)
5. Click `Connect`, then choose a national map layer such as:
   - `ch.swisstopo.pixelkarte-farbe` (color national map), or
   - another `ch.swisstopo.pixelkarte*` layer available in capabilities.
6. In WMS layer options, use:
   - CRS: `EPSG:2056`
   - Image encoding: `image/png`
7. Add your generated files:
   - `contours.geojson`
   - optionally `dem_clip.tif`
8. Layer order in the Layers panel:
   - Basemap WMS at bottom
   - `dem_clip.tif` above it (optional)
   - `contours.geojson` on top
9. Style contours:
   - Right-click `contours.geojson` -> Properties -> Symbology
   - Use a high-contrast line color (dark brown/black), width `0.6-1.2 px`
   - Optional labels: label by `elevation`
10. Zoom and verify:
   - Right-click `contours.geojson` -> `Zoom to Layer`
   - Check contour alignment with ridges/valleys in the basemap.

Troubleshooting:
- If layers look offset, confirm project CRS and WMS layer CRS are both `EPSG:2056`.
- If labels are not in your preferred language, change `Lang=` in the WMS URL (`en`, `de`, `fr`, `it`, `rm`).
- If rendering is slow at national extent, zoom in or switch to WMTS.

WMTS alternative (faster tiled basemap):
- Add connection with URL  
  `https://wmts.geo.admin.ch/EPSG/2056/1.0.0/WMTSCapabilities.xml?lang=en`
- Use WMTS when you prioritize map performance over dynamic WMS rendering.

References:
- WMS: https://docs.geo.admin.ch/visualize-data/wms.html
- WMTS: https://docs.geo.admin.ch/visualize-data/wmts.html
- Layer metadata: https://docs.geo.admin.ch/explore-data/get-layer-metadata.html

## Development

```bash
make dev          # Install with dev dependencies
make ci           # Run full local CI (lint + format check + tests)
make test         # Run all tests (unit + integration + e2e)
make test-unit    # Run unit tests only
make lint         # Run ruff linter
make format       # Auto-format code
make coverage     # Run tests with coverage report

# Optional: run live network smoke tests
KEYLINE_RUN_NETWORK_SMOKE=1 pytest -m network
```

### Project Structure

```
src/keyline_planner/
├── cli/              # CLI adapter (Typer) — thin layer, no business logic
│   └── main.py
└── engine/           # Core processing engine (Layer 1)
    ├── models.py     # Value objects (AOI, BBox, TileInfo, ContourParams)
    ├── geometry.py   # AOI validation, CRS transformation
    ├── tiles.py      # STAC tile discovery
    ├── cache.py      # Content-addressed tile caching
    ├── raster.py     # GDAL raster operations (VRT, clip)
    ├── contours.py   # Contour extraction + canonicalisation
    └── pipeline.py   # Pipeline orchestrator

tests/
├── unit/             # Pure function tests (no I/O)
├── integration/      # Raster + contour tests with synthetic DEMs
└── e2e/              # CLI tests via CliRunner

docs/architecture/    # arc42 documentation (human-readable)
AGENTS.md             # Agent operating rules and architectural constraints
SKILL.md              # Agent self-improvement workflow (logs, templates)
```

### Architecture

This project follows a **two-layer architecture**:

- **Layer 1 (Engine)**: Deterministic processing. Pure transformations with
  explicit inputs/outputs. No agent logic.
- **Layer 2 (Agent)**: Orchestration, evaluation, self-improvement. Composes
  engine skills.

The CLI is a thin adapter — not an agent. It calls the engine pipeline directly.

| Artifact | Audience | Purpose |
|---|---|---|
| [`docs/architecture/`](docs/architecture/) | Humans | arc42 documentation — the negotiation boundary between human intent and agent autonomy |
| [`AGENTS.md`](AGENTS.md) | Agents | Architectural constraints, modularity rules, extension protocol |
| [`SKILL.md`](SKILL.md) | Agents | Operational self-improvement: error logging, learnings, promotion rules |

## Data Source

**swissALTI3D** by the Federal Office of Topography swisstopo.
Available at 0.5m and 2.0m resolution as Cloud Optimized GeoTIFFs.
Distributed under OGD terms (open use with attribution required).

> Source: Federal Office of Topography swisstopo

## License

MIT
