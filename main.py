from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dash import Dash, Input, Output, State, ctx, dash_table, dcc, html, no_update


ROOT_DISPLAY = "直下"
NO_EXTENSION_DISPLAY = "拡張子なし"
APP_TITLE = "Storage Usage Report"


@dataclass
class StorageAnalysisResult:
    summary: dict[str, Any] | None
    ext_stats: pd.DataFrame | None
    subdir_stats: pd.DataFrame | None
    df_files: pd.DataFrame | None
    skipped_files: list[dict[str, str]]


def bytes_to_human(size_bytes: float) -> str:
    """
    バイト数を人間が読みやすい表記に変換する。
    """
    if size_bytes < 0:
        raise ValueError("size_bytes must be non-negative")

    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(size_bytes)

    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{size:.0f} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024

    return f"{size:.1f} PB"


def mb_to_bytes(size_mb: float) -> float:
    return float(size_mb) * 1024 * 1024


def normalize_relative_path(path_value: str) -> str:
    """
    OS 依存の区切り文字を UI と集計用に '/' へ正規化する。
    """
    if path_value == ".":
        return "."
    return path_value.replace("\\", "/")


def display_subdirectory(subdirectory: str) -> str:
    if subdirectory == ".":
        return ROOT_DISPLAY
    return subdirectory


def display_extension(extension: str) -> str:
    if extension == "":
        return NO_EXTENSION_DISPLAY
    return extension


def analyze_directory_storage(target_path: str) -> StorageAnalysisResult:
    """
    指定されたディレクトリ配下のストレージ使用状況を分析する。

    戻り値:
        summary:
            全体サマリー。
        ext_stats:
            拡張子別の件数・容量。
        subdir_stats:
            ファイルが直接存在するサブディレクトリ単位の件数・容量。
            ツリーマップ用の累積ディレクトリ容量は別関数で df_files から作成する。
        df_files:
            個別ファイル一覧。
        skipped_files:
            権限エラーなどで読み取れなかったファイル一覧。
    """
    target_path = os.path.abspath(os.path.expanduser(target_path))

    if not os.path.exists(target_path):
        raise FileNotFoundError(f"対象パスが存在しません: {target_path}")

    if not os.path.isdir(target_path):
        raise NotADirectoryError(f"対象パスはディレクトリではありません: {target_path}")

    file_data: list[dict[str, Any]] = []
    skipped_files: list[dict[str, str]] = []

    for root, _, files in os.walk(target_path):
        for file_name in files:
            filepath = os.path.join(root, file_name)

            try:
                size_bytes = os.path.getsize(filepath)
                size_mb = size_bytes / (1024 * 1024)

                relative_subdir = os.path.relpath(root, target_path)
                relative_subdir = normalize_relative_path(relative_subdir)

                extension = os.path.splitext(file_name)[1].lower()

                file_data.append(
                    {
                        "File": file_name,
                        "Path": normalize_relative_path(os.path.relpath(filepath, target_path)),
                        "Subdirectory": relative_subdir,
                        "Subdirectory_Display": display_subdirectory(relative_subdir),
                        "Size_Bytes": size_bytes,
                        "Size_MB": size_mb,
                        "Size_Display": bytes_to_human(size_bytes),
                        "Extension": extension,
                        "Extension_Display": display_extension(extension),
                    }
                )

            except OSError as exc:
                skipped_files.append(
                    {
                        "Path": normalize_relative_path(os.path.relpath(filepath, target_path)),
                        "Reason": str(exc),
                    }
                )
                continue

    if not file_data:
        return StorageAnalysisResult(
            summary=None,
            ext_stats=None,
            subdir_stats=None,
            df_files=None,
            skipped_files=skipped_files,
        )

    df_files = pd.DataFrame(file_data)

    total_size_bytes = float(df_files["Size_Bytes"].sum())
    total_size_mb = float(df_files["Size_MB"].sum())

    largest_file_row = df_files.sort_values("Size_Bytes", ascending=False).iloc[0]

    summary = {
        "Target Path": target_path,
        "Total Files": int(len(df_files)),
        "Total Size Bytes": total_size_bytes,
        "Total Size MB": total_size_mb,
        "Total Size Display": bytes_to_human(total_size_bytes),
        "Largest File": str(largest_file_row["File"]),
        "Largest File Path": str(largest_file_row["Path"]),
        "Largest File Size Bytes": float(largest_file_row["Size_Bytes"]),
        "Largest File Size Display": str(largest_file_row["Size_Display"]),
        "Skipped Files": int(len(skipped_files)),
    }

    ext_stats = (
        df_files.groupby(["Extension", "Extension_Display"], as_index=False)
        .agg(
            Count=("File", "count"),
            Total_Size_Bytes=("Size_Bytes", "sum"),
            Total_Size_MB=("Size_MB", "sum"),
            Average_Size_Bytes=("Size_Bytes", "mean"),
        )
        .sort_values(by="Total_Size_Bytes", ascending=False)
    )

    ext_stats["Total_Size_Display"] = ext_stats["Total_Size_Bytes"].apply(bytes_to_human)
    ext_stats["Average_Size_Display"] = ext_stats["Average_Size_Bytes"].apply(bytes_to_human)

    subdir_stats = (
        df_files.groupby(["Subdirectory", "Subdirectory_Display"], as_index=False)
        .agg(
            Count=("File", "count"),
            Total_Size_Bytes=("Size_Bytes", "sum"),
            Total_Size_MB=("Size_MB", "sum"),
            Average_Size_Bytes=("Size_Bytes", "mean"),
        )
        .sort_values(by="Total_Size_Bytes", ascending=False)
    )

    subdir_stats["Total_Size_Display"] = subdir_stats["Total_Size_Bytes"].apply(bytes_to_human)
    subdir_stats["Average_Size_Display"] = subdir_stats["Average_Size_Bytes"].apply(bytes_to_human)

    return StorageAnalysisResult(
        summary=summary,
        ext_stats=ext_stats,
        subdir_stats=subdir_stats,
        df_files=df_files,
        skipped_files=skipped_files,
    )


