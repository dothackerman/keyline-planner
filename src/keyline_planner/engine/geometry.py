"""Geometry validation, normalisation, and CRS transformation.

Responsibilities:
    - Validate input geometries (GeoJSON Polygon / MultiPolygon / BBox).
    - Reproject from WGS84 to LV95 (EPSG:2056) when needed.
    - Compute bounding boxes from geometries.
    - Normalise geometries to a canonical form for deterministic hashing.

This module has no side effects and no I/O.
"""

from __future__ import annotations

from typing import Any

from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform

from keyline_planner.engine.models import AOI, CRS, BBox

# Cached transformers (thread-safe, stateless after creation)
_TRANSFORMER_WGS84_TO_LV95 = Transformer.from_crs(CRS.WGS84.value, CRS.LV95.value, always_xy=True)
_TRANSFORMER_LV95_TO_WGS84 = Transformer.from_crs(CRS.LV95.value, CRS.WGS84.value, always_xy=True)

# Swiss LV95 approximate bounds (for sanity checks)
_LV95_BOUNDS = BBox(
    xmin=2_485_000.0,
    ymin=1_075_000.0,
    xmax=2_834_000.0,
    ymax=1_296_000.0,
    crs=CRS.LV95,
)


def validate_geojson_geometry(geojson: dict[str, Any]) -> None:
    """Validate that a GeoJSON geometry dict is a supported type.

    Args:
        geojson: GeoJSON geometry dictionary.

    Raises:
        ValueError: If geometry type is unsupported or geometry is invalid.
    """
    geo_type = geojson.get("type")
    if geo_type not in ("Polygon", "MultiPolygon"):
        msg = f"Unsupported geometry type: {geo_type}. Expected Polygon or MultiPolygon."
        raise ValueError(msg)

    geom = shape(geojson)
    if not geom.is_valid:
        from shapely import validation

        msg = f"Invalid geometry: {validation.explain_validity(geom)}"
        raise ValueError(msg)

    if geom.is_empty:
        msg = "Geometry is empty"
        raise ValueError(msg)


def reproject_geometry(
    geojson: dict[str, Any],
    source_crs: CRS,
    target_crs: CRS,
) -> dict[str, Any]:
    """Reproject a GeoJSON geometry between supported CRS.

    Args:
        geojson: GeoJSON geometry dictionary.
        source_crs: Source coordinate reference system.
        target_crs: Target coordinate reference system.

    Returns:
        Reprojected GeoJSON geometry dictionary.
    """
    if source_crs == target_crs:
        return geojson

    if source_crs == CRS.WGS84 and target_crs == CRS.LV95:
        transformer = _TRANSFORMER_WGS84_TO_LV95
    elif source_crs == CRS.LV95 and target_crs == CRS.WGS84:
        transformer = _TRANSFORMER_LV95_TO_WGS84
    else:
        msg = f"Unsupported CRS transformation: {source_crs} -> {target_crs}"
        raise ValueError(msg)

    geom = shape(geojson)
    reprojected = transform(transformer.transform, geom)
    return dict(mapping(reprojected))


def geometry_to_bbox(geojson: dict[str, Any], crs: CRS = CRS.LV95) -> BBox:
    """Compute the bounding box of a GeoJSON geometry.

    Args:
        geojson: GeoJSON geometry dictionary.
        crs: CRS of the geometry.

    Returns:
        BBox enclosing the geometry.
    """
    geom = shape(geojson)
    bounds = geom.bounds  # (minx, miny, maxx, maxy)
    return BBox(
        xmin=bounds[0],
        ymin=bounds[1],
        xmax=bounds[2],
        ymax=bounds[3],
        crs=crs,
    )


def reproject_bbox(
    bbox: BBox,
    target_crs: CRS,
) -> BBox:
    """Reproject a BBox from its current CRS to a target CRS.

    Args:
        bbox: Bounding box to reproject.
        target_crs: Target coordinate reference system.

    Returns:
        Reprojected BBox.
    """
    if bbox.crs == target_crs:
        return bbox

    # Convert bbox to geometry, reproject, extract bounds
    geojson = bbox_to_geometry(bbox)
    reprojected_geojson = reproject_geometry(geojson, source_crs=bbox.crs, target_crs=target_crs)
    return geometry_to_bbox(reprojected_geojson, crs=target_crs)


def bbox_to_geometry(bbox: BBox) -> dict[str, Any]:
    """Convert a BBox to a GeoJSON Polygon geometry.

    Args:
        bbox: Bounding box to convert.

    Returns:
        GeoJSON Polygon geometry dictionary.
    """
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [bbox.xmin, bbox.ymin],
                [bbox.xmax, bbox.ymin],
                [bbox.xmax, bbox.ymax],
                [bbox.xmin, bbox.ymax],
                [bbox.xmin, bbox.ymin],
            ]
        ],
    }


def normalise_aoi(
    geojson: dict[str, Any] | None = None,
    bbox: tuple[float, float, float, float] | None = None,
    crs: CRS = CRS.LV95,
) -> AOI:
    """Normalise an input AOI to LV95 coordinates.

    Accepts either a GeoJSON geometry or a bbox tuple. Exactly one must be
    provided. If the input is in WGS84, it is reprojected to LV95.

    Args:
        geojson: GeoJSON geometry dict (Polygon or MultiPolygon).
        bbox: Bounding box as (xmin, ymin, xmax, ymax).
        crs: CRS of the input.

    Returns:
        Normalised AOI in LV95.

    Raises:
        ValueError: If inputs are invalid or ambiguous.
    """
    if geojson is not None and bbox is not None:
        msg = "Provide either geojson or bbox, not both."
        raise ValueError(msg)

    if geojson is None and bbox is None:
        msg = "Provide either geojson or bbox."
        raise ValueError(msg)

    # If bbox provided, convert to geometry first
    if bbox is not None:
        input_bbox = BBox(xmin=bbox[0], ymin=bbox[1], xmax=bbox[2], ymax=bbox[3], crs=crs)
        geojson = bbox_to_geometry(input_bbox)

    assert geojson is not None  # for type narrowing

    # Validate geometry
    validate_geojson_geometry(geojson)

    # Reproject to LV95 if needed
    if crs != CRS.LV95:
        geojson = reproject_geometry(geojson, source_crs=crs, target_crs=CRS.LV95)

    # Compute LV95 bbox
    aoi_bbox = geometry_to_bbox(geojson, crs=CRS.LV95)

    # Sanity check: is the AOI within Switzerland?
    _check_within_switzerland(aoi_bbox)

    return AOI(geometry=geojson, bbox=aoi_bbox, source_crs=crs)


def _check_within_switzerland(bbox: BBox) -> None:
    """Warn if bbox is entirely outside Swiss LV95 bounds.

    Raises:
        ValueError: If the bbox does not intersect Swiss territory at all.
    """
    if (
        bbox.xmax < _LV95_BOUNDS.xmin
        or bbox.xmin > _LV95_BOUNDS.xmax
        or bbox.ymax < _LV95_BOUNDS.ymin
        or bbox.ymin > _LV95_BOUNDS.ymax
    ):
        msg = (
            f"AOI bbox {bbox.as_tuple()} appears to be outside Swiss territory "
            f"(LV95 bounds: {_LV95_BOUNDS.as_tuple()}). "
            "Check your CRS and coordinates."
        )
        raise ValueError(msg)
