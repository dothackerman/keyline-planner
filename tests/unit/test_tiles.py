"""Unit tests for engine.tiles — STAC discovery and error handling."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pystac_client.warnings import DoesNotConformTo
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import ReadTimeout

from keyline_planner.engine.geometry import normalise_aoi
from keyline_planner.engine.models import CRS, Resolution
from keyline_planner.engine.tiles import discover_tiles

if TYPE_CHECKING:
    from pytest import MonkeyPatch


class _FakeSearch:
    """Minimal fake STAC search result."""

    def __init__(self, should_raise: bool) -> None:
        self._should_raise = should_raise

    def items(self) -> list[Any]:
        if self._should_raise:
            raise ReadTimeout("timed out")
        return []


class _FakeClient:
    """Minimal fake STAC client."""

    def __init__(self, should_raise_on_items: bool, raise_conformance_once: bool = False) -> None:
        self._should_raise_on_items = should_raise_on_items
        self._raise_conformance_once = raise_conformance_once
        self._conformance_overridden = False

    def search(
        self, collections: list[str], bbox: tuple[float, float, float, float]
    ) -> _FakeSearch:
        assert collections
        assert bbox

        if self._raise_conformance_once and not self._conformance_overridden:
            raise DoesNotConformTo(
                "ITEM_SEARCH", "There is no fallback option available for search."
            )

        return _FakeSearch(should_raise=self._should_raise_on_items)

    def add_conforms_to(self, name: str) -> None:
        assert name == "ITEM_SEARCH"
        self._conformance_overridden = True


class TestDiscoverTiles:
    """Tests for discover_tiles failure behavior."""

    def test_raises_connection_error_when_client_open_fails(
        self, monkeypatch: MonkeyPatch, sample_bbox_lv95: tuple[float, float, float, float]
    ) -> None:
        aoi = normalise_aoi(bbox=sample_bbox_lv95, crs=CRS.LV95)

        def _raise_open(_: str) -> _FakeClient:
            raise RequestsConnectionError("dns failed")

        monkeypatch.setattr("keyline_planner.engine.tiles.Client.open", _raise_open)

        with pytest.raises(ConnectionError, match="Failed to reach STAC API"):
            discover_tiles(aoi=aoi, resolution=Resolution.STANDARD)

    def test_raises_connection_error_when_search_iteration_fails(
        self, monkeypatch: MonkeyPatch, sample_bbox_lv95: tuple[float, float, float, float]
    ) -> None:
        aoi = normalise_aoi(bbox=sample_bbox_lv95, crs=CRS.LV95)

        def _open(_: str) -> _FakeClient:
            return _FakeClient(should_raise_on_items=True)

        monkeypatch.setattr("keyline_planner.engine.tiles.Client.open", _open)

        with pytest.raises(ConnectionError, match="Failed to reach STAC API"):
            discover_tiles(aoi=aoi, resolution=Resolution.STANDARD)

    def test_retries_when_item_search_conformance_missing(
        self, monkeypatch: MonkeyPatch, sample_bbox_lv95: tuple[float, float, float, float]
    ) -> None:
        aoi = normalise_aoi(bbox=sample_bbox_lv95, crs=CRS.LV95)
        fake_client = _FakeClient(should_raise_on_items=False, raise_conformance_once=True)

        def _open(_: str) -> _FakeClient:
            return fake_client

        monkeypatch.setattr("keyline_planner.engine.tiles.Client.open", _open)

        with pytest.raises(ValueError, match="No swissALTI3D tiles found"):
            discover_tiles(aoi=aoi, resolution=Resolution.STANDARD)

        assert fake_client._conformance_overridden is True

    def test_raises_value_error_when_no_tiles_found(
        self, monkeypatch: MonkeyPatch, sample_bbox_lv95: tuple[float, float, float, float]
    ) -> None:
        aoi = normalise_aoi(bbox=sample_bbox_lv95, crs=CRS.LV95)

        def _open(_: str) -> _FakeClient:
            return _FakeClient(should_raise_on_items=False)

        monkeypatch.setattr("keyline_planner.engine.tiles.Client.open", _open)

        with pytest.raises(ValueError, match="No swissALTI3D tiles found"):
            discover_tiles(aoi=aoi, resolution=Resolution.STANDARD)
