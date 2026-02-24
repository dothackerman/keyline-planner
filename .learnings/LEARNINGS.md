# Learnings

## [LRN-20260224-001] GeoJSON CRS Compatibility

**Logged**: 2026-02-24T12:30:00Z
**Priority**: high
**Status**: resolved
**Area**: engine

### Summary
GDAL processing with cutlines is most stable when the cutline GeoJSON is in WGS84, even if the target raster is a local CRS.

### Details
Using LV95 GeoJSONs for `gdalwarp` cutlines caused transient "latitude out of range" errors in some PROJ versions. Forcing the cutline to WGS84 and explicitly setting `-t_srs EPSG:2056` resolved the ambiguity.

### Suggested Action
Generate temporary GeoJSON artifacts in WGS84 by default to ensure maximum interoperability with external tools like GDAL.

### Metadata
- Layer: 1
- Source: runtime_error
- Related Files: [src/keyline_planner/engine/raster.py](src/keyline_planner/engine/raster.py)
- Tags: gdal, crs, geojson
- Resolution: [2026-02-24] Forced WGS84 for temporary cutline files and added target SRS to gdalwarp.

---

## [LRN-20260224-002] Typer Global Flags Pattern

**Logged**: 2026-02-24T12:45:00Z
**Priority**: medium
**Status**: resolved
**Area**: tooling

### Summary
Typer handles global flags (before subcommands) differently than subcommand options.

### Details
To use `command --global-flag subcommand`, the flag must be defined in the `@app.callback()` function and passed to the subcommand via `ctx.obj`.

### Suggested Action
Standardize the use of `ctx.ensure_object(dict)` in the main callback for any flags that need to be shared across the entire CLI tool.

### Metadata
- Layer: 2
- Source: review
- Related Files: [src/keyline_planner/cli/main.py](src/keyline_planner/cli/main.py)
- Tags: typer, cli, global-flags
- Resolution: [2026-02-24] Refactored `verbose` to `app.callback` and used `ctx.obj` for state sharing.
