"""Pipeline orchestrator — ties engine modules into a complete workflow.

This module composes the engine skills (geometry, tiles, cache, raster,
contours) into a single deterministic pipeline. It is the boundary between
"skill composition" and "agent orchestration" — agents call this pipeline,
and this pipeline calls skills.

The pipeline is stateless: all state flows through explicit parameters
and the cache. Identical inputs produce identical outputs.
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any

from keyline_planner.engine.cache import TileCache
from keyline_planner.engine.contours import count_contours, generate_contours
from keyline_planner.engine.geometry import normalise_aoi
from keyline_planner.engine.models import CRS, ContourParams, ProcessingResult, Resolution
from keyline_planner.engine.raster import build_vrt, clip_dem, get_dem_stats
from keyline_planner.engine.tiles import discover_tiles

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


def run_contour_pipeline(
    geojson: dict[str, Any] | None = None,
    bbox: tuple[float, float, float, float] | None = None,
    crs: CRS = CRS.LV95,
    interval: float = 1.0,
    resolution: Resolution = Resolution.STANDARD,
    simplify_tolerance: float = 0.0,
    output_dir: Path | None = None,
    cache_root: Path | None = None,
    save_clipped_dem: bool = True,
) -> ProcessingResult:
    """Run the full contour generation pipeline.

    This is the primary entry point for the engine. It:
    1. Normalises the AOI to LV95
    2. Discovers required elevation tiles via STAC
    3. Downloads/caches tiles
    4. Builds a VRT mosaic
    5. Clips the DEM to the AOI
    6. Generates contour lines
    7. Writes outputs and provenance metadata

    Args:
        geojson: GeoJSON geometry dict (Polygon/MultiPolygon).
        bbox: Bounding box as (xmin, ymin, xmax, ymax).
        crs: CRS of the input geometry/bbox.
        interval: Contour interval in meters.
        resolution: DEM resolution to use.
        simplify_tolerance: Douglas-Peucker tolerance (0 = no simplification).
        output_dir: Directory for output files. Defaults to derived cache dir.
        cache_root: Root directory for tile cache.
        save_clipped_dem: Whether to keep the clipped DEM raster in output.

    Returns:
        ProcessingResult with paths and metadata.

    Raises:
        ValueError: If inputs are invalid.
        ConnectionError: If STAC API is unreachable.
        subprocess.CalledProcessError: If GDAL operations fail.
    """
    t0 = time.monotonic()

    # --- Step 1: Normalise AOI ---
    logger.info("Step 1/6: Normalising AOI")
    aoi = normalise_aoi(geojson=geojson, bbox=bbox, crs=crs)
    aoi_hash = aoi.canonical_hash()
    logger.info("AOI hash: %s, area: %.0f m²", aoi_hash, aoi.bbox.area_m2)

    # --- Step 2: Set up parameters and output dirs ---
    params = ContourParams(
        interval=interval,
        resolution=resolution,
        simplify_tolerance=simplify_tolerance,
    )

    cache = TileCache(cache_root=cache_root)

    if output_dir is None:
        output_dir = cache.derived_dir_for(aoi_hash, params)
    else:
        output_dir.mkdir(parents=True, exist_ok=True)

    # --- Step 3: Discover tiles ---
    logger.info("Step 2/6: Discovering elevation tiles")
    tiles = discover_tiles(aoi=aoi, resolution=resolution)
    tile_ids = [t.item_id for t in tiles]
    logger.info("Found %d tile(s): %s", len(tiles), tile_ids)

    # --- Step 4: Download/cache tiles ---
    logger.info("Step 3/6: Ensuring tiles are cached")
    tile_paths = cache.ensure_tiles(tiles)

    # --- Step 5: Build VRT mosaic ---
    logger.info("Step 4/6: Building VRT mosaic")
    vrt_path = output_dir / "mosaic.vrt"
    build_vrt(tile_paths, vrt_path)

    # --- Step 6: Clip DEM to AOI ---
    logger.info("Step 5/6: Clipping DEM to AOI")
    dem_clip_path = output_dir / "dem_clip.tif"
    clip_dem(vrt_path, aoi, dem_clip_path)

    dem_stats = get_dem_stats(dem_clip_path)
    elevation_range = (dem_stats["min"], dem_stats["max"])
    logger.info("DEM elevation range: %.1f - %.1f m", *elevation_range)

    # --- Step 7: Generate contours ---
    logger.info("Step 6/6: Generating contours")
    contours_path = output_dir / "contours.geojson"
    generate_contours(dem_clip_path, contours_path, params)

    contour_count = count_contours(contours_path)

    # Optionally remove clipped DEM to save space
    clipped_dem_final: Path | None = None
    if save_clipped_dem:
        clipped_dem_final = dem_clip_path
    else:
        dem_clip_path.unlink(missing_ok=True)

    # Write provenance manifest
    elapsed = time.monotonic() - t0
    _write_manifest(
        output_dir=output_dir,
        aoi_hash=aoi_hash,
        params=params,
        tile_ids=tile_ids,
        dem_stats=dem_stats,
        contour_count=contour_count,
        elapsed_seconds=elapsed,
    )

    result = ProcessingResult(
        contours_path=contours_path,
        clipped_dem_path=clipped_dem_final,
        contour_count=contour_count,
        elevation_range=elevation_range,
        aoi_hash=aoi_hash,
        params=params,
        tile_ids=tile_ids,
    )

    logger.info(
        "Pipeline complete: %d contours in %.1fs → %s",
        contour_count,
        elapsed,
        output_dir,
    )

    return result


def _write_manifest(
    output_dir: Path,
    aoi_hash: str,
    params: ContourParams,
    tile_ids: list[str],
    dem_stats: dict[str, Any],
    contour_count: int,
    elapsed_seconds: float,
) -> None:
    """Write a provenance manifest for the pipeline run.

    This JSON file records exactly how the output was produced,
    enabling reproducibility verification and cache invalidation.

    Args:
        output_dir: Output directory to write manifest into.
        aoi_hash: Canonical hash of the AOI.
        params: Processing parameters used.
        tile_ids: STAC tile IDs processed.
        dem_stats: DEM statistics from the clipped raster.
        contour_count: Number of contour features generated.
        elapsed_seconds: Total pipeline runtime.
    """
    manifest = {
        "aoi_hash": aoi_hash,
        "parameters": {
            "interval": params.interval,
            "resolution": params.resolution.value,
            "simplify_tolerance": params.simplify_tolerance,
            "attribute_name": params.attribute_name,
        },
        "tiles_used": tile_ids,
        "dem_stats": dem_stats,
        "contour_count": contour_count,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "attribution": "Source: Federal Office of Topography swisstopo",
    }

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    logger.debug("Wrote manifest: %s", manifest_path)
