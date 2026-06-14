"""ディレクトリ走査とストレージ使用量の集計を提供する。"""

from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from directory_storage_analyzer.constants import NO_EXTENSION_DISPLAY, ROOT_DISPLAY

BYTES_PER_MB = 1024 * 1024
FILE_COLUMNS = [
    "File",
    "Path",
    "Subdirectory",
    "Subdirectory_Display",
    "Size_Bytes",
    "Size_MB",
    "Size_Display",
    "Extension",
    "Extension_Display",
]


@dataclass(slots=True)
class StorageAnalysisResult:
    """ディレクトリ分析の集計結果を保持する。

    Attributes:
        summary: 総容量、ファイル数、最大ファイルなどの全体サマリー。
        ext_stats: 拡張子別の件数・容量集計。
        subdir_stats: ファイルが直接存在するサブディレクトリ単位の容量集計。
        directory_nodes: ツリーマップ用に親ディレクトリへ容量を積み上げたノード一覧。
        df_files: 個別ファイル一覧。
        skipped_files: 権限エラーなどで読み取れなかったパス一覧。
    """

    summary: dict[str, Any] | None
    ext_stats: pd.DataFrame | None
    subdir_stats: pd.DataFrame | None
    directory_nodes: pd.DataFrame | None
    df_files: pd.DataFrame | None
    skipped_files: list[dict[str, str]]


