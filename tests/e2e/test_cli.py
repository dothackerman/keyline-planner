"""End-to-end tests for the CLI interface.

These tests invoke the CLI via Typer's CliRunner, which runs the CLI
in-process for speed and hermeticity. They verify the full user-facing
contract without requiring network access (using synthetic data where
the pipeline is tested, and testing CLI argument parsing/validation here).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from typer.testing import CliRunner

from keyline_planner.cli.main import app

if TYPE_CHECKING:
    from pathlib import Path

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

    def test_both_inputs_shows_error(self, sample_geojson_file: Path) -> None:
        result = runner.invoke(
            app,
            [
                "contours",
                "--bbox",
                "2600000,1200000,2601000,1201000",
                "--geojson",
                str(sample_geojson_file),
            ],
        )
        assert result.exit_code == 1

    def test_invalid_bbox_format(self) -> None:
        result = runner.invoke(app, ["contours", "--bbox", "not,valid"])
        assert result.exit_code == 1

    def test_invalid_crs(self) -> None:
        result = runner.invoke(
            app,
            [
                "contours",
                "--bbox",
                "2600000,1200000,2601000,1201000",
                "--crs",
                "invalid",
            ],
        )
        assert result.exit_code == 1

    def test_invalid_resolution(self) -> None:
        result = runner.invoke(
            app,
            [
                "contours",
                "--bbox",
                "2600000,1200000,2601000,1201000",
                "--resolution",
                "ultra",
            ],
        )
        assert result.exit_code == 1


class TestCLIGeojsonParsing:
    """Tests for GeoJSON file parsing in the CLI."""

    def test_loads_feature(self, tmp_dir: Path, sample_polygon_lv95: dict[str, Any]) -> None:
        path = tmp_dir / "feature.geojson"
        path.write_text(
            json.dumps(
                {
                    "type": "Feature",
                    "geometry": sample_polygon_lv95,
                    "properties": {},
                }
            )
        )
        # Verify that Feature-wrapped geometries are correctly parsed and processed
        result = runner.invoke(app, ["contours", "--geojson", str(path)])
        assert result.exit_code == 0

    def test_loads_feature_collection(
        self, tmp_dir: Path, sample_polygon_lv95: dict[str, Any]
    ) -> None:
        path = tmp_dir / "collection.geojson"
        path.write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": sample_polygon_lv95,
                            "properties": {},
                        }
                    ],
                }
            )
        )
        # Verify that FeatureCollection-wrapped geometries are correctly parsed and processed
        result = runner.invoke(app, ["contours", "--geojson", str(path)])
        assert result.exit_code == 0

    def test_loads_raw_geometry(self, tmp_dir: Path, sample_polygon_lv95: dict[str, Any]) -> None:
        path = tmp_dir / "raw.geojson"
        path.write_text(json.dumps(sample_polygon_lv95))
        # Verify that raw geometry (without Feature/FeatureCollection wrapper) is correctly parsed and processed
        result = runner.invoke(app, ["contours", "--geojson", str(path)])
        assert result.exit_code == 0

    def test_invalid_json_shows_error(self, tmp_dir: Path) -> None:
        path = tmp_dir / "bad.geojson"
        path.write_text("not json {{{")
        result = runner.invoke(app, ["contours", "--geojson", str(path)])
        assert result.exit_code == 1
