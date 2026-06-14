"""Dash DataTable 向けの列定義と表示レコードを生成する。"""

from __future__ import annotations

from typing import Any

import pandas as pd


def table_records(df: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    """ファイル一覧 DataFrame を Dash DataTable の record 形式へ変換する。

    Args:
        df: 表示対象のファイル一覧。
        limit: 先頭から取得する最大件数。`None` の場合は全件。

    Returns:
        DataTable に渡す record list。
    """

    output = df.head(limit) if limit is not None else df
    output = output[
        [
            "File",
            "Subdirectory_Display",
            "Size_Display",
            "Extension_Display",
            "Path",
            "Size_MB",
            "Size_Bytes",
        ]
    ].copy()

    total_size = float(output["Size_Bytes"].max()) if not output.empty else 1.0
    if total_size <= 0:
        total_size = 1.0

    output["Relative_Size_Pct"] = ((output["Size_Bytes"] / total_size) * 100).round(1)
    output["Size_MB"] = output["Size_MB"].round(3)
    output = output.drop(columns=["Size_Bytes"])
    return output.to_dict("records")


def file_table_columns() -> list[dict[str, Any]]:
    """ファイル一覧テーブルの列定義を返す。

    Returns:
        Dash DataTable の `columns` に渡す列定義。
    """

    return [
        {"name": "File", "id": "File"},
        {"name": "Subdirectory", "id": "Subdirectory_Display"},
        {"name": "Size", "id": "Size_Display"},
        {"name": "Extension", "id": "Extension_Display"},
        {"name": "Path", "id": "Path"},
        {"name": "Size MB", "id": "Size_MB", "type": "numeric"},
        {"name": "Relative %", "id": "Relative_Size_Pct", "type": "numeric"},
    ]