def bytes_to_human(size_bytes: float) -> str:
    """バイト数を人間が読みやすい単位表記へ変換する。

    Args:
        size_bytes: 0 以上のバイト数。

    Returns:
        B、KB、MB、GB、TB、PB のいずれかで丸めた文字列。

    Raises:
        ValueError: `size_bytes` が負数の場合。
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
    """MB 単位の値をバイト数へ変換する。

    Args:
        size_mb: MB 単位の数値。

    Returns:
        バイト単位の数値。
    """

    return float(size_mb) * BYTES_PER_MB


def normalize_relative_path(path_value: str) -> str:
    """OS 依存の区切り文字を UI と集計用に `/` へ正規化する。

    Args:
        path_value: `os.path.relpath` などで得た相対パス。

    Returns:
        `.` はそのまま、その他は区切り文字を `/` に統一した相対パス。
    """

    if path_value == ".":
        return "."
    return path_value.replace("\\", "/")


def display_subdirectory(subdirectory: str) -> str:
    """サブディレクトリの内部表現を画面表示名へ変換する。

    Args:
        subdirectory: `.` または `/` 区切りの相対ディレクトリ。

    Returns:
        直下を表す表示名、または元の相対ディレクトリ。
    """

    if subdirectory == ".":
        return ROOT_DISPLAY
    return subdirectory


def display_extension(extension: str) -> str:
    """拡張子の内部表現を画面表示名へ変換する。

    Args:
        extension: `Path.suffix` 由来の拡張子。拡張子なしは空文字。

    Returns:
        拡張子なしを表す表示名、または元の拡張子。
    """

    if extension == "":
        return NO_EXTENSION_DISPLAY
    return extension


def analyze_directory_storage(target_path: str) -> StorageAnalysisResult:
    """指定されたディレクトリ配下のストレージ使用状況を分析する。

    Args:
        target_path: 分析対象ディレクトリ。`~` と相対パスは解決される。

    Returns:
        ファイル一覧、拡張子別集計、ディレクトリ別集計、UI 用サマリー。

    Raises:
        FileNotFoundError: 対象パスが存在しない場合。
        NotADirectoryError: 対象パスがディレクトリではない場合。
    """

    resolved_path = os.path.abspath(os.path.expanduser(target_path))

    if not os.path.exists(resolved_path):
        raise FileNotFoundError(f"対象パスが存在しません: {resolved_path}")

    if not os.path.isdir(resolved_path):
        raise NotADirectoryError(f"対象パスはディレクトリではありません: {resolved_path}")

    file_rows, skipped_files = _collect_file_rows(resolved_path)

    if not file_rows:
        return StorageAnalysisResult(
            summary=None,
            ext_stats=None,
            subdir_stats=None,
            directory_nodes=None,
            df_files=None,
            skipped_files=skipped_files,
        )

    df_files = pd.DataFrame.from_records(file_rows, columns=FILE_COLUMNS)
    summary = _build_summary(resolved_path, df_files, skipped_files)
    ext_stats = _build_extension_stats(df_files)
    subdir_stats = _build_subdirectory_stats(df_files)
    directory_nodes = build_cumulative_directory_nodes(df_files)

    return StorageAnalysisResult(
        summary=summary,
        ext_stats=ext_stats,
        subdir_stats=subdir_stats,
        directory_nodes=directory_nodes,
        df_files=df_files,
        skipped_files=skipped_files,
    )


def build_cumulative_directory_nodes(df_files: pd.DataFrame) -> pd.DataFrame:
    """ツリーマップ用のディレクトリ階層ノードを作成する。

    親ディレクトリに子孫ファイルの容量を積み上げるため、表示値は
    ユーザーが通常期待する「このディレクトリ配下の総容量」と一致する。

    Args:
        df_files: `analyze_directory_storage` が作成した個別ファイル一覧。

    Returns:
        Plotly treemap に渡せる `id`、`parent`、容量列を持つ DataFrame。
    """

    total_size_bytes = float(df_files["Size_Bytes"].sum())

    nodes: dict[str, dict[str, Any]] = {
        "root": {
            "id": "root",
            "label": "対象ディレクトリ",
            "parent": "",
            "Size_Bytes": total_size_bytes,
            "Size_MB": total_size_bytes / BYTES_PER_MB,
            "Path": "",
            "Kind": "root",
        }
    }
    direct_file_size_by_node: dict[str, float] = defaultdict(float)

    for size_bytes, subdir in df_files[["Size_Bytes", "Subdirectory"]].itertuples(index=False, name=None):
        size_bytes = float(size_bytes)
        parts = [] if str(subdir) == "." else [part for part in str(subdir).split("/") if part]
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
            nodes[node_id]["Size_MB"] = nodes[node_id]["Size_Bytes"] / BYTES_PER_MB
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
            "Size_MB": direct_size_bytes / BYTES_PER_MB,
            "Path": parent_path,
            "Kind": "direct_files",
        }

    df_nodes = pd.DataFrame(nodes.values())
    df_nodes["Size_Display"] = df_nodes["Size_Bytes"].apply(bytes_to_human)
    return df_nodes


def _collect_file_rows(target_path: str) -> tuple[list[tuple[Any, ...]], list[dict[str, str]]]:
    """scandir で再帰走査し、DataFrame 生成前の軽量な行データを集める。"""

    file_rows: list[tuple[Any, ...]] = []
    skipped_files: list[dict[str, str]] = []
    stack = [target_path]

    while stack:
        current_dir = stack.pop()
        try:
            with os.scandir(current_dir) as entries:
                for entry in entries:
                    _collect_entry(target_path, current_dir, entry, stack, file_rows, skipped_files)
        except OSError as exc:
            skipped_files.append(
                {
                    "Path": normalize_relative_path(os.path.relpath(current_dir, target_path)),
                    "Reason": str(exc),
                }
            )

    return file_rows, skipped_files


def _collect_entry(
    target_path: str,
    current_dir: str,
    entry: os.DirEntry[str],
    stack: list[str],
    file_rows: list[tuple[Any, ...]],
    skipped_files: list[dict[str, str]],
) -> None:
    """ディレクトリエントリを、再帰対象・ファイル行・読み取り不能のどれかへ分類する。"""

    try:
        if entry.is_dir(follow_symlinks=False):
            stack.append(entry.path)
            return

        if not entry.is_file():
            return

        stat_result = entry.stat()
    except OSError as exc:
        skipped_files.append(
            {
                "Path": normalize_relative_path(os.path.relpath(entry.path, target_path)),
                "Reason": str(exc),
            }
        )
        return

    size_bytes = stat_result.st_size
    relative_subdir = normalize_relative_path(os.path.relpath(current_dir, target_path))
    relative_path = normalize_relative_path(os.path.relpath(entry.path, target_path))
    extension = Path(entry.name).suffix.lower()

    file_rows.append(
        (
            entry.name,
            relative_path,
            relative_subdir,
            display_subdirectory(relative_subdir),
            size_bytes,
            size_bytes / BYTES_PER_MB,
            bytes_to_human(size_bytes),
            extension,
            display_extension(extension),
        )
    )


def _build_summary(target_path: str, df_files: pd.DataFrame, skipped_files: list[dict[str, str]]) -> dict[str, Any]:
    """全体サマリーを DataFrame から一度だけ計算する。"""

    total_size_bytes = float(df_files["Size_Bytes"].sum())
    largest_file_row = df_files.loc[df_files["Size_Bytes"].idxmax()]

    return {
        "Target Path": target_path,
        "Total Files": int(len(df_files)),
        "Total Size Bytes": total_size_bytes,
        "Total Size MB": total_size_bytes / BYTES_PER_MB,
        "Total Size Display": bytes_to_human(total_size_bytes),
        "Largest File": str(largest_file_row["File"]),
        "Largest File Path": str(largest_file_row["Path"]),
        "Largest File Size Bytes": float(largest_file_row["Size_Bytes"]),
        "Largest File Size Display": str(largest_file_row["Size_Display"]),
        "Skipped Files": int(len(skipped_files)),
    }


def _build_extension_stats(df_files: pd.DataFrame) -> pd.DataFrame:
    """拡張子別の件数・容量・平均容量を集計する。"""

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
    return ext_stats


def _build_subdirectory_stats(df_files: pd.DataFrame) -> pd.DataFrame:
    """直接ファイルが存在するサブディレクトリ単位で容量を集計する。"""

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
    return subdir_stats
