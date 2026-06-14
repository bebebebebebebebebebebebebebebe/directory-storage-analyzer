"""Dash callback をアプリへ登録する。"""

from __future__ import annotations

import os
from typing import Any

from dash import Dash, Input, Output, State, ctx, no_update

from directory_storage_analyzer.analysis import analyze_directory_storage
from directory_storage_analyzer.cache import AnalysisCache
from directory_storage_analyzer.charts import (
    make_directory_treemap,
    make_empty_figure,
    make_extension_count_bar,
    make_extension_size_bar,
    make_kpi_cards,
)
from directory_storage_analyzer.filters import (
    apply_file_filters,
    extract_clicked_extension,
    extract_clicked_subdirectory,
    make_active_filter_message,
)
from directory_storage_analyzer.tables import table_records

CACHE_MISS_MESSAGE = "分析結果が見つかりません。再実行してください。"


def register_callbacks(app: Dash, cache: AnalysisCache) -> None:
    """Dash アプリにストレージ分析用 callback を登録する。

    Args:
        app: callback を登録する Dash アプリ。
        cache: 分析結果を保持するサーバー側キャッシュ。
    """

    @app.callback(
        Output("analysis-store", "data"),
        Output("status-message", "children"),
        Input("analyze-button", "n_clicks"),
        State("target-path", "value"),
    )
    def run_analysis(n_clicks: int, target_path: str) -> tuple[dict[str, Any] | None, str]:
        """分析ボタン押下時にディレクトリを走査し、軽量な参照情報を Store に保存する。"""

        if n_clicks == 0:
            return None, "分析対象ディレクトリを指定して「分析を実行」を押してください。"

        try:
            result = analyze_directory_storage(target_path)

            if result.df_files is None:
                skipped_count = len(result.skipped_files)
                return (
                    {
                        "empty": True,
                        "target_path": os.path.abspath(os.path.expanduser(target_path)),
                        "skipped_files": result.skipped_files,
                    },
                    f"分析対象のファイルが見つかりませんでした。読み取り不能ファイル数: {skipped_count:,}",
                )

            analysis_id = cache.put(result)
            payload = {
                "empty": False,
                "analysis_id": analysis_id,
                "summary": result.summary,
                "skipped_files": result.skipped_files,
            }

            return (
                payload,
                (
                    f"分析完了: {result.summary['Total Files']:,} files / "
                    f"{result.summary['Total Size Display']} / "
                    f"読み取り不能 {result.summary['Skipped Files']:,} files"
                ),
            )
        except Exception as exc:  # noqa: BLE001
            return None, f"分析に失敗しました: {exc}"

    @app.callback(
        Output("subdir-filter", "options"),
        Output("extension-filter", "options"),
        Input("analysis-store", "data"),
    )
    def update_filter_options(data: dict[str, Any] | None) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        """保存済み分析結果からサブディレクトリと拡張子の選択肢を更新する。"""

        result = _get_cached_result(cache, data)
        if result is None or result.df_files is None:
            return [], []

        df_files = result.df_files
        subdir_options = (
            df_files[["Subdirectory", "Subdirectory_Display"]]
            .drop_duplicates()
            .sort_values("Subdirectory_Display")
            .to_dict("records")
        )
        extension_options = (
            df_files[["Extension", "Extension_Display"]]
            .drop_duplicates()
            .sort_values("Extension_Display")
            .to_dict("records")
        )

        return (
            [{"label": row["Subdirectory_Display"], "value": row["Subdirectory"]} for row in subdir_options],
            [{"label": row["Extension_Display"], "value": row["Extension"]} for row in extension_options],
        )

    @app.callback(
        Output("click-filter-store", "data"),
        Input("directory-treemap", "clickData"),
        Input("extension-size-bar", "clickData"),
        Input("extension-count-bar", "clickData"),
        Input("clear-click-filter-button", "n_clicks"),
        prevent_initial_call=True,
    )
    def update_click_filter(
        treemap_click_data: dict[str, Any] | None,
        extension_size_click_data: dict[str, Any] | None,
        extension_count_click_data: dict[str, Any] | None,
        clear_clicks: int,
    ) -> dict[str, str | None] | Any:
        """グラフクリックまたは解除ボタンから現在のクリックフィルタを更新する。"""

        triggered_id = ctx.triggered_id

        if triggered_id == "clear-click-filter-button":
            return {"subdirectory": None, "extension": None}

        if triggered_id == "directory-treemap":
            selected_subdirectory = extract_clicked_subdirectory(treemap_click_data)
            return {
                "subdirectory": selected_subdirectory,
                "extension": None,
            }

        if triggered_id == "extension-size-bar":
            selected_extension = extract_clicked_extension(extension_size_click_data)
            return {
                "subdirectory": None,
                "extension": selected_extension,
            }

        if triggered_id == "extension-count-bar":
            selected_extension = extract_clicked_extension(extension_count_click_data)
            return {
                "subdirectory": None,
                "extension": selected_extension,
            }

        return no_update

    @app.callback(
        Output("kpi-section", "children"),
        Output("directory-treemap", "figure"),
        Output("extension-size-bar", "figure"),
        Output("extension-count-bar", "figure"),
        Input("analysis-store", "data"),
    )
    def render_static_dashboard(data: dict[str, Any] | None) -> tuple[Any, Any, Any, Any]:
        """分析完了後に再計算頻度の低い KPI とグラフを描画する。"""

        if not data:
            empty = make_empty_figure("分析結果がありません。")
            return "", empty, empty, empty

        if data.get("empty"):
            empty = make_empty_figure("分析対象のファイルが見つかりませんでした。")
            return "", empty, empty, empty

        result = _get_cached_result(cache, data)
        if result is None or result.df_files is None:
            empty = make_empty_figure(CACHE_MISS_MESSAGE)
            return "", empty, empty, empty

        return (
            make_kpi_cards(result.summary, result.directory_nodes, result.ext_stats),
            make_directory_treemap(result.directory_nodes),
            make_extension_size_bar(result.ext_stats),
            make_extension_count_bar(result.ext_stats),
        )

    @app.callback(
        Output("top-files-table", "data"),
        Output("all-files-table", "data"),
        Output("active-filter-message", "children"),
        Input("analysis-store", "data"),
        Input("subdir-filter", "value"),
        Input("extension-filter", "value"),
        Input("min-size-filter", "value"),
        Input("filename-filter", "value"),
        Input("click-filter-store", "data"),
    )
    def render_file_tables(
        data: dict[str, Any] | None,
        selected_subdirectories: list[str] | None,
        selected_extensions: list[str] | None,
        min_size_mb: float | None,
        filename_query: str | None,
        click_filter: dict[str, Any] | None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Any]:
        """フィルタ変更に応じてファイルテーブルとフィルタ説明だけを更新する。"""

        if not data or data.get("empty"):
            return [], [], ""

        result = _get_cached_result(cache, data)
        if result is None or result.df_files is None:
            return [], [], CACHE_MISS_MESSAGE

        clicked_subdirectory = None
        clicked_extension = None
        if click_filter:
            clicked_subdirectory = click_filter.get("subdirectory")
            clicked_extension = click_filter.get("extension")

        filtered_files = apply_file_filters(
            df_files=result.df_files,
            selected_subdirectories=selected_subdirectories,
            selected_extensions=selected_extensions,
            min_size_mb=min_size_mb,
            filename_query=filename_query,
            clicked_subdirectory=clicked_subdirectory,
            clicked_extension=clicked_extension,
        )
        active_filter_message = make_active_filter_message(
            clicked_subdirectory=clicked_subdirectory,
            clicked_extension=clicked_extension,
            selected_subdirectories=selected_subdirectories,
            selected_extensions=selected_extensions,
            min_size_mb=min_size_mb,
            filename_query=filename_query,
        )

        return table_records(filtered_files, limit=10), table_records(filtered_files), active_filter_message


def _get_cached_result(cache: AnalysisCache, data: dict[str, Any] | None) -> Any:
    """Store の軽量 payload からサーバー側の分析結果を取り出す。"""

    if not data or data.get("empty"):
        return None
    return cache.get(data.get("analysis_id"))
