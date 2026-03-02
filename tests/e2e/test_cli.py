"""End-to-end tests for the CLI interface.

These tests execute the Typer CLI through CliRunner and validate user-facing
behaviour. The pipeline call is mocked in default E2E tests so the suite stays
deterministic and offline.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from typer.testing import CliRunner

from keyline_planner.cli.main import app
from keyline_planner.engine.models import CRS, Resolution

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.e2e

runner = CliRunner()


class TestCLIBasics:
    """Tests for basic CLI command behaviour."""

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


class TestCLIValidation:
    """Tests for CLI input validation."""

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


class TestCLISuccessPaths:
    """Tests for successful CLI invocations with mocked pipeline execution."""

    def test_bbox_invokes_pipeline_with_parsed_values(
        self,
        mock_run_contour_pipeline_success: list[dict[str, Any]],
        mock_processing_result: Any,
    ) -> None:
        result = runner.invoke(
            app,
            ["contours", "--bbox", "2600000,1200000,2601000,1201000"],
        )

        assert result.exit_code == 0
        assert "Contour Generation Results" in result.output
        assert str(mock_processing_result.contours_path) in result.output

        assert len(mock_run_contour_pipeline_success) == 1
        kwargs = mock_run_contour_pipeline_success[0]
        assert kwargs["bbox"] == (2600000.0, 1200000.0, 2601000.0, 1201000.0)
        assert kwargs["geojson"] is None
        assert kwargs["crs"] == CRS.LV95
        assert kwargs["resolution"] == Resolution.STANDARD
        assert kwargs["interval"] == 1.0
        assert kwargs["simplify_tolerance"] == 0.0
        assert kwargs["save_clipped_dem"] is True

    def test_passes_through_cli_options(
        self,
        tmp_dir: Path,
        mock_run_contour_pipeline_success: list[dict[str, Any]],
    ) -> None:
        output_dir = tmp_dir / "custom_output"
        cache_dir = tmp_dir / "custom_cache"

        result = runner.invoke(
            app,
            [
                "contours",
                "--bbox",
                "7.44,46.94,7.45,46.95",
                "--crs",
                "wgs84",
                "--interval",
                "2.5",
                "--resolution",
                "high",
                "--simplify",
                "1.2",
                "--output",
                str(output_dir),
                "--cache",
                str(cache_dir),
                "--no-dem",
            ],
        )

        assert result.exit_code == 0
        assert len(mock_run_contour_pipeline_success) == 1
        kwargs = mock_run_contour_pipeline_success[0]
        assert kwargs["bbox"] == (7.44, 46.94, 7.45, 46.95)
        assert kwargs["crs"] == CRS.WGS84
        assert kwargs["resolution"] == Resolution.HIGH
        assert kwargs["interval"] == 2.5
        assert kwargs["simplify_tolerance"] == 1.2
        assert kwargs["output_dir"] == output_dir
        assert kwargs["cache_root"] == cache_dir
        assert kwargs["save_clipped_dem"] is False


class TestCLIGeojsonParsing:
    """Tests for GeoJSON file parsing in the CLI."""

    def test_loads_feature(
        self,
        tmp_dir: Path,
        sample_polygon_lv95: dict[str, Any],
        mock_run_contour_pipeline_success: list[dict[str, Any]],
    ) -> None:
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

        result = runner.invoke(app, ["contours", "--geojson", str(path)])
        assert result.exit_code == 0

        assert len(mock_run_contour_pipeline_success) == 1
        kwargs = mock_run_contour_pipeline_success[0]
        assert kwargs["geojson"] == sample_polygon_lv95
        assert kwargs["bbox"] is None

    def test_loads_feature_collection(
        self,
        tmp_dir: Path,
        sample_polygon_lv95: dict[str, Any],
        mock_run_contour_pipeline_success: list[dict[str, Any]],
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

        result = runner.invoke(app, ["contours", "--geojson", str(path)])
        assert result.exit_code == 0

        assert len(mock_run_contour_pipeline_success) == 1
        kwargs = mock_run_contour_pipeline_success[0]
        assert kwargs["geojson"] == sample_polygon_lv95
        assert kwargs["bbox"] is None

    def test_loads_raw_geometry(
        self,
        tmp_dir: Path,
        sample_polygon_lv95: dict[str, Any],
        mock_run_contour_pipeline_success: list[dict[str, Any]],
    ) -> None:
        path = tmp_dir / "raw.geojson"
        path.write_text(json.dumps(sample_polygon_lv95))

        result = runner.invoke(app, ["contours", "--geojson", str(path)])
        assert result.exit_code == 0

        assert len(mock_run_contour_pipeline_success) == 1
        kwargs = mock_run_contour_pipeline_success[0]
        assert kwargs["geojson"] == sample_polygon_lv95
        assert kwargs["bbox"] is None

    def test_invalid_json_shows_error(self, tmp_dir: Path) -> None:
        path = tmp_dir / "bad.geojson"
        path.write_text("not json {{{")
        result = runner.invoke(app, ["contours", "--geojson", str(path)])
        assert result.exit_code == 1


class TestCLIErrorHandling:
    """Tests for CLI error reporting behaviour."""

    def test_connection_error_shows_network_hint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise_connection_error(**_: Any) -> Any:
            raise ConnectionError("STAC unavailable")

        monkeypatch.setattr(
            "keyline_planner.cli.main.run_contour_pipeline",
            _raise_connection_error,
        )

        result = runner.invoke(
            app,
            ["contours", "--bbox", "2600000,1200000,2601000,1201000"],
        )
        assert result.exit_code == 1
        assert "Pipeline error:" in result.output
        assert "Verify DNS/network access" in result.output

    def test_generic_error_shows_pipeline_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise_generic_error(**_: Any) -> Any:
            raise RuntimeError("boom")

        monkeypatch.setattr(
            "keyline_planner.cli.main.run_contour_pipeline",
            _raise_generic_error,
        )

        result = runner.invoke(
            app,
            ["contours", "--bbox", "2600000,1200000,2601000,1201000"],
        )
        assert result.exit_code == 1
        assert "Pipeline error:" in result.output
        assert "boom" in result.output

    def test_verbose_error_includes_traceback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise_generic_error(**_: Any) -> Any:
            raise RuntimeError("kaboom")

        monkeypatch.setattr(
            "keyline_planner.cli.main.run_contour_pipeline",
            _raise_generic_error,
        )

        result = runner.invoke(
            app,
            ["--verbose", "contours", "--bbox", "2600000,1200000,2601000,1201000"],
        )
        assert result.exit_code == 1
        assert "Traceback" in result.output
        assert "RuntimeError: kaboom" in result.output