def build_cumulative_directory_nodes(df_files: pd.DataFrame) -> pd.DataFrame:
    """
    ツリーマップ用のディレクトリ階層ノードを作成する。

    重要:
        この関数では、親ディレクトリに子孫ファイルの容量を積み上げる。
        そのため、ユーザーが通常期待する「このディレクトリ配下の総容量」と一致する。
    """
    total_size_bytes = float(df_files["Size_Bytes"].sum())

    nodes: dict[str, dict[str, Any]] = {
        "root": {
            "id": "root",
            "label": "対象ディレクトリ",
            "parent": "",
            "Size_Bytes": total_size_bytes,
            "Size_MB": total_size_bytes / (1024 * 1024),
            "Path": "",
            "Kind": "root",
        }
    }

    direct_file_size_by_node: dict[str, float] = defaultdict(float)

    for _, row in df_files.iterrows():
        size_bytes = float(row["Size_Bytes"])
        subdir = str(row["Subdirectory"])

        if subdir == ".":
            parts: list[str] = []
        else:
            parts = [part for part in subdir.split("/") if part]

        parent_id = "root"
        accumulated_parts: list[str] = []

        for part in parts:
            accumulated_parts.append(part)
            current_path = "/".join(accumulated_parts)
            node_id = f"dir:{current_path}"

            if node_id not in nodes:
                nodes[node_id] = {
                    "id": node_id,
                    "label": part,
                    "parent": parent_id,
                    "Size_Bytes": 0.0,
                    "Size_MB": 0.0,
                    "Path": current_path,
                    "Kind": "directory",
                }

            nodes[node_id]["Size_Bytes"] += size_bytes
            nodes[node_id]["Size_MB"] = nodes[node_id]["Size_Bytes"] / (1024 * 1024)

            parent_id = node_id

        direct_file_size_by_node[parent_id] += size_bytes

    for parent_id, direct_size_bytes in direct_file_size_by_node.items():
        if direct_size_bytes <= 0:
            continue

        parent_path = str(nodes[parent_id]["Path"])
        direct_node_id = f"direct:{parent_id}"

        nodes[direct_node_id] = {
            "id": direct_node_id,
            "label": "直下ファイル",
            "parent": parent_id,
            "Size_Bytes": direct_size_bytes,
            "Size_MB": direct_size_bytes / (1024 * 1024),
            "Path": parent_path,
            "Kind": "direct_files",
        }

    df_nodes = pd.DataFrame(nodes.values())
    df_nodes["Size_Display"] = df_nodes["Size_Bytes"].apply(bytes_to_human)

    return df_nodes


