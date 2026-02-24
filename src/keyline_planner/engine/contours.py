"""Contour line extraction and formatting.

Responsibilities:
    - Generate contour isolines from a clipped DEM.
    - Format contours as GeoJSON with stable, deterministic output.
    - Apply optional simplification (Douglas-Peucker).
    - Sort and canonicalise features for golden-file testing.

Uses GDAL's gdal_contour utility for extraction, then post-processes
the output with Shapely for simplification and canonicalisation.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from shapely.geometry import mapping, shape

if TYPE_CHECKING:
    from keyline_planner.engine.models import ContourParams

logger = logging.getLogger(__name__)


def generate_contours(
    dem_path: Path,
    output_path: Path,
    params: ContourParams,
) -> Path:
    """Generate contour lines from a clipped DEM raster.

    Uses gdal_contour to extract isolines, then canonicalises the output
    for deterministic golden-file testing.

    Args:
        dem_path: Path to the clipped DEM GeoTIFF.
        output_path: Path for the output GeoJSON file.
        params: Contour generation parameters.

    Returns:
        Path to the generated GeoJSON file.

    Raises:
        subprocess.CalledProcessError: If gdal_contour fails.
    """
    # gdal_contour outputs to a temp file first (GeoJSON format)
    tmp_fd, tmp_name = tempfile.mkstemp(suffix=".geojson", prefix="keyline_contours_raw_")
    os.close(tmp_fd)
    # GDAL's GeoJSON driver refuses to overwrite existing files,
    # so remove the placeholder created by mkstemp.
    os.unlink(tmp_name)

    cmd = [
        "gdal_contour",
        "-i",
        str(params.interval),
        "-a",
        params.attribute_name,
        "-f",
        "GeoJSON",
        str(dem_path),
        tmp_name,
    ]

    logger.info(
        "Generating contours: interval=%.1f, attr=%s",
        params.interval,
        params.attribute_name,
    )
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    # Read raw contours
    raw_geojson = json.loads(Path(tmp_name).read_text())

    # Post-process: simplify, canonicalise, write final output
    features = raw_geojson.get("features", [])
    if not features:
        logger.warning("No contour features generated — DEM may be flat or too small")

    processed_features = _postprocess_features(features, params)

    # Write canonicalised output
    output_geojson = _build_canonical_geojson(processed_features, params)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output_geojson, indent=2, sort_keys=False))

    # Cleanup temp file
    Path(tmp_name).unlink(missing_ok=True)

    logger.info("Generated %d contour features → %s", len(processed_features), output_path)
    return output_path


def count_contours(geojson_path: Path) -> int:
    """Count the number of contour features in a GeoJSON file.

    Args:
        geojson_path: Path to a GeoJSON file.

    Returns:
        Number of features.
    """
    data = json.loads(geojson_path.read_text())
    return len(data.get("features", []))


def get_elevation_range(geojson_path: Path, attribute: str = "elevation") -> tuple[float, float]:
    """Get the min/max elevation from contour features.

    Args:
        geojson_path: Path to a GeoJSON contour file.
        attribute: Name of the elevation attribute.

    Returns:
        Tuple of (min_elevation, max_elevation).

    Raises:
        ValueError: If no features have the elevation attribute.
    """
    data = json.loads(geojson_path.read_text())
    elevations = [
        f["properties"][attribute]
        for f in data.get("features", [])
        if attribute in f.get("properties", {})
    ]
    if not elevations:
        msg = f"No features with attribute '{attribute}' found"
        raise ValueError(msg)
    return (min(elevations), max(elevations))


def _postprocess_features(
    features: list[dict[str, Any]],
    params: ContourParams,
) -> list[dict[str, Any]]:
    """Post-process contour features: simplify and clean.

    Args:
        features: Raw GeoJSON features from gdal_contour.
        params: Processing parameters.

    Returns:
        Processed list of features.
    """
    processed = []
    for feature in features:
        geom = shape(feature["geometry"])

        # Skip degenerate geometries
        if geom.is_empty or geom.length == 0:
            continue

        # Apply Douglas-Peucker simplification if requested
        if params.simplify_tolerance > 0:
            geom = geom.simplify(
                params.simplify_tolerance,
                preserve_topology=True,
            )
            if geom.is_empty:
                continue

        # Round coordinates to cm precision (LV95 is in meters)
        geom_dict = _round_geometry_coords(mapping(geom), precision=2)

        # Normalise elevation value
        elev = feature.get("properties", {}).get(params.attribute_name, 0.0)

        processed.append(
            {
                "type": "Feature",
                "geometry": geom_dict,
                "properties": {
                    params.attribute_name: round(float(elev), 2),
                },
            }
        )

    return processed


def _build_canonical_geojson(
    features: list[dict[str, Any]],
    params: ContourParams,
) -> dict[str, Any]:
    """Build a canonical GeoJSON FeatureCollection with stable ordering.

    Features are sorted by elevation (ascending), then by geometry bbox
    for features at the same elevation. This ensures deterministic output
    for golden-file testing.

    Args:
        features: Processed features.
        params: Processing parameters.

    Returns:
        Canonical GeoJSON FeatureCollection dict.
    """

    # Sort by (elevation, minx, miny) for deterministic ordering
    def sort_key(f: dict[str, Any]) -> tuple[float, float, float]:
        elev = f["properties"].get(params.attribute_name, 0.0)
        geom = shape(f["geometry"])
        bounds = geom.bounds  # (minx, miny, maxx, maxy)
        return (elev, bounds[0], bounds[1])

    sorted_features = sorted(features, key=sort_key)

    return {
        "type": "FeatureCollection",
        "features": sorted_features,
    }


def _round_geometry_coords(
    geom_dict: dict[str, Any],
    precision: int = 2,
) -> dict[str, Any]:
    """Round all coordinates in a GeoJSON geometry to a fixed precision.

    Args:
        geom_dict: GeoJSON geometry dictionary.
        precision: Number of decimal places.

    Returns:
        Geometry dict with rounded coordinates.
    """

    def _round_coords(coords: list[Any] | float) -> list[Any] | float:
        if isinstance(coords, (list, tuple)):
            if coords and isinstance(coords[0], (int, float)):
                return [round(c, precision) for c in coords]
            return [_round_coords(c) for c in coords]
        return coords

    return {
        "type": geom_dict["type"],
        "coordinates": _round_coords(geom_dict["coordinates"]),
    }
