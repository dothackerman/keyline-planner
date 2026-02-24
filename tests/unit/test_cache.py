"""Unit tests for engine.cache — cache keying, layout, and verification."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from keyline_planner.engine.cache import (
    TileCache,
    _download_timeout_from_env,
    _params_hash,
    _verify_checksum,
)
from keyline_planner.engine.models import ContourParams, TileInfo

if TYPE_CHECKING:
    from pathlib import Path


class TestTileCache:
    """Tests for TileCache path management."""

    def test_tile_path_layout(self, tmp_dir: Path) -> None:
        cache = TileCache(cache_root=tmp_dir)
        tile = TileInfo(
            item_id="tile_001",
            collection_id="ch.swisstopo.swissalti3d",
            asset_href="https://example.com/data/tile_001_2m.tif",
        )
        path = cache.tile_path(tile)
        expected = tmp_dir / "raw" / "ch.swisstopo.swissalti3d" / "tile_001" / "tile_001_2m.tif"
        assert path == expected

    def test_has_tile_false_when_missing(self, tmp_dir: Path) -> None:
        cache = TileCache(cache_root=tmp_dir)
        tile = TileInfo(
            item_id="missing",
            collection_id="test",
            asset_href="https://example.com/missing.tif",
        )
        assert cache.has_tile(tile) is False

    def test_has_tile_true_when_exists(self, tmp_dir: Path) -> None:
        cache = TileCache(cache_root=tmp_dir)
        tile = TileInfo(
            item_id="exists",
            collection_id="test",
            asset_href="https://example.com/exists.tif",
        )
        path = cache.tile_path(tile)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake raster data")
        assert cache.has_tile(tile) is True

    def test_derived_dir_structure(self, tmp_dir: Path) -> None:
        cache = TileCache(cache_root=tmp_dir)
        params = ContourParams(interval=2.0)
        derived = cache.derived_dir_for("abc123", params)
        assert derived.parent.name == "abc123"
        assert derived.exists()


class TestVerifyChecksum:
    """Tests for checksum verification logic."""

    def test_matching_sha256(self) -> None:
        # Should not raise
        _verify_checksum("abcdef1234567890", "abcdef1234567890", "tile_1")

    def test_multihash_sha256(self) -> None:
        # Multihash prefix 1220 + sha256 hex
        expected = "1220abcdef1234567890"
        _verify_checksum(expected, "abcdef1234567890", "tile_1")

    def test_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="Checksum mismatch"):
            _verify_checksum("1220aaaa", "bbbb", "tile_1")


class TestParamsHash:
    """Tests for parameter hashing determinism."""

    def test_deterministic(self) -> None:
        p1 = ContourParams(interval=1.0)
        p2 = ContourParams(interval=1.0)
        assert _params_hash(p1) == _params_hash(p2)

    def test_different_params_different_hash(self) -> None:
        p1 = ContourParams(interval=1.0)
        p2 = ContourParams(interval=2.0)
        assert _params_hash(p1) != _params_hash(p2)

    def test_hash_length(self) -> None:
        params = ContourParams()
        assert len(_params_hash(params)) == 12


class TestDownloadTimeout:
    """Tests for environment-based download timeout parsing."""

    def test_uses_default_when_env_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("KEYLINE_DOWNLOAD_TIMEOUT", raising=False)
        assert _download_timeout_from_env() == 120.0

    def test_uses_env_when_valid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KEYLINE_DOWNLOAD_TIMEOUT", "300")
        assert _download_timeout_from_env() == 300.0

    def test_falls_back_when_invalid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KEYLINE_DOWNLOAD_TIMEOUT", "not-a-number")
        assert _download_timeout_from_env() == 120.0

    def test_falls_back_when_non_positive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KEYLINE_DOWNLOAD_TIMEOUT", "0")
        assert _download_timeout_from_env() == 120.0
