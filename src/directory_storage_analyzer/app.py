"""Dash アプリケーションの生成処理を提供する。"""

from __future__ import annotations

from dash import Dash

from directory_storage_analyzer.cache import AnalysisCache
from directory_storage_analyzer.callbacks import register_callbacks
from directory_storage_analyzer.config import AppSettings
from directory_storage_analyzer.constants import APP_TITLE
from directory_storage_analyzer.layout import INDEX_STRING, create_layout


def create_dash_app(settings: AppSettings) -> Dash:
    """設定に基づいて Dash アプリを生成する。

    Args:
        settings: CLI と環境変数から解決済みの起動設定。

    Returns:
        callback 登録と layout 設定を終えた Dash アプリ。
    """

    app = Dash(__name__)
    app.title = APP_TITLE
    app.layout = create_layout(settings.target_path)
    app.index_string = INDEX_STRING
    register_callbacks(app, AnalysisCache(max_entries=settings.cache_size))
    return app
