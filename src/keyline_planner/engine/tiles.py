"""STAC-based tile discovery for swissALTI3D.

Responsibilities:
    - Query the Swiss federal STAC API for elevation tiles overlapping an AOI.
    - Parse STAC Items into TileInfo objects.
    - Filter tiles by resolution (GSD).

This module performs network I/O (STAC API queries) but encapsulates it
behind a clean interface that can be mocked in tests.
"""

from __future__ import annotations

import logging
from typing import Any

from pystac_client import Client
from pystac_client.exceptions import APIError
from pystac_client.warnings import DoesNotConformTo
from requests.exceptions import RequestException

from keyline_planner.engine.geometry import reproject_bbox
from keyline_planner.engine.models import AOI, CRS, Resolution, TileInfo

logger = logging.getLogger(__name__)

# Swiss federal STAC API endpoint
STAC_API_URL = "https://data.geo.admin.ch/api/stac/v0.9"

# SwissALTI3D collection ID
SWISSALTI3D_COLLECTION = "ch.swisstopo.swissalti3d"

# Asset key patterns for different resolutions
_ASSET_GSD_MAP: dict[Resolution, float] = {
    Resolution.STANDARD: 2.0,
    Resolution.HIGH: 0.5,
}


def discover_tiles(
    aoi: AOI,
    resolution: Resolution = Resolution.STANDARD,
    stac_url: str = STAC_API_URL,
    collection: str = SWISSALTI3D_COLLECTION,
) -> list[TileInfo]:
    """Discover swissALTI3D tiles overlapping the given AOI.

    Queries the STAC API using the AOI's bounding box and filters
    results by resolution (GSD).

    Args:
        aoi: Area of interest (must be in LV95).
        resolution: Desired DEM resolution.
        stac_url: STAC API endpoint URL (injectable for testing).
        collection: STAC collection ID.

    Returns:
        List of TileInfo objects for tiles overlapping the AOI.

    Raises:
        ConnectionError: If the STAC API is unreachable.
        ValueError: If no tiles are found for the given AOI.
    """
    target_gsd = _ASSET_GSD_MAP[resolution]

    # Convert AOI from LV95 to WGS84 for STAC API query
    wgs84_bbox = reproject_bbox(aoi.bbox, target_crs=CRS.WGS84)
    bbox = wgs84_bbox.as_tuple()

    logger.info(
        "Discovering tiles: collection=%s, bbox=%s (WGS84), gsd=%.1f",
        collection,
        bbox,
        target_gsd,
    )

    try:
        client = Client.open(stac_url)

        # Some STAC servers expose /search but do not advertise ITEM_SEARCH
        # conformance in landing-page metadata. Retry once with explicit override.
        try:
            search = client.search(
                collections=[collection],
                bbox=bbox,
            )
        except DoesNotConformTo as exc:
            logger.warning(
                "STAC conformance metadata incomplete (%s). Retrying with ITEM_SEARCH override.",
                exc,
            )
            client.add_conforms_to("ITEM_SEARCH")
            search = client.search(
                collections=[collection],
                bbox=bbox,
            )

        tiles: list[TileInfo] = []
        for item in search.items():
            tile = _parse_stac_item(item, target_gsd=target_gsd)
            if tile is not None:
                tiles.append(tile)
    except (RequestException, APIError) as exc:
        logger.error(
            "STAC API error: %s: %s",
            type(exc).__name__,
            str(exc),
        )
        msg = (
            f"Failed to reach STAC API at {stac_url}. "
            f"Underlying error: {type(exc).__name__}: {str(exc)}"
        )
        raise ConnectionError(msg) from exc

    if not tiles:
        msg = (
            f"No swissALTI3D tiles found for bbox={bbox} at gsd={target_gsd}. "
            "Check that the AOI is within Swiss territory."
        )
        raise ValueError(msg)

    logger.info("Discovered %d tile(s) for AOI", len(tiles))
    return tiles


def _parse_stac_item(
    item: Any,  # noqa: ANN401
    target_gsd: float,
) -> TileInfo | None:
    """Parse a STAC Item into a TileInfo, filtering by GSD.

    Args:
        item: A pystac Item object.
        target_gsd: Desired ground sample distance.

    Returns:
        TileInfo if a matching asset is found, None otherwise.
    """
    # Look through assets for one matching the target GSD
    for asset_key, asset in item.assets.items():
        # Skip non-GeoTIFF assets
        media_type = getattr(asset, "media_type", "") or ""
        if "tiff" not in media_type.lower() and not asset_key.endswith(".tif"):
            continue

        # Check GSD via extra_fields or asset properties
        asset_gsd = asset.extra_fields.get("gsd") or asset.extra_fields.get("eo:gsd")
        if asset_gsd is not None and float(asset_gsd) != target_gsd:
            continue

        # Extract checksum
        checksum = asset.extra_fields.get("file:checksum")

        # Extract EPSG
        epsg = (
            item.properties.get("proj:epsg")
            or asset.extra_fields.get("proj:epsg")
            or CRS.LV95.epsg_code
        )

        return TileInfo(
            item_id=item.id,
            collection_id=item.collection_id or SWISSALTI3D_COLLECTION,
            asset_href=asset.href,
            checksum=checksum,
            gsd=target_gsd,
            epsg=int(epsg),
            bbox=item.bbox,
            updated=item.properties.get("updated") or item.properties.get("datetime"),
        )

    return None
