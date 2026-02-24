"""Core engine — deterministic geoprocessing pipeline.

This package contains the processing engine (Layer 1) for keyline-planner.
All modules here are pure computational units with explicit inputs and outputs.
No orchestration, no CLI concerns, no agent logic.

Sub-modules:
    geometry   — AOI validation, normalisation, CRS transformation
    tiles      — STAC-based tile discovery and download management
    cache      — Content-addressed local tile & artifact caching
    raster     — DEM mosaic, clip, resample operations
    contours   — Contour line extraction and formatting
    models     — Shared data models / value objects
"""
