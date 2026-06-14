"""Dash のレイアウトと index HTML を生成する。"""

from __future__ import annotations

from dash import dash_table, dcc, html

from directory_storage_analyzer.constants import APP_TITLE
from directory_storage_analyzer.tables import file_table_columns

INDEX_STRING = """
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


def create_layout(initial_target_path: str) -> html.Div:
    """Dash アプリの画面構造を作成する。

    Args:
        initial_target_path: 対象パス入力欄の初期値。

    Returns:
        Dash の root layout。
    """

    return html.Div(
        [
            dcc.Store(id="analysis-store"),
            dcc.Store(id="click-filter-store", data={"subdirectory": None, "extension": None}),
            html.Header(
                [
                    html.H1(APP_TITLE),
                    html.P("ディレクトリ配下の容量分布を、場所・拡張子・個別ファイルの順に可視化します。"),
                ],
                className="header",
            ),
            html.Section(
                [
                    dcc.Input(
                        id="target-path",
                        type="text",
                        value=initial_target_path,
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
            _make_file_table_section("容量上位ファイル", "top-files-table", page_size=10, filter_action=None),
            _make_file_table_section("全ファイル一覧", "all-files-table", page_size=25, filter_action="native"),
        ],
        className="page",
    )


def _make_file_table_section(
    title: str,
    table_id: str,
    page_size: int,
    filter_action: str | None,
) -> html.Section:
    """共通スタイルを保った DataTable セクションを作成する。"""

    table_kwargs = {
        "id": table_id,
        "columns": file_table_columns(),
        "data": [],
        "page_size": page_size,
        "sort_action": "native",
        "style_table": {"overflowX": "auto"},
        "style_cell": {
            "fontFamily": "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
            "fontSize": "14px",
            "padding": "8px",
            "textAlign": "left",
            "whiteSpace": "normal",
            "height": "auto",
        },
        "style_header": {
            "fontWeight": "700",
            "backgroundColor": "#f4f6f8",
        },
    }
    if filter_action is not None:
        table_kwargs["filter_action"] = filter_action

    return html.Section(
        [
            html.H2(title),
            dash_table.DataTable(**table_kwargs),
        ],
        className="section",
    )
