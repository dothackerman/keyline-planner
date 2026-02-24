# 2. Constraints

## 2.1 Technical Constraints

| Constraint | Rationale |
|-----------|-----------|
| Python 3.11+ | Mature geospatial ecosystem (GDAL, rasterio, shapely, pyproj) |
| GDAL as processing engine | Industry standard for raster/vector operations; MIT-licensed |
| CLI-first interface | Rapid prototyping, deterministic testing, composable with scripts |
| LV95 / EPSG:2056 | Swiss national CRS — all processing happens in this CRS |
| Local-first caching | Bounded resource use on standard developer machines |

## 2.2 Organisational Constraints

| Constraint | Rationale |
|-----------|-----------|
| Entirely open-source stack | All dependencies must use permissive licences (MIT, BSD, PostgreSQL, etc.) |
| Agent-driven development | Architecture and implementation created by agents; humans validate via testing |
| swisstopo attribution required | OGD terms mandate "Source: Federal Office of Topography swisstopo" |

## 2.3 Conventions

| Convention | Detail |
|-----------|--------|
| Two-layer architecture | Processing Engine (Layer 1) + Agent Layer (Layer 2) per AGENTS.md |
| arc42 documentation | Human-readable architecture docs as negotiation boundary |
| Conventional commits | `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `ci:` prefixes |
| Test markers | `@pytest.mark.unit`, `integration`, `e2e`, `benchmark`, `network` |
