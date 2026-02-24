"""Integration tests for contour generation on synthetic DEMs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from keyline_planner.engine.contours import (
    count_contours,
    generate_contours,
    get_elevation_range,
)
from keyline_planner.engine.models import ContourParams

pytestmark = pytest.mark.integration


class TestGenerateContours:
    """Tests for end-to-end contour generation from a DEM."""

    def test_generates_contours_from_cone_dem(
        self, synthetic_dem: Path, tmp_dir: Path
    ) -> None:
        output = tmp_dir / "contours.geojson"
        params = ContourParams(interval=10.0)
        generate_contours(synthetic_dem, output, params)

        assert output.exists()
        data = json.loads(output.read_text())
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) > 0

    def test_contour_count_matches(
        self, synthetic_dem: Path, tmp_dir: Path
    ) -> None:
        output = tmp_dir / "contours.geojson"
        params = ContourParams(interval=50.0)
        generate_contours(synthetic_dem, output, params)

        count = count_contours(output)
        assert count > 0
        # Cone surface spans ~400m, so at 50m intervals we expect ~8 contours
        # (some tolerance for edge effects)
        assert 3 <= count <= 15

    def test_elevation_range_matches_dem(
        self, synthetic_dem: Path, tmp_dir: Path
    ) -> None:
        output = tmp_dir / "contours.geojson"
        params = ContourParams(interval=25.0)
        generate_contours(synthetic_dem, output, params)

        elev_min, elev_max = get_elevation_range(output)
        # Should be within the synthetic DEM range
        assert elev_min >= 400.0
        assert elev_max <= 800.0

    def test_contours_sorted_by_elevation(
        self, synthetic_dem: Path, tmp_dir: Path
    ) -> None:
        output = tmp_dir / "contours.geojson"
        params = ContourParams(interval=25.0)
        generate_contours(synthetic_dem, output, params)

        data = json.loads(output.read_text())
        elevations = [f["properties"]["elevation"] for f in data["features"]]
        assert elevations == sorted(elevations)

    def test_simplification_reduces_points(
        self, synthetic_dem: Path, tmp_dir: Path
    ) -> None:
        # Generate without simplification
        out_raw = tmp_dir / "raw.geojson"
        params_raw = ContourParams(interval=25.0, simplify_tolerance=0.0)
        generate_contours(synthetic_dem, out_raw, params_raw)

        # Generate with simplification
        out_simple = tmp_dir / "simple.geojson"
        params_simple = ContourParams(interval=25.0, simplify_tolerance=5.0)
        generate_contours(synthetic_dem, out_simple, params_simple)

        # Simplified file should generally be smaller
        raw_size = out_raw.stat().st_size
        simple_size = out_simple.stat().st_size
        # Allow for edge cases, but simplified should not be much larger
        assert simple_size <= raw_size * 1.1

    def test_flat_dem_produces_no_contours(
        self, synthetic_dem_flat: Path, tmp_dir: Path
    ) -> None:
        output = tmp_dir / "flat_contours.geojson"
        params = ContourParams(interval=10.0)
        generate_contours(synthetic_dem_flat, output, params)

        # A perfectly flat surface at 500m with 10m intervals should
        # produce at most one contour line (at exactly 500m)
        count = count_contours(output)
        assert count <= 1
