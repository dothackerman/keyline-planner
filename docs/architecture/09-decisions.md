# 9. Architecture Decisions

## ADR-001: CLI-First Interface for Milestone 1

**Status**: Accepted

**Context**: The system needs a user interface for Milestone 1. Options
considered: REST API (FastAPI), CLI, or library-only.

**Decision**: CLI-first using Typer, with the engine as a reusable library.

**Rationale**:
- CLI enables deterministic E2E testing via CliRunner
- CLI is composable with shell scripts and CI pipelines
- Engine remains a library — future API layers call the same functions
- Faster to prototype and iterate than a web service

**Consequences**:
- No HTTP server in Milestone 1
- CLI must handle input parsing, progress display, and error formatting
- Engine API must be clean enough for both CLI and future REST consumption

---

## ADR-002: GDAL via Subprocess for Raster Operations

**Status**: Accepted

**Context**: GDAL operations can be invoked via Python bindings (osgeo.gdal),
rasterio (which wraps GDAL), or subprocess calls to GDAL CLI utilities.

**Decision**: Use subprocess calls to GDAL CLI utilities (gdalbuildvrt,
gdalwarp, gdal_contour) as the primary interface.

**Rationale**:
- CLI utilities are the most stable, well-documented GDAL interface
- Subprocess isolation prevents GDAL's C library from crashing the Python process
- Easy to debug (commands are reproducible in a terminal)
- Rasterio used for metadata/stats where subprocess is overkill

**Consequences**:
- GDAL must be installed system-wide (not pip-installable)
- Pipeline requires temporary files for intermediate artifacts
- Slightly higher overhead than in-process calls (negligible for our workloads)

---

## ADR-003: Content-Addressed Tile Cache

**Status**: Accepted

**Context**: SwissALTI3D tiles must be downloaded from swisstopo's servers.
Repeated processing of the same or overlapping AOIs should not re-download.

**Decision**: Local file cache keyed by (collection_id, item_id, filename)
with checksum verification against STAC metadata.

**Rationale**:
- Simple, predictable, no external dependencies
- Checksums ensure cache integrity
- Derived artifacts cached separately with parameter-aware keys
- CI can pre-seed cache for offline testing

**Consequences**:
- Cache grows over time; no automatic eviction (acceptable for local dev)
- Cache directory must be excluded from version control

---

## ADR-004: Default to 2m Resolution

**Status**: Accepted

**Context**: swissALTI3D is available at 0.5m (~26 MB/tile) and 2.0m (~1 MB/tile).

**Decision**: Default to 2.0m resolution; 0.5m available via `--resolution high`.

**Rationale**:
- 26× less data per tile = faster downloads and CI runs
- 2m is sufficient for keyline planning at typical parcel scales
- 0.5m may be oversampled in areas with sparse source data (per swisstopo)
- Keeps developer experience fast on standard machines

**Consequences**:
- Users wanting maximum detail must explicitly opt in
- Some contour artifacts may differ between resolutions
