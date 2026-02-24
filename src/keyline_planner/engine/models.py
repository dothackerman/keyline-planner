"""Shared data models and value objects for the engine.

All models are immutable (frozen dataclasses) to support determinism
and referential transparency across the pipeline.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


class CRS(Enum):
    """Supported coordinate reference systems."""

    LV95 = "EPSG:2056"  # Swiss LV95 / CH1903+
    WGS84 = "EPSG:4326"  # WGS 84 (lat/lon)

    @property
    def epsg_code(self) -> int:
        """Return the integer EPSG code."""
        return int(self.value.split(":")[1])


class Resolution(Enum):
    """SwissALTI3D resolution tiers."""

    HIGH = 0.5  # 0.5 m — detailed, ~26 MB/tile
    STANDARD = 2.0  # 2.0 m — default, ~1 MB/tile


@dataclass(frozen=True)
class BBox:
    """Axis-aligned bounding box in a specific CRS.

    Attributes:
        xmin: Minimum x (easting or longitude).
        ymin: Minimum y (northing or latitude).
        xmax: Maximum x (easting or longitude).
        ymax: Maximum y (northing or latitude).
        crs: Coordinate reference system.
    """

    xmin: float
    ymin: float
    xmax: float
    ymax: float
    crs: CRS = CRS.LV95

    def __post_init__(self) -> None:
        """Validate bbox invariants."""
        if self.xmin >= self.xmax:
            msg = f"xmin ({self.xmin}) must be less than xmax ({self.xmax})"
            raise ValueError(msg)
        if self.ymin >= self.ymax:
            msg = f"ymin ({self.ymin}) must be less than ymax ({self.ymax})"
            raise ValueError(msg)

    def as_tuple(self) -> tuple[float, float, float, float]:
        """Return as (xmin, ymin, xmax, ymax) tuple."""
        return (self.xmin, self.ymin, self.xmax, self.ymax)

    @property
    def area_m2(self) -> float:
        """Approximate area in square meters (only meaningful for projected CRS)."""
        return (self.xmax - self.xmin) * (self.ymax - self.ymin)


@dataclass(frozen=True)
class AOI:
    """Area of Interest — the parcel geometry for processing.

    Can be specified as a GeoJSON geometry dict or a bounding box.
    Internally normalised to LV95 for all engine operations.

    Attributes:
        geometry: GeoJSON geometry dict (Polygon or MultiPolygon) in target CRS.
        bbox: Bounding box enclosing the geometry.
        source_crs: CRS of the original input (before normalisation).
    """

    geometry: dict[str, Any]
    bbox: BBox
    source_crs: CRS = CRS.LV95

    def canonical_hash(self) -> str:
        """Compute a deterministic hash of the AOI for cache keying.

        Geometry coordinates are rounded to 2 decimal places (cm precision
        in LV95) to ensure stable hashing across floating-point variations.
        """

        def _round_coordinates_array(value: Any, ndigits: int) -> Any:  # noqa: ANN401
            """Recursively round numeric coordinate values inside nested arrays."""
            if isinstance(value, list):
                return [_round_coordinates_array(v, ndigits) for v in value]
            if isinstance(value, tuple):
                return tuple(_round_coordinates_array(v, ndigits) for v in value)
            if isinstance(value, float):
                return round(value, ndigits)
            return value

        def _round_geometry_coords(obj: Any, ndigits: int) -> Any:  # noqa: ANN401
            """Return a copy of the GeoJSON geometry with rounded coordinates."""
            if isinstance(obj, dict):
                rounded: dict[str, Any] = {}
                for key, value in obj.items():
                    if key == "coordinates":
                        rounded[key] = _round_coordinates_array(value, ndigits)
                    else:
                        # Recurse into nested geometries (e.g. GeometryCollection)
                        rounded[key] = _round_geometry_coords(value, ndigits)
                return rounded
            if isinstance(obj, list):
                return [_round_geometry_coords(v, ndigits) for v in obj]
            if isinstance(obj, tuple):
                return tuple(_round_geometry_coords(v, ndigits) for v in obj)
            return obj

        # Create a normalised copy of the geometry with rounded coordinates
        rounded_geometry = _round_geometry_coords(self.geometry, ndigits=2)

        # Serialize geometry with sorted keys and rounded coordinates
        serialised = json.dumps(rounded_geometry, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialised.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class TileInfo:
    """Metadata for a single swissALTI3D tile discovered via STAC.

    Attributes:
        item_id: STAC Item identifier.
        collection_id: STAC Collection identifier.
        asset_href: Download URL for the tile asset.
        checksum: Multihash checksum from STAC metadata (for verification).
        gsd: Ground sample distance in meters.
        epsg: EPSG code of the tile's CRS.
        bbox: Spatial extent of the tile.
        updated: ISO 8601 timestamp of last update.
    """

    item_id: str
    collection_id: str
    asset_href: str
    checksum: str | None = None
    gsd: float = 2.0
    epsg: int = 2056
    bbox: tuple[float, float, float, float] | None = None
    updated: str | None = None


@dataclass(frozen=True)
class ContourParams:
    """Parameters for contour generation.

    Attributes:
        interval: Contour interval in meters.
        attribute_name: Name of the elevation attribute in output features.
        simplify_tolerance: Douglas-Peucker simplification tolerance in CRS
            units (meters for LV95). 0.0 means no simplification.
        resolution: DEM resolution to use.
    """

    interval: float = 1.0
    attribute_name: str = "elevation"
    simplify_tolerance: float = 0.0
    resolution: Resolution = Resolution.STANDARD

    def __post_init__(self) -> None:
        """Validate parameters."""
        if self.interval <= 0:
            msg = f"Contour interval must be positive, got {self.interval}"
            raise ValueError(msg)
        if self.simplify_tolerance < 0:
            msg = f"Simplify tolerance must be non-negative, got {self.simplify_tolerance}"
            raise ValueError(msg)


@dataclass(frozen=True)
class ProcessingResult:
    """Result of a contour generation run.

    Attributes:
        contours_path: Path to the generated contour file (GeoJSON).
        clipped_dem_path: Path to the clipped DEM raster (optional).
        contour_count: Number of contour lines generated.
        elevation_range: (min, max) elevation in the clipped DEM.
        aoi_hash: Canonical hash of the AOI used.
        params: Parameters used for generation.
        tile_ids: List of STAC tile IDs used.
        attribution: Required data attribution string.
    """

    contours_path: Path
    clipped_dem_path: Path | None
    contour_count: int
    elevation_range: tuple[float, float]
    aoi_hash: str
    params: ContourParams
    tile_ids: list[str] = field(default_factory=list)
    attribution: str = "Source: Federal Office of Topography swisstopo"
