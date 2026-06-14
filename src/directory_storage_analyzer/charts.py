"""Plotly figure と KPI 表示部品を生成する。"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import html

from directory_storage_analyzer.analysis import bytes_to_human
from directory_storage_analyzer.constants import ROOT_DISPLAY


def make_empty_figure(message: str) -> go.Figure:
    """結果がない状態を示す空の Plotly figure を作成する。

    Args:
        message: グラフ中央に表示するメッセージ。

    Returns:
        Dash Graph に渡せる figure。
    """

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


def make_directory_treemap(df_nodes: pd.DataFrame) -> go.Figure:
    """ディレクトリ別ストレージ使用量のツリーマップを作成する。

    Args:
        df_nodes: `build_cumulative_directory_nodes` が返す階層ノード。

    Returns:
        Dash Graph に渡せる treemap figure。
    """

    fig = go.Figure(
        go.Treemap(
            ids=df_nodes["id"],
            labels=df_nodes["label"],
            parents=df_nodes["parent"],
            values=df_nodes["Size_MB"],
            branchvalues="total",
            customdata=df_nodes[["Kind", "Path", "Size_Display"]],
            hovertemplate=("<b>%{label}</b><br>容量: %{customdata[2]}<br>パス: %{customdata[1]}<extra></extra>"),
        )
    )
    fig.update_layout(
        title="ディレクトリ別ストレージ使用量",
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        height=520,
    )
    return fig


def make_extension_size_bar(ext_stats: pd.DataFrame, top_n: int = 15) -> go.Figure:
    """拡張子別ストレージ使用量の横棒グラフを作成する。

    Args:
        ext_stats: 拡張子別集計 DataFrame。
        top_n: 表示する上位件数。

    Returns:
        Dash Graph に渡せる bar figure。
    """

    df = ext_stats.head(top_n).sort_values("Total_Size_Bytes", ascending=True)
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
    fig.update_traces(hovertemplate=("<b>%{y}</b><br>容量: %{text}<br>容量（MB）: %{x:.2f}<extra></extra>"))
    fig.update_layout(
        height=420,
        margin={"l": 20, "r": 20, "t": 60, "b": 40},
        showlegend=False,
    )
    return fig


def make_extension_count_bar(ext_stats: pd.DataFrame, top_n: int = 15) -> go.Figure:
    """拡張子別ファイル数の横棒グラフを作成する。

    Args:
        ext_stats: 拡張子別集計 DataFrame。
        top_n: 表示する上位件数。

    Returns:
        Dash Graph に渡せる bar figure。
    """

    df = ext_stats.sort_values("Count", ascending=False).head(top_n).sort_values("Count", ascending=True)
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
    fig.update_traces(hovertemplate="<b>%{y}</b><br>ファイル数: %{x:,}<extra></extra>")
    fig.update_layout(
        height=420,
        margin={"l": 20, "r": 20, "t": 60, "b": 40},
        showlegend=False,
    )
    return fig


def make_kpi_cards(summary: dict[str, Any], directory_nodes: pd.DataFrame, ext_stats: pd.DataFrame) -> html.Div:
    """ダッシュボード上部の KPI カードを作成する。

    Args:
        summary: 全体サマリー。
        directory_nodes: 累積容量を含むディレクトリ階層ノード。
        ext_stats: 拡張子別集計。

    Returns:
        KPI カード群を含む Dash HTML。
    """

    top_directory = directory_nodes.query("Kind == 'directory'").sort_values("Size_Bytes", ascending=False).head(1)

    if top_directory.empty:
        largest_directory_label = ROOT_DISPLAY
        largest_directory_size = summary["Total Size Display"]
    else:
        row = top_directory.iloc[0]
        largest_directory_label = str(row["Path"])
        largest_directory_size = str(row["Size_Display"])

    top_extension = ext_stats.sort_values("Total_Size_Bytes", ascending=False).head(1).iloc[0]
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
