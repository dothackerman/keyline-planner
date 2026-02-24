"""End-to-end tests for the CLI interface.

These tests invoke the CLI via Typer's CliRunner, which runs the CLI
in-process for speed and hermeticity. They verify the full user-facing
contract without requiring network access (using synthetic data where
the pipeline is tested, and testing CLI argument parsing/validation here).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from keyline_planner.cli.main import app

pytestmark = pytest.mark.e2e

runner = CliRunner()


class TestCLIBasics:
    """Tests for CLI argument handling and validation."""

    def test_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "keyline" in result.output.lower() or "contour" in result.output.lower()

    def test_version(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_contours_help(self) -> None:
        result = runner.invoke(app, ["contours", "--help"])
        assert result.exit_code == 0
        assert "--bbox" in result.output
        assert "--geojson" in result.output

    def test_no_input_shows_error(self) -> None:
        result = runner.invoke(app, ["contours"])
        assert result.exit_code == 1

    def test_both_inputs_shows_error(
        self, sample_geojson_file: Path
    ) -> None:
        result = runner.invoke(app, [
            "contours",
            "--bbox", "2600000,1200000,2601000,1201000",
            "--geojson", str(sample_geojson_file),
        ])
        assert result.exit_code == 1

    def test_invalid_bbox_format(self) -> None:
        result = runner.invoke(app, ["contours", "--bbox", "not,valid"])
        assert result.exit_code == 1

    def test_invalid_crs(self) -> None:
        result = runner.invoke(app, [
            "contours",
            "--bbox", "2600000,1200000,2601000,1201000",
            "--crs", "invalid",
        ])
        assert result.exit_code == 1

    def test_invalid_resolution(self) -> None:
        result = runner.invoke(app, [
            "contours",
            "--bbox", "2600000,1200000,2601000,1201000",
            "--resolution", "ultra",
        ])
        assert result.exit_code == 1


class TestCLIGeojsonParsing:
    """Tests for GeoJSON file parsing in the CLI."""

    def test_loads_feature(self, tmp_dir: Path, sample_polygon_lv95: dict[str, Any]) -> None:
        path = tmp_dir / "feature.geojson"
        path.write_text(json.dumps({
            "type": "Feature",
            "geometry": sample_polygon_lv95,
            "properties": {},
        }))
        # This will fail at the pipeline step (no STAC), but it should
        # parse the GeoJSON successfully — exit code 1 from pipeline, not parsing
        result = runner.invoke(app, ["contours", "--geojson", str(path)])
        assert result.exit_code == 1
        # Should NOT contain "Failed to parse GeoJSON"
        assert "Failed to parse GeoJSON" not in result.output

    def test_loads_feature_collection(
        self, tmp_dir: Path, sample_polygon_lv95: dict[str, Any]
    ) -> None:
        path = tmp_dir / "collection.geojson"
        path.write_text(json.dumps({
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": sample_polygon_lv95,
                "properties": {},
            }],
        }))
        result = runner.invoke(app, ["contours", "--geojson", str(path)])
        assert result.exit_code == 1
        assert "Failed to parse GeoJSON" not in result.output

    def test_loads_raw_geometry(
        self, tmp_dir: Path, sample_polygon_lv95: dict[str, Any]
    ) -> None:
        path = tmp_dir / "raw.geojson"
        path.write_text(json.dumps(sample_polygon_lv95))
        result = runner.invoke(app, ["contours", "--geojson", str(path)])
        assert result.exit_code == 1
        assert "Failed to parse GeoJSON" not in result.output

    def test_invalid_json_shows_error(self, tmp_dir: Path) -> None:
        path = tmp_dir / "bad.geojson"
        path.write_text("not json {{{")
        result = runner.invoke(app, ["contours", "--geojson", str(path)])
        assert result.exit_code == 1
