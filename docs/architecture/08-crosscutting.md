📍 **[arc42](README.md)** › Crosscutting Concepts

# 8. Crosscutting Concepts

## 8.1 Determinism

All engine outputs must be reproducible given the same inputs:

- **Coordinate rounding**: All output coordinates are rounded to 2 decimal
  places (cm precision in LV95) before serialisation.
- **Feature ordering**: Contour features are sorted by (elevation, minx, miny)
  before serialisation to ensure stable output artifacts regardless of GDAL's
  internal ordering.
- **CRS-safe defaults**: Default contour output is GeoPackage in LV95
  (`EPSG:2056`), avoiding CRS ambiguity in GIS tools.
- **GeoJSON export policy**: When requested, GeoJSON is exported in WGS84
  (`EPSG:4326`) for standards compliance.
- **Cache keying**: Cache keys are derived from deterministic hashes of AOI
  geometry and processing parameters.
- **Provenance manifests**: Every pipeline run writes a `manifest.json`
  recording exact parameters, tile IDs, and timing.

## 8.2 Error Handling

- Engine modules raise `ValueError` for input validation failures.
- Network errors from STAC/tile downloads propagate as `ConnectionError`
  or `requests.HTTPError`.
- GDAL failures propagate as `subprocess.CalledProcessError`.
- The CLI catches all exceptions, prints user-friendly messages, and exits
  with non-zero codes.

## 8.3 Logging

- All engine modules use Python's `logging` module.
- The CLI configures `RichHandler` for formatted terminal output.
- Log levels: `INFO` by default, `DEBUG` with `--verbose`.
- No sensitive data in logs.

## 8.4 Caching Strategy

Two-tier cache:

1. **Raw tile cache**: Content-addressed by (collection_id, item_id, filename).
   Tiles are verified against STAC checksums on download.
2. **Derived artifact cache**: Keyed by (aoi_hash, params_hash). Contains
   clipped DEMs, contour files, and provenance manifests.

Cache invalidation: Upstream version validation via STAC `file:checksum`
and `updated` timestamps.

## 8.5 Attribution

swisstopo's OGD terms require source attribution on all derived data products.
The engine automatically includes `"Source: Federal Office of Topography swisstopo"`
in all `ProcessingResult` objects and provenance manifests.

## 8.6 Testing Philosophy

Three test levels aligned with the two-layer model:

| Level | Scope | Network | Fixtures |
|-------|-------|---------|----------|
| **Unit** | Individual functions/classes | No | In-memory |
| **Integration** | Module composition (raster + contour pipeline) | No | Synthetic DEMs |
| **E2E (default)** | CLI invocation → output validation | No (mocked pipeline) | CliRunner + mocked `run_contour_pipeline` |
| **E2E (smoke)** | Minimal live end-to-end path | Yes (opt-in) | Real STAC + GDAL, gated by `KEYLINE_RUN_NETWORK_SMOKE=1` |

Golden-file regression testing via `pytest-regressions` is planned for future
contour output stability hardening.
Performance regression tracking via `pytest-benchmark` is planned for future
quality-gate expansion.

## 8.7 Runtime Connectivity

- Current runtime contour generation requires network access to swisstopo STAC
  for tile discovery.
- Cached tiles reduce repeated downloads, but discovery still hits STAC.
- Fully offline runtime execution is planned future work.

---

**Navigation:**  
⬅️ [Previous: Building Blocks](05-building-blocks.md) · [Overview](README.md) · [Next: Architecture Decisions](09-decisions.md) ➡️
