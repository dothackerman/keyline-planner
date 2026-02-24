# Keyline Planner

CLI-first Swiss contour generation engine for keyline design planning.

Generates topographic contour lines from [swissALTI3D](https://www.swisstopo.admin.ch/en/height-model-swissalti3d)
elevation data, designed for agricultural and landscape management workflows.

> **Status**: Milestone 1 — Proof of concept. Under active agentic development.

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

## Development

```bash
make dev          # Install with dev dependencies
make ci           # Run full local CI (lint + format check + tests)
make test         # Run all tests (unit + integration + e2e)
make test-unit    # Run unit tests only
make lint         # Run ruff linter
make format       # Auto-format code
make coverage     # Run tests with coverage report
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