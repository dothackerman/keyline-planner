"""Integration tests for pipeline output-format behaviour."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

from keyline_planner.engine.models import OutputFormat, TileInfo
from keyline_planner.engine.pipeline import run_contour_pipeline

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.integration


def _patch_pipeline_boundaries(monkeypatch: pytest.MonkeyPatch, tmp_dir: Path) -> None:
    """Patch I/O boundaries so output-format logic can be tested deterministically."""

    def _discover_tiles(**_: Any) -> list[TileInfo]:
        return [
            TileInfo(
                item_id="tile_001",
                collection_id="ch.swisstopo.swissalti3d",
                asset_href="https://example.com/tile_001.tif",
            )
        ]

    def _ensure_tiles(self: Any, tiles: list[TileInfo]) -> list[Path]:
        assert tiles
        tile_path = tmp_dir / "tile_001.tif"
        tile_path.write_text("tile")
        return [tile_path]

    def _build_vrt(tile_paths: list[Path], output_path: Path) -> Path:
        assert tile_paths
        output_path.write_text("vrt")
        return output_path

    def _clip_dem(raster_path: Path, aoi: Any, output_path: Path) -> Path:
        assert raster_path.exists()
        assert aoi is not None
        output_path.write_text("dem")
        return output_path

    def _get_dem_stats(_: Path) -> dict[str, Any]:
        return {
            "min": 500.0,
            "max": 700.0,
            "mean": 600.0,
            "std": 50.0,
            "nodata": -9999.0,
            "width": 100,
            "height": 100,
            "crs": "EPSG:2056",
        }

    def _extract_features(_: Path, __: Any) -> list[dict[str, Any]]:
        return [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[2600000.0, 1200000.0], [2600100.0, 1200100.0]],
                },
                "properties": {"elevation": 500.0},
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[2600200.0, 1200200.0], [2600300.0, 1200300.0]],
                },
                "properties": {"elevation": 510.0},
            },
        ]

    def _write_gpkg(features: list[dict[str, Any]], output_path: Path, **_: Any) -> Path:
        assert len(features) == 2
        output_path.write_text("gpkg")
        return output_path

    def _write_geojson(
        features: list[dict[str, Any]],
        output_path: Path,
        params: Any,
    ) -> Path:
        assert len(features) == 2
        assert params is not None
        output_path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
        return output_path

    monkeypatch.setattr("keyline_planner.engine.pipeline.discover_tiles", _discover_tiles)
    monkeypatch.setattr("keyline_planner.engine.pipeline.TileCache.ensure_tiles", _ensure_tiles)
    monkeypatch.setattr("keyline_planner.engine.pipeline.build_vrt", _build_vrt)
    monkeypatch.setattr("keyline_planner.engine.pipeline.clip_dem", _clip_dem)
    monkeypatch.setattr("keyline_planner.engine.pipeline.get_dem_stats", _get_dem_stats)
    monkeypatch.setattr(
        "keyline_planner.engine.pipeline.extract_canonical_contour_features_lv95",
        _extract_features,
    )
    monkeypatch.setattr("keyline_planner.engine.pipeline.write_contours_gpkg_lv95", _write_gpkg)
    monkeypatch.setattr(
        "keyline_planner.engine.pipeline.write_contours_geojson_wgs84",
        _write_geojson,
    )


@pytest.mark.parametrize(
    "output_format",
    [OutputFormat.GPKG, OutputFormat.GEOJSON, OutputFormat.BOTH],
)
def test_pipeline_respects_output_format(
    output_format: OutputFormat,
    monkeypatch: pytest.MonkeyPatch,
    tmp_dir: Path,
) -> None:
    _patch_pipeline_boundaries(monkeypatch, tmp_dir)

    output_dir = tmp_dir / f"out_{output_format.value}"
    result = run_contour_pipeline(
        bbox=(2600000.0, 1200000.0, 2601000.0, 1201000.0),
        output_dir=output_dir,
        output_format=output_format,
    )

    manifest = json.loads((output_dir / "manifest.json").read_text())

    assert manifest["output_format"] == output_format.value
    assert manifest["outputs"].keys() == {"gpkg", "geojson"}
    assert result.contour_count == 2

    if output_format == OutputFormat.GPKG:
        assert result.contours_path.suffix == ".gpkg"
        assert result.contours_gpkg_path is not None
        assert result.contours_geojson_path is None
        assert manifest["outputs"]["gpkg"] is not None
        assert manifest["outputs"]["geojson"] is None
    elif output_format == OutputFormat.GEOJSON:
        assert result.contours_path.suffix == ".geojson"
        assert result.contours_gpkg_path is None
        assert result.contours_geojson_path is not None
        assert manifest["outputs"]["gpkg"] is None
        assert manifest["outputs"]["geojson"] is not None
    else:
        assert result.contours_path.suffix == ".gpkg"
        assert result.contours_gpkg_path is not None
        assert result.contours_geojson_path is not None
        assert manifest["outputs"]["gpkg"] is not None
        assert manifest["outputs"]["geojson"] is not None


def test_pipeline_default_output_format_is_gpkg(
    monkeypatch: pytest.MonkeyPatch,
    tmp_dir: Path,
) -> None:
    _patch_pipeline_boundaries(monkeypatch, tmp_dir)

    output_dir = tmp_dir / "out_default"
    result = run_contour_pipeline(
        bbox=(2600000.0, 1200000.0, 2601000.0, 1201000.0),
        output_dir=output_dir,
    )

    manifest = json.loads((output_dir / "manifest.json").read_text())
    assert result.contours_path.suffix == ".gpkg"
    assert manifest["output_format"] == "gpkg"
