from __future__ import annotations

import pytest

from directory_storage_analyzer.analysis import (
    analyze_directory_storage,
    build_cumulative_directory_nodes,
    bytes_to_human,
    display_extension,
    display_subdirectory,
    normalize_relative_path,
)


def test_display_helpers_convert_internal_values() -> None:
    assert bytes_to_human(0) == "0 B"
    assert bytes_to_human(1536) == "1.5 KB"
    assert normalize_relative_path("nested\\file.txt") == "nested/file.txt"
    assert display_subdirectory(".") == "直下"
    assert display_subdirectory("logs") == "logs"
    assert display_extension("") == "拡張子なし"
    assert display_extension(".txt") == ".txt"


def test_bytes_to_human_rejects_negative_value() -> None:
    with pytest.raises(ValueError):
        bytes_to_human(-1)


def test_analyze_directory_storage_returns_empty_result_for_empty_directory(tmp_path) -> None:
    result = analyze_directory_storage(str(tmp_path))

    assert result.summary is None
    assert result.df_files is None
    assert result.skipped_files == []


def test_analyze_directory_storage_summarizes_files_and_extensions(tmp_path) -> None:
    (tmp_path / "root.txt").write_bytes(b"a" * 10)
    (tmp_path / "README").write_bytes(b"b" * 5)
    nested = tmp_path / "logs"
    nested.mkdir()
    (nested / "app.log").write_bytes(b"c" * 20)

    result = analyze_directory_storage(str(tmp_path))

    assert result.summary is not None
    assert result.df_files is not None
    assert result.ext_stats is not None
    assert result.subdir_stats is not None
    assert result.directory_nodes is not None
    assert result.summary["Total Files"] == 3
    assert result.summary["Total Size Bytes"] == 35
    assert set(result.df_files["Extension"]) == {".txt", "", ".log"}
    assert set(result.df_files["Subdirectory"]) == {".", "logs"}


def test_build_cumulative_directory_nodes_accumulates_parent_sizes(tmp_path) -> None:
    (tmp_path / "root.bin").write_bytes(b"a" * 10)
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    (nested / "deep.bin").write_bytes(b"b" * 20)
    result = analyze_directory_storage(str(tmp_path))

    nodes = build_cumulative_directory_nodes(result.df_files)
    root = nodes.loc[nodes["id"] == "root"].iloc[0]
    dir_a = nodes.loc[nodes["id"] == "dir:a"].iloc[0]
    dir_b = nodes.loc[nodes["id"] == "dir:a/b"].iloc[0]

    assert root["Size_Bytes"] == 30
    assert dir_a["Size_Bytes"] == 20
    assert dir_b["parent"] == "dir:a"
