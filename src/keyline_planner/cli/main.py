"""Keyline Planner CLI — thin adapter over the core engine.

This is the primary user interface for Milestone 1. It translates
command-line arguments into engine pipeline calls and formats results
for human consumption.

Usage:
    keyline contours --bbox "2600000,1200000,2601000,1201000"
    keyline contours --geojson parcel.geojson --interval 2.0
    keyline contours --geojson parcel.geojson --resolution high
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from keyline_planner import __version__
from keyline_planner.engine.models import CRS, Resolution
from keyline_planner.engine.pipeline import run_contour_pipeline

app = typer.Typer(
    name="keyline",
    help="CLI-first Swiss keyline-design contour generation engine.",
    no_args_is_help=True,
    add_completion=False,
)

console = Console(stderr=True)
output_console = Console()  # stdout for data output


def _setup_logging(verbose: bool) -> None:
    """Configure logging with Rich handler."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"keyline-planner {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", "-V", help="Show version and exit.", callback=version_callback),
    ] = None,
) -> None:
    """Keyline Planner — Swiss contour generation for keyline design."""


@app.command()
def contours(
    bbox: Annotated[
        str | None,
        typer.Option(
            "--bbox",
            "-b",
            help='Bounding box as "xmin,ymin,xmax,ymax" in the specified CRS.',
        ),
    ] = None,
    geojson_file: Annotated[
        Path | None,
        typer.Option(
            "--geojson",
            "-g",
            help="Path to a GeoJSON file containing the AOI polygon.",
            exists=True,
            readable=True,
        ),
    ] = None,
    interval: Annotated[
        float,
        typer.Option("--interval", "-i", help="Contour interval in meters."),
    ] = 1.0,
    resolution: Annotated[
        str,
        typer.Option(
            "--resolution",
            "-r",
            help="DEM resolution: 'standard' (2m) or 'high' (0.5m).",
        ),
    ] = "standard",
    crs: Annotated[
        str,
        typer.Option("--crs", help="Input CRS: 'lv95' or 'wgs84'."),
    ] = "lv95",
    simplify: Annotated[
        float,
        typer.Option("--simplify", "-s", help="Simplification tolerance in CRS units (0=none)."),
    ] = 0.0,
    output_dir: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output directory for results."),
    ] = None,
    cache_dir: Annotated[
        Path | None,
        typer.Option("--cache", help="Cache directory for downloaded tiles."),
    ] = None,
    no_dem: Annotated[
        bool,
        typer.Option("--no-dem", help="Don't save the clipped DEM raster."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose/debug logging."),
    ] = False,
) -> None:
    """Generate contour lines from Swiss elevation data for a given AOI.

    Provide either --bbox or --geojson to define the area of interest.
    Results are written to the output directory as GeoJSON contours,
    an optional clipped DEM, and a provenance manifest.
    """
    _setup_logging(verbose)

    # --- Parse inputs ---
    if bbox is None and geojson_file is None:
        console.print("[red]Error:[/] Provide either --bbox or --geojson", style="bold")
        raise typer.Exit(code=1)

    if bbox is not None and geojson_file is not None:
        console.print("[red]Error:[/] Provide either --bbox or --geojson, not both", style="bold")
        raise typer.Exit(code=1)

    # Parse CRS
    crs_map = {"lv95": CRS.LV95, "wgs84": CRS.WGS84}
    input_crs = crs_map.get(crs.lower())
    if input_crs is None:
        console.print(f"[red]Error:[/] Unknown CRS '{crs}'. Use 'lv95' or 'wgs84'.")
        raise typer.Exit(code=1)

    # Parse resolution
    res_map = {"standard": Resolution.STANDARD, "high": Resolution.HIGH}
    input_resolution = res_map.get(resolution.lower())
    if input_resolution is None:
        console.print(
            f"[red]Error:[/] Unknown resolution '{resolution}'. Use 'standard' or 'high'."
        )
        raise typer.Exit(code=1)

    # Parse bbox or load geojson
    parsed_bbox: tuple[float, float, float, float] | None = None
    parsed_geojson: dict[str, object] | None = None

    if bbox is not None:
        try:
            parts = [float(x.strip()) for x in bbox.split(",")]
            if len(parts) != 4:
                msg = "Expected 4 values"
                raise ValueError(msg)
            parsed_bbox = (parts[0], parts[1], parts[2], parts[3])
        except (ValueError, IndexError) as e:
            console.print(f"[red]Error:[/] Invalid bbox format: {e}")
            raise typer.Exit(code=1) from e

    if geojson_file is not None:
        try:
            data = json.loads(geojson_file.read_text())
            # Support both raw geometry and FeatureCollection
            if data.get("type") == "FeatureCollection":
                features = data.get("features", [])
                if not features:
                    msg = "FeatureCollection has no features"
                    raise ValueError(msg)
                parsed_geojson = features[0]["geometry"]
            elif data.get("type") == "Feature":
                parsed_geojson = data["geometry"]
            else:
                parsed_geojson = data  # Assume raw geometry
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            console.print(f"[red]Error:[/] Failed to parse GeoJSON file: {e}")
            raise typer.Exit(code=1) from e

    # --- Run pipeline ---
    try:
        result = run_contour_pipeline(
            geojson=parsed_geojson,
            bbox=parsed_bbox,
            crs=input_crs,
            interval=interval,
            resolution=input_resolution,
            simplify_tolerance=simplify,
            output_dir=output_dir,
            cache_root=cache_dir,
            save_clipped_dem=not no_dem,
        )
    except Exception as e:
        console.print(f"[red]Pipeline error:[/] {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(code=1) from e

    # --- Display results ---
    table = Table(title="Contour Generation Results", show_header=False, pad_edge=False)
    table.add_column("Key", style="bold cyan")
    table.add_column("Value")
    table.add_row("Contours", str(result.contours_path))
    table.add_row("Count", f"{result.contour_count} contour lines")
    elev_lo, elev_hi = result.elevation_range
    table.add_row("Elevation", f"{elev_lo:.1f} - {elev_hi:.1f} m")
    table.add_row("Interval", f"{interval} m")
    table.add_row("Resolution", f"{input_resolution.value} m")
    table.add_row("AOI Hash", result.aoi_hash)
    table.add_row("Tiles Used", ", ".join(result.tile_ids))
    if result.clipped_dem_path:
        table.add_row("Clipped DEM", str(result.clipped_dem_path))
    table.add_row("Attribution", result.attribution)

    console.print()
    console.print(table)

    # Also print the contours path to stdout (for piping)
    output_console.print(str(result.contours_path))


if __name__ == "__main__":
    app()