def make_empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 16},
    )
    fig.update_layout(
        xaxis={"visible": False},
        yaxis={"visible": False},
        margin={"l": 20, "r": 20, "t": 40, "b": 20},
        height=360,
    )
    return fig


def make_directory_treemap(df_files: pd.DataFrame) -> go.Figure:
    df_nodes = build_cumulative_directory_nodes(df_files)

    fig = go.Figure(
        go.Treemap(
            ids=df_nodes["id"],
            labels=df_nodes["label"],
            parents=df_nodes["parent"],
            values=df_nodes["Size_MB"],
            branchvalues="total",
            customdata=df_nodes[["Kind", "Path", "Size_Display"]],
            hovertemplate=(
                "<b>%{label}</b><br>"
                "容量: %{customdata[2]}<br>"
                "パス: %{customdata[1]}<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title="ディレクトリ別ストレージ使用量",
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        height=520,
    )

    return fig


def make_extension_size_bar(ext_stats: pd.DataFrame, top_n: int = 15) -> go.Figure:
    df = ext_stats.head(top_n).copy()
    df = df.sort_values("Total_Size_Bytes", ascending=True)

    fig = px.bar(
        df,
        x="Total_Size_MB",
        y="Extension_Display",
        orientation="h",
        text="Total_Size_Display",
        custom_data=["Extension", "Extension_Display"],
        labels={
            "Total_Size_MB": "容量（MB）",
            "Extension_Display": "拡張子",
        },
        title="拡張子別ストレージ使用量",
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "容量: %{text}<br>"
            "容量（MB）: %{x:.2f}<extra></extra>"
        )
    )

    fig.update_layout(
        height=420,
        margin={"l": 20, "r": 20, "t": 60, "b": 40},
        showlegend=False,
    )

    return fig


def make_extension_count_bar(ext_stats: pd.DataFrame, top_n: int = 15) -> go.Figure:
    df = ext_stats.sort_values("Count", ascending=False).head(top_n).copy()
    df = df.sort_values("Count", ascending=True)

    fig = px.bar(
        df,
        x="Count",
        y="Extension_Display",
        orientation="h",
        text="Count",
        custom_data=["Extension", "Extension_Display"],
        labels={
            "Count": "ファイル数",
            "Extension_Display": "拡張子",
        },
        title="拡張子別ファイル数",
    )

    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>ファイル数: %{x:,}<extra></extra>"
    )

    fig.update_layout(
        height=420,
        margin={"l": 20, "r": 20, "t": 60, "b": 40},
        showlegend=False,
    )

    return fig


