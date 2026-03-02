"""Optional live-network smoke test for CLI contour generation."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from keyline_planner.cli.main import app

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.e2e, pytest.mark.network]

runner = CliRunner()


@pytest.mark.skipif(
    os.getenv("KEYLINE_RUN_NETWORK_SMOKE") != "1",
    reason="Set KEYLINE_RUN_NETWORK_SMOKE=1 to run live network smoke tests.",
)
def test_contours_network_smoke(
    sample_bbox_lv95: tuple[float, float, float, float],
    tmp_dir: Path,
) -> None:
    """Run a minimal live STAC+GDAL smoke test when explicitly enabled."""
    output_dir = tmp_dir / "network_smoke_output"
    bbox_arg = ",".join(str(v) for v in sample_bbox_lv95)

    result = runner.invoke(
        app,
        [
            "contours",
            "--bbox",
            bbox_arg,
            "--output",
            str(output_dir),
            "--no-dem",
        ],
    )
    assert result.exit_code == 0
    assert (output_dir / "contours.geojson").exists()
    assert (output_dir / "manifest.json").exists()
