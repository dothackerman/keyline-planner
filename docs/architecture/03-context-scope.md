# 3. Context and Scope

## 3.1 Business Context

```
                    ┌─────────────────────┐
                    │   Keyline Planner    │
                    │   (CLI Engine)       │
                    └──────┬──────────┬───┘
                           │          │
              ┌────────────▼──┐  ┌────▼──────────┐
              │  swisstopo    │  │  Local File    │
              │  STAC API     │  │  System        │
              │  (data.geo.   │  │  (cache +      │
              │   admin.ch)   │  │   outputs)     │
              └───────────────┘  └────────────────┘
```

| External System | Interface | Purpose |
|----------------|-----------|---------|
| **swisstopo STAC API** | HTTPS / STAC Item Search | Discover + download swissALTI3D elevation tiles |
| **Local file system** | File I/O | Tile cache, DEM artifacts, contour outputs, manifests |
| **User (CLI)** | stdin/stdout/stderr + exit codes | Invoke processing, receive results |

## 3.2 Technical Context

### Data Flow

```
User Input (AOI + params)
    │
    ▼
┌─────────────────────────────────────────────┐
│ CLI Adapter (Typer)                         │
│   Parse args → call engine → format output  │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ Engine Pipeline                             │
│                                             │
│  1. Normalise AOI (geometry.py)             │
│  2. Discover tiles (tiles.py → STAC API)    │
│  3. Cache tiles (cache.py → file system)    │
│  4. Build VRT mosaic (raster.py → GDAL)     │
│  5. Clip DEM (raster.py → GDAL)            │
│  6. Generate contours (contours.py → GDAL)  │
│  7. Write outputs (GeoJSON + manifest)      │
└─────────────────────────────────────────────┘
```

### CRS Transformation

- Input: WGS84 (EPSG:4326) or LV95 (EPSG:2056)
- Processing: Always in LV95 (EPSG:2056)
- Output: LV95 (EPSG:2056) — matches source DEM
