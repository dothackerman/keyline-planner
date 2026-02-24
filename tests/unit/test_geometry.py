"""Unit tests for engine.geometry — validation, CRS, and normalisation."""

from __future__ import annotations

from typing import Any

import pytest

from keyline_planner.engine.geometry import (
    bbox_to_geometry,
    geometry_to_bbox,
    normalise_aoi,
    reproject_geometry,
    validate_geojson_geometry,
)
from keyline_planner.engine.models import CRS, BBox


class TestValidateGeojsonGeometry:
    """Tests for geometry validation."""

    def test_valid_polygon(self, sample_polygon_lv95: dict[str, Any]) -> None:
        # Should not raise
        validate_geojson_geometry(sample_polygon_lv95)

    def test_invalid_type_point(self) -> None:
        with pytest.raises(ValueError, match="Unsupported geometry type"):
            validate_geojson_geometry({"type": "Point", "coordinates": [0, 0]})

    def test_invalid_type_linestring(self) -> None:
        with pytest.raises(ValueError, match="Unsupported geometry type"):
            validate_geojson_geometry(
                {
                    "type": "LineString",
                    "coordinates": [[0, 0], [1, 1]],
                }
            )

    def test_empty_polygon(self) -> None:
        with pytest.raises(ValueError):
            validate_geojson_geometry(
                {
                    "type": "Polygon",
                    "coordinates": [],
                }
            )


class TestReprojectGeometry:
    """Tests for CRS reprojection."""

    def test_same_crs_is_identity(self, sample_polygon_lv95: dict[str, Any]) -> None:
        result = reproject_geometry(sample_polygon_lv95, CRS.LV95, CRS.LV95)
        assert result == sample_polygon_lv95

    def test_wgs84_to_lv95_produces_large_coords(
        self, sample_polygon_wgs84: dict[str, Any]
    ) -> None:
        result = reproject_geometry(sample_polygon_wgs84, CRS.WGS84, CRS.LV95)
        # LV95 coordinates should be in the millions range
        coords = result["coordinates"][0][0]
        assert coords[0] > 2_000_000
        assert coords[1] > 1_000_000

    def test_lv95_to_wgs84_roundtrip(self, sample_polygon_lv95: dict[str, Any]) -> None:
        wgs84 = reproject_geometry(sample_polygon_lv95, CRS.LV95, CRS.WGS84)
        back = reproject_geometry(wgs84, CRS.WGS84, CRS.LV95)
        # Should be approximately the same (within 0.01m for LV95)
        orig_x = sample_polygon_lv95["coordinates"][0][0][0]
        back_x = back["coordinates"][0][0][0]
        assert abs(orig_x - back_x) < 0.01

    def test_same_crs_returns_unchanged(self, sample_polygon_lv95: dict[str, Any]) -> None:
        result = reproject_geometry(sample_polygon_lv95, CRS.LV95, CRS.LV95)
        assert result == sample_polygon_lv95


class TestGeometryToBBox:
    """Tests for geometry → bbox conversion."""

    def test_polygon_bbox(self, sample_polygon_lv95: dict[str, Any]) -> None:
        bbox = geometry_to_bbox(sample_polygon_lv95)
        assert bbox.xmin == 2600100.0
        assert bbox.ymin == 1200100.0
        assert bbox.xmax == 2600600.0
        assert bbox.ymax == 1200600.0
        assert bbox.crs == CRS.LV95


class TestBboxToGeometry:
    """Tests for bbox → geometry conversion."""

    def test_produces_polygon(self) -> None:
        bbox = BBox(xmin=0, ymin=0, xmax=1, ymax=1)
        geom = bbox_to_geometry(bbox)
        assert geom["type"] == "Polygon"
        assert len(geom["coordinates"][0]) == 5  # Closed ring


class TestNormaliseAoi:
    """Tests for the normalise_aoi entry point."""

    def test_bbox_input(self, sample_bbox_lv95: tuple[float, float, float, float]) -> None:
        aoi = normalise_aoi(bbox=sample_bbox_lv95)
        assert aoi.bbox.crs == CRS.LV95
        assert aoi.source_crs == CRS.LV95

    def test_geojson_input(self, sample_polygon_lv95: dict[str, Any]) -> None:
        aoi = normalise_aoi(geojson=sample_polygon_lv95)
        assert aoi.bbox.crs == CRS.LV95
        assert aoi.geometry["type"] == "Polygon"

    def test_wgs84_input_reprojected(self, sample_polygon_wgs84: dict[str, Any]) -> None:
        aoi = normalise_aoi(geojson=sample_polygon_wgs84, crs=CRS.WGS84)
        # Result should be in LV95
        assert aoi.bbox.crs == CRS.LV95
        assert aoi.source_crs == CRS.WGS84
        # Coordinates should be in LV95 range
        assert aoi.bbox.xmin > 2_000_000

    def test_both_inputs_raises(
        self,
        sample_polygon_lv95: dict[str, Any],
        sample_bbox_lv95: tuple[float, float, float, float],
    ) -> None:
        with pytest.raises(ValueError, match="not both"):
            normalise_aoi(geojson=sample_polygon_lv95, bbox=sample_bbox_lv95)

    def test_no_inputs_raises(self) -> None:
        with pytest.raises(ValueError, match="Provide either"):
            normalise_aoi()

    def test_outside_switzerland_raises(self) -> None:
        geom = {
            "type": "Polygon",
            "coordinates": [
                [
                    [0.0, 0.0],
                    [1.0, 0.0],
                    [1.0, 1.0],
                    [0.0, 1.0],
                    [0.0, 0.0],
                ]
            ],
        }
        with pytest.raises(ValueError, match="outside Swiss territory"):
            normalise_aoi(geojson=geom, crs=CRS.LV95)
