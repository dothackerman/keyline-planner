# Errors

## [ERR-20260224-001] Swiss STAC API 400 Bad Request

**Logged**: 2026-02-24T12:00:00Z
**Priority**: high
**Status**: resolved
**Area**: code | tooling

### Summary
The swisstopo STAC API returned a 400 error when queried with LV95 (EPSG:2056) bounding boxes.

### Error Output
Initially masked by generic parsing error. Captured after adding verbose logging:
```json
{"message": "illegal bounding box ... latitude must be between -90 and 90"}
```

### Context
Attempting to fetch AOI tiles using `pystac-client` with local Swiss coordinates.

### Suggested Fix
Reproject all STAC search bounding boxes to WGS84 (EPSG:4326) before calling the API.

### Metadata
- Layer: 1
- Reproducible: yes
- Related Files: [src/keyline_planner/engine/tiles.py](src/keyline_planner/engine/tiles.py), [src/keyline_planner/engine/geometry.py](src/keyline_planner/engine/geometry.py)
- Resolution: [2026-02-24] Resolved by adding `reproject_bbox` and calling it before STAC search.

---

## [ERR-20260224-002] gdalwarp "dataset already exists"

**Logged**: 2026-02-24T12:15:00Z
**Priority**: medium
**Status**: resolved
**Area**: engine

### Summary
`gdalwarp` failed when running sequentially in the same directory because the output file already existed.

### Error Output
```text
Output dataset output.tif exists, but -overwrite not set.
```

### Context
`RasterProcessor.clip_to_aoi` calling `gdalwarp` without overwrite flag.

### Suggested Fix
Always include `-overwrite` in GDAL subprocess calls for intermediate or generated artifacts.

### Metadata
- Layer: 1
- Reproducible: yes
- Related Files: [src/keyline_planner/engine/raster.py](src/keyline_planner/engine/raster.py)
- Resolution: [2026-02-24] Added `-overwrite` to all gdalwarp and gdalbuildvrt calls.
- Resolution: Added `-overwrite` to all gdalwarp and gdalbuildvrt calls.
