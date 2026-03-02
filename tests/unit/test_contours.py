"""Unit tests for engine.contours — contour post-processing and formatting."""

from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING

import pytest

from keyline_planner.engine.contours import (
    _build_canonical_geojson,
    _postprocess_features,
    _round_geometry_coords,
    count_contours,
    get_elevation_range,
    write_contours_geojson_wgs84,
    write_contours_gpkg_lv95,
)
from keyline_planner.engine.models import ContourParams

if TYPE_CHECKING:
    from pathlib import Path


class TestRoundGeometryCoords:
    """Tests for coordinate rounding."""

    def test_rounds_to_precision(self) -> None:
        geom = {
            "type": "LineString",
            "coordinates": [[1.23456, 2.34567], [3.45678, 4.56789]],
        }
        result = _round_geometry_coords(geom, precision=2)
        assert result["coordinates"] == [[1.23, 2.35], [3.46, 4.57]]

    def test_handles_polygon(self) -> None:
        geom = {
            "type": "Polygon",
            "coordinates": [[[1.111, 2.222], [3.333, 4.444], [1.111, 2.222]]],
        }
        result = _round_geometry_coords(geom, precision=1)
        assert result["coordinates"] == [[[1.1, 2.2], [3.3, 4.4], [1.1, 2.2]]]


class TestPostprocessFeatures:
    """Tests for feature post-processing."""

    def test_simplification_applied(self) -> None:
        features = [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [0.0, 0.0],
                        [0.5, 0.001],
                        [1.0, 0.0],
                        [1.5, 0.001],
                        [2.0, 0.0],
                    ],
                },
                "properties": {"elevation": 100.0},
            }
        ]
        params = ContourParams(simplify_tolerance=0.01)
        result = _postprocess_features(features, params)
        assert len(result) == 1
        # Simplified geometry should have fewer points
        assert len(result[0]["geometry"]["coordinates"]) <= len(
            features[0]["geometry"]["coordinates"]
        )

    def test_empty_geometry_skipped(self) -> None:
        features = [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": []},
                "properties": {"elevation": 100.0},
            }
        ]
        params = ContourParams()
        result = _postprocess_features(features, params)
        assert len(result) == 0


class TestCanonicalGeojson:
    """Tests for canonical GeoJSON ordering."""

    def test_sorted_by_elevation(self) -> None:
        features = [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 0]]},
                "properties": {"elevation": 300.0},
            },
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 0]]},
                "properties": {"elevation": 100.0},
            },
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 0]]},
                "properties": {"elevation": 200.0},
            },
        ]
        params = ContourParams()
        result = _build_canonical_geojson(features, params)
        elevs = [f["properties"]["elevation"] for f in result["features"]]
        assert elevs == [100.0, 200.0, 300.0]


class TestCountContours:
    """Tests for contour counting utility."""

    def test_counts_features(self, tmp_dir: Path) -> None:
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": {}, "properties": {}},
                {"type": "Feature", "geometry": {}, "properties": {}},
            ],
        }
        path = tmp_dir / "test.geojson"
        path.write_text(json.dumps(geojson))
        assert count_contours(path) == 2

    def test_empty_features(self, tmp_dir: Path) -> None:
        geojson = {"type": "FeatureCollection", "features": []}
        path = tmp_dir / "empty.geojson"
        path.write_text(json.dumps(geojson))
        assert count_contours(path) == 0


class TestGetElevationRange:
    """Tests for elevation range extraction."""

    def test_extracts_range(self, tmp_dir: Path) -> None:
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": {}, "properties": {"elevation": 500.0}},
                {"type": "Feature", "geometry": {}, "properties": {"elevation": 800.0}},
                {"type": "Feature", "geometry": {}, "properties": {"elevation": 600.0}},
            ],
        }
        path = tmp_dir / "contours.geojson"
        path.write_text(json.dumps(geojson))
        assert get_elevation_range(path) == (500.0, 800.0)

    def test_missing_attribute_raises(self, tmp_dir: Path) -> None:
        geojson = {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "geometry": {}, "properties": {}}],
        }
        path = tmp_dir / "no_elev.geojson"
        path.write_text(json.dumps(geojson))
        with pytest.raises(ValueError, match="No features"):
            get_elevation_range(path)


class TestOutputWriters:
    """Tests for contour output writers."""

    def test_write_geojson_wgs84_reprojects_coordinates(self, tmp_dir: Path) -> None:
        features_lv95 = [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[2600000.0, 1200000.0], [2600100.0, 1200100.0]],
                },
                "properties": {"elevation": 500.0},
            }
        ]
        output = tmp_dir / "contours.geojson"
        write_contours_geojson_wgs84(features_lv95, output, ContourParams())

        data = json.loads(output.read_text())
        coords = data["features"][0]["geometry"]["coordinates"][0]
        lon, lat = coords[0], coords[1]
        assert 5.0 <= lon <= 11.0
        assert 45.0 <= lat <= 48.5

    @pytest.mark.skipif(shutil.which("ogr2ogr") is None, reason="ogr2ogr is required")
    def test_write_gpkg_lv95_creates_file(self, tmp_dir: Path) -> None:
        features_lv95 = [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[2600000.0, 1200000.0], [2600100.0, 1200100.0]],
                },
                "properties": {"elevation": 500.0},
            }
        ]
        output = tmp_dir / "contours.gpkg"
        write_contours_gpkg_lv95(features_lv95, output)
        assert output.exists()
        assert output.stat().st_size > 0
