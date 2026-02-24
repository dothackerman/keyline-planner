# 8. Crosscutting Concepts

## 8.1 Determinism

All engine outputs must be reproducible given the same inputs:

- **Coordinate rounding**: All output coordinates are rounded to 2 decimal
  places (cm precision in LV95) before serialisation.
- **Feature ordering**: Contour features are sorted by (elevation, minx, miny)
  to ensure stable GeoJSON output regardless of GDAL's internal ordering.
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
| **E2E** | CLI invocation → output validation | No (mocked) | Synthetic DEMs + CliRunner |

Golden-file regression testing via `pytest-regressions` for contour output stability.
Performance regression tracking via `pytest-benchmark`.