def extract_clicked_subdirectory(click_data: dict[str, Any] | None) -> str | None:
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
    """
    selected_subdir 配下に file_subdir が含まれるかを判定する。
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
    df = df_files.copy()

    if selected_subdirectories:
        df = df[
            df["Subdirectory"].apply(
                lambda value: any(
                    is_under_directory(str(value), selected)
                    for selected in selected_subdirectories
                )
            )
        ]

    if selected_extensions:
        df = df[df["Extension"].isin(selected_extensions)]

    if min_size_mb is not None:
        df = df[df["Size_MB"] >= float(min_size_mb)]

    if filename_query:
        query = filename_query.strip().lower()
        if query:
            df = df[
                df["File"].str.lower().str.contains(query, regex=False)
                | df["Path"].str.lower().str.contains(query, regex=False)
            ]

    if clicked_subdirectory:
        df = df[
            df["Subdirectory"].apply(
                lambda value: is_under_directory(str(value), clicked_subdirectory)
            )
        ]

    if clicked_extension is not None:
        df = df[df["Extension"] == clicked_extension]

    return df.sort_values("Size_Bytes", ascending=False)


def make_kpi_cards(summary: dict[str, Any], df_files: pd.DataFrame) -> html.Div:
    top_directory = (
        build_cumulative_directory_nodes(df_files)
        .query("Kind == 'directory'")
        .sort_values("Size_Bytes", ascending=False)
        .head(1)
    )

    if top_directory.empty:
        largest_directory_label = ROOT_DISPLAY
        largest_directory_size = summary["Total Size Display"]
    else:
        row = top_directory.iloc[0]
        largest_directory_label = str(row["Path"])
        largest_directory_size = str(row["Size_Display"])

    top_extension = (
        df_files.groupby(["Extension", "Extension_Display"], as_index=False)
        .agg(Total_Size_Bytes=("Size_Bytes", "sum"))
        .sort_values("Total_Size_Bytes", ascending=False)
        .head(1)
        .iloc[0]
    )

    top_extension_label = str(top_extension["Extension_Display"])
    top_extension_size = bytes_to_human(float(top_extension["Total_Size_Bytes"]))

    cards = [
        ("総使用量", summary["Total Size Display"], ""),
        ("総ファイル数", f"{summary['Total Files']:,}", "files"),
        ("最大ファイル", summary["Largest File"], summary["Largest File Size Display"]),
        ("最大ディレクトリ", largest_directory_label, largest_directory_size),
        ("最大拡張子", top_extension_label, top_extension_size),
        ("読み取り不能", f"{summary['Skipped Files']:,}", "files"),
    ]

    return html.Div(
        [
            html.Div(
                [
                    html.Div(title, className="kpi-title"),
                    html.Div(value, className="kpi-value"),
                    html.Div(subtitle, className="kpi-subtitle"),
                ],
                className="kpi-card",
            )
            for title, value, subtitle in cards
        ],
        className="kpi-grid",
    )


def make_active_filter_message(
    clicked_subdirectory: str | None,
    clicked_extension: str | None,
    selected_subdirectories: list[str] | None,
    selected_extensions: list[str] | None,
    min_size_mb: float | None,
    filename_query: str | None,
) -> html.Div:
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


def table_records(df: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    if limit is not None:
        df = df.head(limit)

    output = df.copy()

    total_size = float(output["Size_Bytes"].max()) if not output.empty else 1.0
    if total_size <= 0:
        total_size = 1.0

    output["Relative_Size"] = output["Size_Bytes"] / total_size
    output["Relative_Size_Pct"] = (output["Relative_Size"] * 100).round(1)

    columns = [
        "File",
        "Subdirectory_Display",
        "Size_Display",
        "Extension_Display",
        "Path",
        "Size_MB",
        "Relative_Size_Pct",
    ]

    output = output[columns]
    output["Size_MB"] = output["Size_MB"].round(3)

    return output.to_dict("records")


def file_table_columns() -> list[dict[str, Any]]:
    return [
        {"name": "File", "id": "File"},
        {"name": "Subdirectory", "id": "Subdirectory_Display"},
        {"name": "Size", "id": "Size_Display"},
        {"name": "Extension", "id": "Extension_Display"},
        {"name": "Path", "id": "Path"},
        {"name": "Size MB", "id": "Size_MB", "type": "numeric"},
        {"name": "Relative %", "id": "Relative_Size_Pct", "type": "numeric"},
    ]


def create_layout() -> html.Div:
    return html.Div(
        [
            dcc.Store(id="analysis-store"),
            dcc.Store(id="click-filter-store", data={"subdirectory": None, "extension": None}),

            html.Header(
                [
                    html.H1(APP_TITLE),
                    html.P(
                        "ディレクトリ配下の容量分布を、場所・拡張子・個別ファイルの順に可視化します。"
                    ),
                ],
                className="header",
            ),

            html.Section(
                [
                    dcc.Input(
                        id="target-path",
                        type="text",
                        value=os.getcwd(),
                        placeholder="分析対象ディレクトリのパス",
                        className="path-input",
                    ),
                    html.Button("分析を実行", id="analyze-button", n_clicks=0, className="primary-button"),
                ],
                className="path-row",
            ),

            html.Div(id="status-message", className="status-message"),

            html.Section(id="kpi-section", className="section"),

            html.Section(
                [
                    dcc.Graph(id="directory-treemap"),
                    html.Button(
                        "グラフ選択を解除",
                        id="clear-click-filter-button",
                        n_clicks=0,
                        className="secondary-button",
                    ),
                    html.Div(id="active-filter-message"),
                ],
                className="section",
            ),

            html.Section(
                [
                    html.Div(
                        dcc.Graph(id="extension-size-bar"),
                        className="chart-column",
                    ),
                    html.Div(
                        dcc.Graph(id="extension-count-bar"),
                        className="chart-column",
                    ),
                ],
                className="chart-grid",
            ),

            html.Section(
                [
                    html.H2("ファイルフィルタ"),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label("サブディレクトリ"),
                                    dcc.Dropdown(
                                        id="subdir-filter",
                                        multi=True,
                                        placeholder="サブディレクトリで絞り込み",
                                    ),
                                ],
                                className="filter-control",
                            ),
                            html.Div(
                                [
                                    html.Label("拡張子"),
                                    dcc.Dropdown(
                                        id="extension-filter",
                                        multi=True,
                                        placeholder="拡張子で絞り込み",
                                    ),
                                ],
                                className="filter-control",
                            ),
                            html.Div(
                                [
                                    html.Label("最小サイズ MB"),
                                    dcc.Input(
                                        id="min-size-filter",
                                        type="number",
                                        min=0,
                                        step=1,
                                        placeholder="例: 100",
                                        className="number-input",
                                    ),
                                ],
                                className="filter-control",
                            ),
                            html.Div(
                                [
                                    html.Label("ファイル名・パス検索"),
                                    dcc.Input(
                                        id="filename-filter",
                                        type="text",
                                        placeholder="例: .log, backup, video",
                                        className="text-input",
                                    ),
                                ],
                                className="filter-control",
                            ),
                        ],
                        className="filter-grid",
                    ),
                ],
                className="section",
            ),

            html.Section(
                [
                    html.H2("容量上位ファイル"),
                    dash_table.DataTable(
                        id="top-files-table",
                        columns=file_table_columns(),
                        data=[],
                        page_size=10,
                        sort_action="native",
                        style_table={"overflowX": "auto"},
                        style_cell={
                            "fontFamily": "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
                            "fontSize": "14px",
                            "padding": "8px",
                            "textAlign": "left",
                            "whiteSpace": "normal",
                            "height": "auto",
                        },
                        style_header={
                            "fontWeight": "700",
                            "backgroundColor": "#f4f6f8",
                        },
                    ),
                ],
                className="section",
            ),

            html.Section(
                [
                    html.H2("全ファイル一覧"),
                    dash_table.DataTable(
                        id="all-files-table",
                        columns=file_table_columns(),
                        data=[],
                        page_size=25,
                        sort_action="native",
                        filter_action="native",
                        style_table={"overflowX": "auto"},
                        style_cell={
                            "fontFamily": "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
                            "fontSize": "14px",
                            "padding": "8px",
                            "textAlign": "left",
                            "whiteSpace": "normal",
                            "height": "auto",
                        },
                        style_header={
                            "fontWeight": "700",
                            "backgroundColor": "#f4f6f8",
                        },
                    ),
                ],
                className="section",
            ),
        ],
        className="page",
    )


app = Dash(__name__)
app.title = APP_TITLE
app.layout = create_layout()


app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                margin: 0;
                background: #f7f8fa;
                color: #1f2933;
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            }

            .page {
                max-width: 1440px;
                margin: 0 auto;
                padding: 28px;
            }

            .header {
                margin-bottom: 24px;
            }

            .header h1 {
                margin: 0 0 8px 0;
                font-size: 32px;
                letter-spacing: -0.03em;
            }

            .header p {
                margin: 0;
                color: #52606d;
                font-size: 15px;
            }

            .path-row {
                display: grid;
                grid-template-columns: 1fr 140px;
                gap: 12px;
                margin-bottom: 16px;
            }

            .path-input,
            .text-input,
            .number-input {
                width: 100%;
                box-sizing: border-box;
                padding: 10px 12px;
                border: 1px solid #d9e2ec;
                border-radius: 8px;
                font-size: 14px;
                background: white;
            }

            .primary-button,
            .secondary-button {
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 700;
            }

            .primary-button {
                background: #1f2933;
                color: white;
            }

            .secondary-button {
                margin-top: 12px;
                padding: 9px 12px;
                background: #e5e7eb;
                color: #1f2933;
            }

            .status-message {
                margin-bottom: 16px;
                color: #52606d;
            }

            .section {
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 14px;
                padding: 18px;
                margin-bottom: 18px;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            }

            .section h2 {
                margin: 0 0 14px 0;
                font-size: 20px;
                letter-spacing: -0.02em;
            }

            .kpi-grid {
                display: grid;
                grid-template-columns: repeat(6, minmax(0, 1fr));
                gap: 12px;
            }

            .kpi-card {
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 14px;
                padding: 16px;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
                min-height: 96px;
            }

            .kpi-title {
                font-size: 13px;
                color: #66788a;
                margin-bottom: 8px;
            }

            .kpi-value {
                font-size: 20px;
                font-weight: 800;
                overflow-wrap: anywhere;
            }

            .kpi-subtitle {
                font-size: 12px;
                color: #7b8794;
                margin-top: 6px;
                overflow-wrap: anywhere;
            }

            .chart-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 18px;
                margin-bottom: 18px;
            }

            .chart-column {
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 14px;
                padding: 12px;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            }

            .filter-grid {
                display: grid;
                grid-template-columns: 1fr 1fr 180px 1fr;
                gap: 14px;
                align-items: end;
            }

            .filter-control label {
                display: block;
                margin-bottom: 6px;
                font-size: 13px;
                color: #52606d;
                font-weight: 700;
            }

            .filter-message {
                margin-top: 12px;
                color: #52606d;
                font-size: 14px;
            }

            @media (max-width: 1100px) {
                .kpi-grid {
                    grid-template-columns: repeat(3, minmax(0, 1fr));
                }

                .chart-grid {
                    grid-template-columns: 1fr;
                }

                .filter-grid {
                    grid-template-columns: 1fr 1fr;
                }
            }

            @media (max-width: 720px) {
                .page {
                    padding: 16px;
                }

                .path-row {
                    grid-template-columns: 1fr;
                }

                .kpi-grid {
                    grid-template-columns: 1fr;
                }

                .filter-grid {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""


@app.callback(
    Output("analysis-store", "data"),
    Output("status-message", "children"),
    Input("analyze-button", "n_clicks"),
    State("target-path", "value"),
)
def run_analysis(n_clicks: int, target_path: str):
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

        payload = {
            "empty": False,
            "summary": result.summary,
            "ext_stats": result.ext_stats.to_dict("records"),
            "subdir_stats": result.subdir_stats.to_dict("records"),
            "df_files": result.df_files.to_dict("records"),
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

    except Exception as exc:
        return None, f"分析に失敗しました: {exc}"


@app.callback(
    Output("subdir-filter", "options"),
    Output("extension-filter", "options"),
    Input("analysis-store", "data"),
)
def update_filter_options(data: dict[str, Any] | None):
    if not data or data.get("empty"):
        return [], []

    df_files = pd.DataFrame(data["df_files"])

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
        [
            {"label": row["Subdirectory_Display"], "value": row["Subdirectory"]}
            for row in subdir_options
        ],
        [
            {"label": row["Extension_Display"], "value": row["Extension"]}
            for row in extension_options
        ],
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
):
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
def render_dashboard(
    data: dict[str, Any] | None,
    selected_subdirectories: list[str] | None,
    selected_extensions: list[str] | None,
    min_size_mb: float | None,
    filename_query: str | None,
    click_filter: dict[str, Any] | None,
):
    if not data:
        empty = make_empty_figure("分析結果がありません。")
        return "", empty, empty, empty, [], [], ""

    if data.get("empty"):
        empty = make_empty_figure("分析対象のファイルが見つかりませんでした。")
        return "", empty, empty, empty, [], [], ""

    summary = data["summary"]
    df_files = pd.DataFrame(data["df_files"])
    ext_stats = pd.DataFrame(data["ext_stats"])

    clicked_subdirectory = None
    clicked_extension = None

    if click_filter:
        clicked_subdirectory = click_filter.get("subdirectory")
        clicked_extension = click_filter.get("extension")

    filtered_files = apply_file_filters(
        df_files=df_files,
        selected_subdirectories=selected_subdirectories,
        selected_extensions=selected_extensions,
        min_size_mb=min_size_mb,
        filename_query=filename_query,
        clicked_subdirectory=clicked_subdirectory,
        clicked_extension=clicked_extension,
    )

    kpi_cards = make_kpi_cards(summary, df_files)

    treemap_fig = make_directory_treemap(df_files)
    ext_size_fig = make_extension_size_bar(ext_stats)
    ext_count_fig = make_extension_count_bar(ext_stats)

    top_files_data = table_records(filtered_files, limit=10)
    all_files_data = table_records(filtered_files)

    active_filter_message = make_active_filter_message(
        clicked_subdirectory=clicked_subdirectory,
        clicked_extension=clicked_extension,
        selected_subdirectories=selected_subdirectories,
        selected_extensions=selected_extensions,
        min_size_mb=min_size_mb,
        filename_query=filename_query,
    )

    return (
        kpi_cards,
        treemap_fig,
        ext_size_fig,
        ext_count_fig,
        top_files_data,
        all_files_data,
        active_filter_message,
    )

if __name__ == "__main__":
    app.run(debug=True)