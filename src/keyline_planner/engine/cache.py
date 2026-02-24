"""Content-addressed local tile and artifact cache.

Responsibilities:
    - Download and store raw swissALTI3D tiles.
    - Verify tile integrity against STAC checksums.
    - Manage derived artifact caching (clipped DEMs, contours).
    - Provide deterministic cache keys based on AOI + parameters.

Cache layout:
    <cache_root>/
        raw/
            <collection_id>/
                <item_id>/
                    <filename>.tif
                    metadata.json          # STAC item excerpt
        derived/
            <aoi_hash>/
                <param_hash>/
                    dem_clip.tif
                    contours.geojson
                    manifest.json          # derivation provenance
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import requests

if TYPE_CHECKING:
    from keyline_planner.engine.models import ContourParams, TileInfo

logger = logging.getLogger(__name__)

DEFAULT_CACHE_ROOT = Path.home() / ".cache" / "keyline-planner"

# Download timeout in seconds
_DOWNLOAD_TIMEOUT = 120


class TileCache:
    """Content-addressed cache for swissALTI3D tiles and derived artifacts."""

    def __init__(
        self, cache_root: Path | None = None, download_timeout: float | None = None
    ) -> None:
        """Initialise the cache.

        Args:
            cache_root: Root directory for the cache. Defaults to
                ``~/.cache/keyline-planner``.
            download_timeout: Tile download timeout in seconds. If omitted,
                value is loaded from ``KEYLINE_DOWNLOAD_TIMEOUT`` or defaults
                to 120 seconds.
        """
        self.root = cache_root or DEFAULT_CACHE_ROOT
        self.raw_dir = self.root / "raw"
        self.derived_dir = self.root / "derived"
        self.download_timeout = (
            _download_timeout_from_env() if download_timeout is None else download_timeout
        )

    def tile_path(self, tile: TileInfo) -> Path:
        """Return the expected local path for a raw tile.

        Args:
            tile: Tile metadata from STAC discovery.

        Returns:
            Path where the tile file should be stored.
        """
        filename = Path(urlparse(tile.asset_href).path).name
        return self.raw_dir / tile.collection_id / tile.item_id / filename

    def has_tile(self, tile: TileInfo) -> bool:
        """Check if a tile is already cached.

        Args:
            tile: Tile metadata.

        Returns:
            True if the tile file exists locally.
        """
        return self.tile_path(tile).exists()

    def download_tile(self, tile: TileInfo) -> Path:
        """Download a tile if not already cached, with checksum verification.

        Args:
            tile: Tile metadata including download URL and expected checksum.

        Returns:
            Path to the cached tile file.

        Raises:
            requests.HTTPError: If the download fails.
            ValueError: If checksum verification fails.
        """
        dest = self.tile_path(tile)

        if dest.exists():
            logger.debug("Cache hit: %s", dest)
            return dest

        logger.info("Downloading tile %s → %s", tile.item_id, dest)
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Download with streaming to handle large tiles
        with requests.get(tile.asset_href, stream=True, timeout=self.download_timeout) as response:
            response.raise_for_status()

            # Write to a temp file first, then rename for atomicity
            tmp_path = dest.with_suffix(".tmp")
            sha256 = hashlib.sha256()
            try:
                with open(tmp_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        sha256.update(chunk)

                # Verify checksum if available
                if tile.checksum is not None:
                    _verify_checksum(tile.checksum, sha256.hexdigest(), tile.item_id)

                tmp_path.rename(dest)
            except Exception:
                tmp_path.unlink(missing_ok=True)
                raise

        # Save tile metadata alongside
        self._save_tile_metadata(tile, dest.parent)

        logger.info("Cached tile: %s (%.1f MB)", dest, dest.stat().st_size / 1_048_576)
        return dest

    def ensure_tiles(self, tiles: list[TileInfo]) -> list[Path]:
        """Download all missing tiles and return their local paths.

        Args:
            tiles: List of tile metadata objects.

        Returns:
            List of local file paths for all tiles (in same order).
        """
        paths: list[Path] = []
        for tile in tiles:
            paths.append(self.download_tile(tile))
        return paths

    def derived_dir_for(self, aoi_hash: str, params: ContourParams) -> Path:
        """Return the cache directory for derived artifacts.

        Args:
            aoi_hash: Canonical hash of the AOI.
            params: Processing parameters.

        Returns:
            Path to the derived artifact directory.
        """
        param_hash = _params_hash(params)
        d = self.derived_dir / aoi_hash / param_hash
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _save_tile_metadata(self, tile: TileInfo, directory: Path) -> None:
        """Save a JSON excerpt of the tile's STAC metadata.

        Args:
            tile: Tile metadata.
            directory: Directory to write metadata.json into.
        """
        meta = {
            "item_id": tile.item_id,
            "collection_id": tile.collection_id,
            "asset_href": tile.asset_href,
            "checksum": tile.checksum,
            "gsd": tile.gsd,
            "epsg": tile.epsg,
            "bbox": tile.bbox,
            "updated": tile.updated,
        }
        meta_path = directory / "metadata.json"
        meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True))


def _verify_checksum(expected: str, actual_sha256: str, tile_id: str) -> None:
    """Verify a downloaded tile's checksum.

    Note: STAC checksums may use multihash encoding. This implementation
    supports plain SHA-256 hex and falls back to a warning for unknown formats.

    Args:
        expected: Expected checksum from STAC metadata.
        actual_sha256: SHA-256 hex digest of the downloaded file.
        tile_id: Tile identifier for error messages.

    Raises:
        ValueError: If checksums do not match.
    """
    # Simple case: plain SHA-256 hex
    if expected.lower() == actual_sha256.lower():
        return

    # Multihash prefix for SHA-256 is 1220 (0x12 = sha2-256, 0x20 = 32 bytes)
    if expected.lower().startswith("1220"):
        expected_hex = expected[4:].lower()
        if expected_hex == actual_sha256.lower():
            return
        msg = f"Checksum mismatch for tile {tile_id}: expected={expected_hex}, got={actual_sha256}"
        raise ValueError(msg)

    # Unknown format — log warning but don't fail
    logger.warning(
        "Cannot verify checksum format for tile %s (expected=%s). Skipping verification.",
        tile_id,
        expected[:20],
    )


def _download_timeout_from_env() -> float:
    """Return download timeout from environment with safe fallback."""
    raw = os.getenv("KEYLINE_DOWNLOAD_TIMEOUT")
    if raw is None:
        return float(_DOWNLOAD_TIMEOUT)

    try:
        timeout = float(raw)
    except ValueError:
        logger.warning(
            "Invalid KEYLINE_DOWNLOAD_TIMEOUT=%r; falling back to %ss.",
            raw,
            _DOWNLOAD_TIMEOUT,
        )
        return float(_DOWNLOAD_TIMEOUT)

    if timeout <= 0:
        logger.warning(
            "Non-positive KEYLINE_DOWNLOAD_TIMEOUT=%r; falling back to %ss.",
            raw,
            _DOWNLOAD_TIMEOUT,
        )
        return float(_DOWNLOAD_TIMEOUT)

    return timeout


def _params_hash(params: ContourParams) -> str:
    """Compute a deterministic hash of processing parameters.

    Args:
        params: Contour generation parameters.

    Returns:
        Short hex hash string.
    """
    serialised = json.dumps(
        {
            "interval": params.interval,
            "simplify_tolerance": params.simplify_tolerance,
            "resolution": params.resolution.value,
            "attribute_name": params.attribute_name,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialised.encode()).hexdigest()[:12]
