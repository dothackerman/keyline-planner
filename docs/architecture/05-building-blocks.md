📍 **[arc42](README.md)** › Building Blocks

# 5. Building Block View

## 5.1 Level 1 — System Overview

```mermaid
graph LR
    subgraph keyline["🔑 keyline-planner<br/>System"]
        direction LR
        CLI["CLI Adapter<br/><small>cli/</small>"]
        Engine["Core Engine<br/><small>engine/</small>"]
        CLI -->|depends on| Engine
    end
    
    Engine -->|depends on| Nothing["📭 Nothing<br/><small>Engine depends on<br/>nothing internal</small>"]
    
    style CLI fill:#fff3e0
    style Engine fill:#f3e5f5
    style Nothing fill:#ffebee,color:#c62828
```

**Dependency rule**: CLI depends on Engine. Engine depends on nothing internal.

## 5.2 Level 2 — Engine Modules

```
engine/
├── models.py      # Value objects: AOI, BBox, TileInfo, ContourParams, etc.
├── geometry.py     # AOI validation, CRS transformation, point->square AOI helper
├── tiles.py        # STAC tile discovery (network boundary)
├── cache.py        # Content-addressed tile + artifact caching
├── raster.py       # GDAL raster operations: VRT, clip, stats
├── contours.py     # Contour extraction + canonicalisation
└── pipeline.py     # Orchestrates modules into a complete workflow
```

### Module Responsibilities

| Module | Input | Output | Side Effects |
|--------|-------|--------|-------------|
| `models` | — | Data classes | None |
| `geometry` | GeoJSON / bbox / point+extent + CRS | Normalised AOI (LV95) or derived LV95 bbox | None |
| `tiles` | AOI | List of TileInfo | Network (STAC API) |
| `cache` | TileInfo list | Local file paths | Disk I/O, Network |
| `raster` | File paths + AOI | Clipped DEM path | Disk I/O (GDAL) |
| `contours` | DEM path + params + output format | GPKG path (default) and/or GeoJSON path | Disk I/O (GDAL) |
| `pipeline` | User params | ProcessingResult | Composes all above |

### Dependency Graph (Engine Internal)

```mermaid
graph TB
    Models["📦 models.py<br/><small>Data Classes</small>"]
    Pipeline["🔄 pipeline.py<br/><small>Orchestrator</small>"]
    Geometry["📐 geometry.py<br/><small>CRS + AOI Validation</small>"]
    Tiles["🗺️ tiles.py<br/><small>STAC Discovery</small>"]
    Cache["💾 cache.py<br/><small>Tile Caching</small>"]
    Raster["🖼️ raster.py<br/><small>GDAL Operations</small>"]
    Contours["📈 contours.py<br/><small>Contour Generation</small>"]
    
    Models -.->|used by all| Pipeline
    Models -.->|used by all| Geometry
    Models -.->|used by all| Tiles
    Models -.->|used by all| Cache
    Models -.->|used by all| Raster
    Models -.->|used by all| Contours
    
    Pipeline -->|uses| Geometry
    Pipeline -->|uses| Tiles
    Pipeline -->|uses| Cache
    Pipeline -->|uses| Raster
    Pipeline -->|uses| Contours
    
    style Models fill:#e0e0e0
    style Pipeline fill:#fff3e0
    style Geometry fill:#f3e5f5
    style Tiles fill:#e8f5e9
    style Cache fill:#e0f2f1
    style Raster fill:#fce4ec
    style Contours fill:#f1f8e9
```

No circular dependencies. `models` is a leaf dependency.

---

**Navigation:**  
⬅️ [Previous: Solution Strategy](04-solution-strategy.md) · [Overview](README.md) · [Next: Crosscutting Concepts](08-crosscutting.md) ➡️
