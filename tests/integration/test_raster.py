"""Integration tests for raster operations using synthetic DEMs.

These tests exercise the GDAL-based raster pipeline on synthetic data
to verify deterministic behaviour without network access.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from keyline_planner.engine.models import AOI, BBox, CRS, ContourParams
from keyline_planner.engine.raster import build_vrt, clip_dem, get_dem_stats

pytestmark = pytest.mark.integration


class TestBuildVrt:
    """Tests for VRT mosaic construction."""

    def test_builds_vrt_from_single_tile(
        self, synthetic_dem: Path, tmp_dir: Path
    ) -> None:
        vrt_path = tmp_dir / "test.vrt"
        result = build_vrt([synthetic_dem], vrt_path)
        assert result.exists()
        assert result.suffix == ".vrt"

    def test_raises_on_empty_input(self, tmp_dir: Path) -> None:
        with pytest.raises(ValueError, match="No tile paths"):
            build_vrt([], tmp_dir / "empty.vrt")


class TestClipDem:
    """Tests for DEM clipping to an AOI."""

    def test_clips_to_aoi(
        self, synthetic_dem: Path, tmp_dir: Path
    ) -> None:
        aoi = AOI(
            geometry={
                "type": "Polygon",
                "coordinates": [[
                    [2600050.0, 1200050.0],
                    [2600150.0, 1200050.0],
                    [2600150.0, 1200150.0],
                    [2600050.0, 1200150.0],
                    [2600050.0, 1200050.0],
                ]],
            },
            bbox=BBox(
                xmin=2600050.0, ymin=1200050.0,
                xmax=2600150.0, ymax=1200150.0,
            ),
        )

        output = tmp_dir / "clipped.tif"
        result = clip_dem(synthetic_dem, aoi, output)
        assert result.exists()
        assert result.stat().st_size > 0

    def test_clipped_dem_stats(
        self, synthetic_dem: Path, tmp_dir: Path
    ) -> None:
        aoi = AOI(
            geometry={
                "type": "Polygon",
                "coordinates": [[
                    [2600050.0, 1200050.0],
                    [2600150.0, 1200050.0],
                    [2600150.0, 1200150.0],
                    [2600050.0, 1200150.0],
                    [2600050.0, 1200050.0],
                ]],
            },
            bbox=BBox(
                xmin=2600050.0, ymin=1200050.0,
                xmax=2600150.0, ymax=1200150.0,
            ),
        )

        output = tmp_dir / "clipped.tif"
        clip_dem(synthetic_dem, aoi, output)
        stats = get_dem_stats(output)

        # Elevation should be within the synthetic DEM range (400-800m)
        assert stats["min"] >= 400.0
        assert stats["max"] <= 800.0
        assert stats["crs"] == "EPSG:2056"


class TestGetDemStats:
    """Tests for DEM statistics extraction."""

    def test_stats_from_synthetic_dem(self, synthetic_dem: Path) -> None:
        stats = get_dem_stats(synthetic_dem)
        assert stats["width"] == 100
        assert stats["height"] == 100
        assert stats["nodata"] == -9999.0
        assert 400.0 <= stats["min"] <= 800.0
        assert 400.0 <= stats["max"] <= 800.0
        assert stats["crs"] == "EPSG:2056"
