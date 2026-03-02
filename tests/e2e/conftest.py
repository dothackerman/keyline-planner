"""Shared fixtures for end-to-end CLI tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from keyline_planner.engine.models import ContourParams, ProcessingResult

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def mock_processing_result(tmp_dir: Path) -> ProcessingResult:
    """Return a deterministic ProcessingResult for CLI tests."""
    output_dir = tmp_dir / "mock_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    contours_path = output_dir / "contours.gpkg"
    contours_path.write_text("mock gpkg")

    dem_path = output_dir / "dem_clip.tif"
    dem_path.write_text("mock dem")

    return ProcessingResult(
        contours_path=contours_path,
        clipped_dem_path=dem_path,
        contour_count=12,
        elevation_range=(450.0, 780.0),
        aoi_hash="deadbeefcafebabe",
        params=ContourParams(),
        contours_gpkg_path=contours_path,
        tile_ids=["tile_001", "tile_002"],
    )


@pytest.fixture
def mock_run_contour_pipeline_success(
    monkeypatch: pytest.MonkeyPatch,
    mock_processing_result: ProcessingResult,
) -> list[dict[str, Any]]:
    """Patch the CLI pipeline call to avoid network and disk-heavy processing."""
    calls: list[dict[str, Any]] = []

    def _mock_run_contour_pipeline(**kwargs: Any) -> ProcessingResult:
        calls.append(kwargs)
        return mock_processing_result

    monkeypatch.setattr(
        "keyline_planner.cli.main.run_contour_pipeline",
        _mock_run_contour_pipeline,
    )
    return calls
