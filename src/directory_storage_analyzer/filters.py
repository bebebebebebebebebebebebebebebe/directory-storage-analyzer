"""Dash のクリック状態とファイル表フィルタを扱う。"""

from __future__ import annotations

from typing import Any

import pandas as pd
from dash import html

from directory_storage_analyzer.analysis import display_extension, display_subdirectory


def extract_clicked_subdirectory(click_data: dict[str, Any] | None) -> str | None:
    """ツリーマップの clickData から選択されたサブディレクトリを抽出する。

    Args:
        click_data: Dash Graph が渡すクリックイベントデータ。

    Returns:
        選択された相対ディレクトリ。root または無効な入力では `None`。
    """

    if not click_data:
        return None

    points = click_data.get("points", [])
    if not points:
        return None

    customdata = points[0].get("customdata")
    if not customdata:
        return None

    kind = customdata[0]
    path = customdata[1]

    if kind == "root":
        return None

    if path == "":
        return "."

    return str(path)


def extract_clicked_extension(click_data: dict[str, Any] | None) -> str | None:
    """拡張子グラフの clickData から選択された拡張子を抽出する。

    Args:
        click_data: Dash Graph が渡すクリックイベントデータ。

    Returns:
        選択された拡張子。無効な入力では `None`。
    """

    if not click_data:
        return None

    points = click_data.get("points", [])
    if not points:
        return None

    customdata = points[0].get("customdata")
    if not customdata:
        return None

    extension = customdata[0]
    return str(extension)


def is_under_directory(file_subdir: str, selected_subdir: str) -> bool:
    """選択ディレクトリ配下にファイルのサブディレクトリが含まれるか判定する。

    Args:
        file_subdir: ファイルが直接存在するサブディレクトリ。
        selected_subdir: フィルタとして選択されたサブディレクトリ。

    Returns:
        選択範囲に含まれる場合は `True`。
    """

    if selected_subdir == ".":
        return file_subdir == "."

    return file_subdir == selected_subdir or file_subdir.startswith(f"{selected_subdir}/")


def apply_file_filters(
    df_files: pd.DataFrame,
    selected_subdirectories: list[str] | None,
    selected_extensions: list[str] | None,
    min_size_mb: float | None,
    filename_query: str | None,
    clicked_subdirectory: str | None,
    clicked_extension: str | None,
) -> pd.DataFrame:
    """ファイル一覧へ UI で指定された複数条件のフィルタを適用する。

    Args:
        df_files: 分析済みの個別ファイル一覧。
        selected_subdirectories: Dropdown で選択されたサブディレクトリ群。
        selected_extensions: Dropdown で選択された拡張子群。
        min_size_mb: 最小サイズ MB。
        filename_query: ファイル名またはパスの検索語。
        clicked_subdirectory: ツリーマップクリックで選択されたサブディレクトリ。
        clicked_extension: 拡張子グラフクリックで選択された拡張子。

    Returns:
        サイズ降順に並べたフィルタ済み DataFrame。
    """

    mask = pd.Series(True, index=df_files.index)

    if selected_subdirectories:
        mask &= df_files["Subdirectory"].map(
            lambda value: any(is_under_directory(str(value), selected) for selected in selected_subdirectories)
        )

    if selected_extensions:
        mask &= df_files["Extension"].isin(selected_extensions)

    if min_size_mb is not None:
        mask &= df_files["Size_MB"] >= float(min_size_mb)

    if filename_query:
        query = filename_query.strip()
        if query:
            mask &= df_files["File"].str.contains(query, case=False, regex=False) | df_files["Path"].str.contains(
                query, case=False, regex=False
            )

    if clicked_subdirectory:
        mask &= df_files["Subdirectory"].map(lambda value: is_under_directory(str(value), clicked_subdirectory))

    if clicked_extension is not None:
        mask &= df_files["Extension"] == clicked_extension

    return df_files.loc[mask].sort_values("Size_Bytes", ascending=False)


def make_active_filter_message(
    clicked_subdirectory: str | None,
    clicked_extension: str | None,
    selected_subdirectories: list[str] | None,
    selected_extensions: list[str] | None,
    min_size_mb: float | None,
    filename_query: str | None,
) -> html.Div:
    """現在有効なフィルタ条件を表示する Dash HTML を作成する。

    Args:
        clicked_subdirectory: ツリーマップで選択されたサブディレクトリ。
        clicked_extension: 拡張子グラフで選択された拡張子。
        selected_subdirectories: Dropdown で選択されたサブディレクトリ群。
        selected_extensions: Dropdown で選択された拡張子群。
        min_size_mb: 最小サイズ MB。
        filename_query: ファイル名またはパスの検索語。

    Returns:
        フィルタ状態を示す Dash HTML。
    """

    parts: list[str] = []

    if clicked_subdirectory:
        parts.append(f"ツリーマップ選択: {display_subdirectory(clicked_subdirectory)}")

    if clicked_extension is not None:
        parts.append(f"グラフ選択: {display_extension(clicked_extension)}")

    if selected_subdirectories:
        labels = ", ".join(display_subdirectory(value) for value in selected_subdirectories)
        parts.append(f"ディレクトリフィルタ: {labels}")

    if selected_extensions:
        labels = ", ".join(display_extension(value) for value in selected_extensions)
        parts.append(f"拡張子フィルタ: {labels}")

    if min_size_mb is not None:
        parts.append(f"最小サイズ: {min_size_mb:g} MB")

    if filename_query:
        query = filename_query.strip()
        if query:
            parts.append(f"検索語: {query}")

    if not parts:
        return html.Div("有効なフィルタ: なし", className="filter-message")

    return html.Div("有効なフィルタ: " + " / ".join(parts), className="filter-message")
