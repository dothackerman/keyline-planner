"""DEM raster operations — mosaic, clip, resample.

Responsibilities:
    - Build a VRT mosaic from multiple tiles.
    - Clip the mosaic to an AOI polygon (cutline).
    - Optionally resample to a different resolution.

All operations use GDAL via rasterio and the osgeo.gdal utilities.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from keyline_planner.engine.models import AOI

logger = logging.getLogger(__name__)


def build_vrt(tile_paths: list[Path], output_path: Path) -> Path:
    """Build a GDAL VRT mosaic from multiple raster tiles.

    This is a lightweight operation — VRT is a virtual format that references
    the source tiles without copying data.

    Args:
        tile_paths: Paths to input GeoTIFF tiles.
        output_path: Path for the output VRT file.

    Returns:
        Path to the created VRT file.

    Raises:
        subprocess.CalledProcessError: If gdalbuildvrt fails.
        ValueError: If no tile paths are provided.
    """
    if not tile_paths:
        msg = "No tile paths provided for VRT construction"
        raise ValueError(msg)

    cmd = [
        "gdalbuildvrt",
        str(output_path),
        *[str(p) for p in tile_paths],
    ]

    logger.info("Building VRT: %d tiles → %s", len(tile_paths), output_path)
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    return output_path


def clip_dem(
    raster_path: Path,
    aoi: AOI,
    output_path: Path,
    nodata: float = -9999.0,
) -> Path:
    """Clip a DEM raster to an AOI polygon using gdalwarp.

    Uses the cutline mechanism for precise polygon clipping and crops
    the output to the cutline extent.

    Args:
        raster_path: Path to input raster (VRT or GeoTIFF).
        aoi: Area of interest with LV95 geometry.
        output_path: Path for the clipped output GeoTIFF.
        nodata: NoData value for output pixels outside the AOI.

    Returns:
        Path to the clipped DEM GeoTIFF.

    Raises:
        subprocess.CalledProcessError: If gdalwarp fails.
    """
    # Write AOI geometry to temporary GeoJSON for cutline
    cutline_path = _write_cutline_geojson(aoi)

    cmd = [
        "gdalwarp",
        "-cutline", str(cutline_path),
        "-crop_to_cutline",
        "-dstnodata", str(nodata),
        "-of", "GTiff",
        "-co", "COMPRESS=LZW",
        "-co", "TILED=YES",
        str(raster_path),
        str(output_path),
    ]

    logger.info("Clipping DEM to AOI → %s", output_path)
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    return output_path


def get_dem_stats(dem_path: Path) -> dict[str, Any]:
    """Read basic statistics from a DEM raster.

    Args:
        dem_path: Path to a single-band DEM GeoTIFF.

    Returns:
        Dictionary with keys: min, max, mean, std, nodata, width, height, crs.
    """
    import rasterio

    with rasterio.open(dem_path) as src:
        band = src.read(1, masked=True)
        return {
            "min": float(band.min()),
            "max": float(band.max()),
            "mean": float(band.mean()),
            "std": float(band.std()),
            "nodata": src.nodata,
            "width": src.width,
            "height": src.height,
            "crs": str(src.crs),
        }


def _write_cutline_geojson(aoi: AOI) -> Path:
    """Write AOI geometry to a temporary GeoJSON file for use as a GDAL cutline.

    Args:
        aoi: Area of interest with geometry.

    Returns:
        Path to the temporary GeoJSON file.
    """
    import json

    geojson = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": aoi.geometry,
            "properties": {},
        }],
    }

    # Use a named temp file that persists until process end
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".geojson",
        prefix="keyline_cutline_",
        delete=False,
    )
    json.dump(geojson, tmp)
    tmp.close()

    return Path(tmp.name)
