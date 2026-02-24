"""Unit tests for engine.models — data model validation and behaviour."""

from __future__ import annotations

import pytest

from keyline_planner.engine.models import (
    AOI,
    BBox,
    CRS,
    ContourParams,
    Resolution,
)


class TestBBox:
    """Tests for BBox construction and validation."""

    def test_valid_bbox(self) -> None:
        bbox = BBox(xmin=1.0, ymin=2.0, xmax=3.0, ymax=4.0)
        assert bbox.as_tuple() == (1.0, 2.0, 3.0, 4.0)

    def test_invalid_xmin_ge_xmax(self) -> None:
        with pytest.raises(ValueError, match="xmin"):
            BBox(xmin=5.0, ymin=2.0, xmax=3.0, ymax=4.0)

    def test_invalid_ymin_ge_ymax(self) -> None:
        with pytest.raises(ValueError, match="ymin"):
            BBox(xmin=1.0, ymin=5.0, xmax=3.0, ymax=4.0)

    def test_area_m2(self) -> None:
        bbox = BBox(xmin=0.0, ymin=0.0, xmax=100.0, ymax=200.0)
        assert bbox.area_m2 == 20000.0

    def test_default_crs_is_lv95(self) -> None:
        bbox = BBox(xmin=1.0, ymin=2.0, xmax=3.0, ymax=4.0)
        assert bbox.crs == CRS.LV95

    def test_frozen(self) -> None:
        bbox = BBox(xmin=1.0, ymin=2.0, xmax=3.0, ymax=4.0)
        with pytest.raises(AttributeError):
            bbox.xmin = 99.0  # type: ignore[misc]


class TestCRS:
    """Tests for CRS enum."""

    def test_lv95_epsg(self) -> None:
        assert CRS.LV95.epsg_code == 2056

    def test_wgs84_epsg(self) -> None:
        assert CRS.WGS84.epsg_code == 4326


class TestResolution:
    """Tests for Resolution enum."""

    def test_standard_is_2m(self) -> None:
        assert Resolution.STANDARD.value == 2.0

    def test_high_is_half_meter(self) -> None:
        assert Resolution.HIGH.value == 0.5


class TestContourParams:
    """Tests for ContourParams validation."""

    def test_defaults(self) -> None:
        params = ContourParams()
        assert params.interval == 1.0
        assert params.attribute_name == "elevation"
        assert params.simplify_tolerance == 0.0
        assert params.resolution == Resolution.STANDARD

    def test_custom_params(self) -> None:
        params = ContourParams(interval=5.0, simplify_tolerance=1.5)
        assert params.interval == 5.0
        assert params.simplify_tolerance == 1.5

    def test_invalid_interval_zero(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            ContourParams(interval=0.0)

    def test_invalid_interval_negative(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            ContourParams(interval=-1.0)

    def test_invalid_simplify_negative(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            ContourParams(simplify_tolerance=-0.5)


class TestAOI:
    """Tests for AOI canonical hashing."""

    def test_canonical_hash_deterministic(self) -> None:
        geom = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}
        bbox = BBox(xmin=0, ymin=0, xmax=1, ymax=1)
        aoi1 = AOI(geometry=geom, bbox=bbox)
        aoi2 = AOI(geometry=geom, bbox=bbox)
        assert aoi1.canonical_hash() == aoi2.canonical_hash()

    def test_canonical_hash_changes_with_geometry(self) -> None:
        geom1 = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}
        geom2 = {"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 0]]]}
        bbox = BBox(xmin=0, ymin=0, xmax=2, ymax=2)
        aoi1 = AOI(geometry=geom1, bbox=bbox)
        aoi2 = AOI(geometry=geom2, bbox=bbox)
        assert aoi1.canonical_hash() != aoi2.canonical_hash()

    def test_canonical_hash_length(self) -> None:
        geom = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}
        bbox = BBox(xmin=0, ymin=0, xmax=1, ymax=1)
        aoi = AOI(geometry=geom, bbox=bbox)
        assert len(aoi.canonical_hash()) == 16  # Truncated SHA-256
