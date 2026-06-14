from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from dash.development.base_component import Component

from directory_storage_analyzer.app import create_dash_app
from directory_storage_analyzer.config import AppSettings


def test_create_dash_app_includes_expected_layout_ids(tmp_path) -> None:
    app = create_dash_app(AppSettings(target_path=str(tmp_path)))

    found_ids = {component_id for component_id in _iter_component_ids(app.layout) if component_id is not None}

    assert {
        "analysis-store",
        "click-filter-store",
        "target-path",
        "analyze-button",
        "directory-treemap",
        "extension-size-bar",
        "extension-count-bar",
        "top-files-table",
        "all-files-table",
    }.issubset(found_ids)


def _iter_component_ids(component: Any) -> Iterator[str | None]:
    """Dash component tree から id を再帰的に列挙する。"""

    if not isinstance(component, Component):
        return

    yield getattr(component, "id", None)
    children = getattr(component, "children", None)
    if isinstance(children, list):
        for child in children:
            yield from _iter_component_ids(child)
    elif children is not None:
        yield from _iter_component_ids(children)
