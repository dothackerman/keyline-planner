"""Shared test configuration and fixtures.

Provides:
    - Synthetic DEM raster generation for deterministic testing.
    - Sample AOI geometries in LV95.
    - Temporary directories with auto-cleanup.
    - Test markers for selective test runs.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pytest


@pytest.fixture
def tmp_dir() -> Path:
    """Provide a temporary directory that persists for the test's lifetime."""
    with tempfile.TemporaryDirectory(prefix="keyline_test_") as d:
        yield Path(d)


@pytest.fixture
def sample_bbox_lv95() -> tuple[float, float, float, float]:
    """A small sample bbox in LV95 coordinates (near Bern).

    Covers approximately 1 km² — intersects a single swissALTI3D tile.
    """
    return (2600000.0, 1200000.0, 2601000.0, 1201000.0)


@pytest.fixture
def sample_polygon_lv95() -> dict[str, Any]:
    """A small sample polygon in LV95 coordinates (near Bern).

    Roughly 500m x 500m rectangle — a typical parcel size.
    """
    return {
        "type": "Polygon",
        "coordinates": [[
            [2600100.0, 1200100.0],
            [2600600.0, 1200100.0],
            [2600600.0, 1200600.0],
            [2600100.0, 1200600.0],
            [2600100.0, 1200100.0],
        ]],
    }


@pytest.fixture
def sample_polygon_wgs84() -> dict[str, Any]:
    """A small sample polygon in WGS84 coordinates (near Bern).

    Approximately equivalent to sample_polygon_lv95.
    """
    return {
        "type": "Polygon",
        "coordinates": [[
            [7.44, 46.94],
            [7.45, 46.94],
            [7.45, 46.95],
            [7.44, 46.95],
            [7.44, 46.94],
        ]],
    }


@pytest.fixture
def synthetic_dem(tmp_dir: Path) -> Path:
    """Generate a synthetic DEM GeoTIFF for deterministic testing.

    Creates a 100x100 raster with a cone-shaped surface centered in the
    middle, elevation ranging from ~400m to ~800m. This produces known
    contour patterns that are easy to verify.

    The raster is in EPSG:2056 (LV95) with 2m pixel size.
    """
    import rasterio
    from rasterio.transform import from_bounds

    dem_path = tmp_dir / "synthetic_dem.tif"

    width, height = 100, 100
    xmin, ymin = 2600000.0, 1200000.0
    xmax = xmin + width * 2.0  # 2m resolution
    ymax = ymin + height * 2.0

    # Create a cone surface: max elevation at center, decreasing outward
    y, x = np.mgrid[0:height, 0:width]
    cx, cy = width / 2, height / 2
    distance = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    max_distance = np.sqrt(cx**2 + cy**2)
    elevation = 800.0 - (distance / max_distance) * 400.0  # 400m to 800m

    transform = from_bounds(xmin, ymin, xmax, ymax, width, height)

    with rasterio.open(
        dem_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="float32",
        crs="EPSG:2056",
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        dst.write(elevation.astype(np.float32), 1)

    return dem_path


@pytest.fixture
def synthetic_dem_flat(tmp_dir: Path) -> Path:
    """Generate a flat synthetic DEM (single elevation = 500m).

    Useful for testing edge case: no contours should be generated
    when the surface is perfectly flat.
    """
    import rasterio
    from rasterio.transform import from_bounds

    dem_path = tmp_dir / "synthetic_dem_flat.tif"

    width, height = 50, 50
    xmin, ymin = 2600000.0, 1200000.0
    xmax = xmin + width * 2.0
    ymax = ymin + height * 2.0

    elevation = np.full((height, width), 500.0, dtype=np.float32)
    transform = from_bounds(xmin, ymin, xmax, ymax, width, height)

    with rasterio.open(
        dem_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="float32",
        crs="EPSG:2056",
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        dst.write(elevation, 1)

    return dem_path


@pytest.fixture
def sample_geojson_file(tmp_dir: Path, sample_polygon_lv95: dict[str, Any]) -> Path:
    """Write sample polygon to a GeoJSON file."""
    path = tmp_dir / "parcel.geojson"
    geojson = {
        "type": "Feature",
        "geometry": sample_polygon_lv95,
        "properties": {"name": "test_parcel"},
    }
    path.write_text(json.dumps(geojson))
    return path
