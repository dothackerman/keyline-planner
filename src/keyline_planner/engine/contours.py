"""Contour line extraction and formatting.

Responsibilities:
    - Generate contour isolines from a clipped DEM.
    - Format contours with stable, deterministic output.
    - Apply optional simplification (Douglas-Peucker).
    - Sort and canonicalise features for golden-file testing.

Uses GDAL's gdal_contour utility for extraction, then post-processes the
output with Shapely for simplification and canonicalisation. Supports writing:
    - GeoJSON (WGS84, standards-compliant)
    - GeoPackage (LV95, CRS baked into layer metadata)
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

    Uses gdal_contour to extract isolines and writes standards-compliant
    WGS84 GeoJSON output.

    Args:
        dem_path: Path to the clipped DEM GeoTIFF.
        output_path: Path for the output GeoJSON file.
        params: Contour generation parameters.

    Returns:
        Path to the generated GeoJSON file.

    Raises:
        subprocess.CalledProcessError: If gdal_contour fails.
    """
    features_lv95 = extract_canonical_contour_features_lv95(dem_path, params)
    write_contours_geojson_wgs84(features_lv95, output_path, params)
    logger.info("Generated %d contour features → %s", len(features_lv95), output_path)
    return output_path


def extract_canonical_contour_features_lv95(
    dem_path: Path,
    params: ContourParams,
) -> list[dict[str, Any]]:
    """Extract canonical contour features in LV95 from a DEM raster.

    Args:
        dem_path: Path to the clipped DEM GeoTIFF.
        params: Contour generation parameters.

    Returns:
        Canonical contour features in LV95.

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
        "Extracting contours: interval=%.1f, attr=%s",
        params.interval,
        params.attribute_name,
    )
    try:
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            logger.error("gdal_contour failed with exit code %s", exc.returncode)
            if exc.stderr:
                logger.error("gdal_contour stderr:\n%s", exc.stderr.strip())
            if exc.stdout:
                logger.debug("gdal_contour stdout:\n%s", exc.stdout.strip())
            raise

        # Read raw contours
        raw_geojson = json.loads(Path(tmp_name).read_text())

        # Post-process: simplify, canonicalise, write final output
        features = raw_geojson.get("features", [])
        if not features:
            logger.warning("No contour features generated — DEM may be flat or too small")

        processed_features = _postprocess_features(features, params)
        canonical_geojson = _build_canonical_geojson(processed_features, params)
        canonical_features = canonical_geojson.get("features", [])
        return [feature for feature in canonical_features if isinstance(feature, dict)]
    finally:
        # Cleanup temp file on both success and failure paths
        Path(tmp_name).unlink(missing_ok=True)


def write_contours_geojson_wgs84(
    features_lv95: list[dict[str, Any]],
    output_path: Path,
    params: ContourParams,
) -> Path:
    """Write contour features as standards-compliant WGS84 GeoJSON.

    Args:
        features_lv95: Canonical contour features in LV95.
        output_path: Output GeoJSON path.
        params: Contour generation parameters.

    Returns:
        Path to the written GeoJSON file.
    """
    from keyline_planner.engine.geometry import reproject_geometry
    from keyline_planner.engine.models import CRS

    features_wgs84: list[dict[str, Any]] = []
    for feature in features_lv95:
        reprojected = reproject_geometry(
            feature["geometry"],
            source_crs=CRS.LV95,
            target_crs=CRS.WGS84,
        )
        features_wgs84.append(
            {
                "type": "Feature",
                "geometry": _round_geometry_coords(reprojected, precision=7),
                "properties": feature["properties"],
            }
        )

    output_geojson = {
        "type": "FeatureCollection",
        "features": features_wgs84,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output_geojson, indent=2, sort_keys=False))
    return output_path


def write_contours_gpkg_lv95(
    features_lv95: list[dict[str, Any]],
    output_path: Path,
    layer_name: str = "contours",
) -> Path:
    """Write contour features to a GeoPackage layer in LV95.

    Args:
        features_lv95: Canonical contour features in LV95.
        output_path: Output GeoPackage path.
        layer_name: GeoPackage layer name.

    Returns:
        Path to the written GeoPackage file.

    Raises:
        subprocess.CalledProcessError: If ogr2ogr fails.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.unlink(missing_ok=True)

    tmp_fd, tmp_name = tempfile.mkstemp(suffix=".geojson", prefix="keyline_contours_lv95_")
    try:
        with os.fdopen(tmp_fd, "w") as tmp:
            json.dump(
                {
                    "type": "FeatureCollection",
                    "features": features_lv95,
                },
                tmp,
            )

        cmd = [
            "ogr2ogr",
            "-f",
            "GPKG",
            str(output_path),
            tmp_name,
            "-nln",
            layer_name,
            "-a_srs",
            "EPSG:2056",
            "-overwrite",
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            logger.error("ogr2ogr failed with exit code %s", exc.returncode)
            if exc.stderr:
                logger.error("ogr2ogr stderr:\n%s", exc.stderr.strip())
            if exc.stdout:
                logger.debug("ogr2ogr stdout:\n%s", exc.stdout.strip())
            raise

        return output_path
    finally:
        Path(tmp_name).unlink(missing_ok=True)


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
