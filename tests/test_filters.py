from __future__ import annotations

from pathlib import Path

from directory_storage_analyzer.analysis import analyze_directory_storage
from directory_storage_analyzer.filters import (
    apply_file_filters,
    extract_clicked_extension,
    extract_clicked_subdirectory,
    is_under_directory,
)


def test_extract_clicked_values_from_plotly_customdata() -> None:
    assert extract_clicked_subdirectory({"points": [{"customdata": ["root", "", "1 B"]}]}) is None
    assert extract_clicked_subdirectory({"points": [{"customdata": ["directory", "logs", "1 B"]}]}) == "logs"
    assert extract_clicked_subdirectory({"points": [{"customdata": ["direct_files", "", "1 B"]}]}) == "."
    assert extract_clicked_extension({"points": [{"customdata": [".log", ".log"]}]}) == ".log"


def test_is_under_directory_matches_descendants_only() -> None:
    assert is_under_directory("logs/app", "logs")
    assert is_under_directory("logs", "logs")
    assert not is_under_directory("logs-old", "logs")
    assert is_under_directory(".", ".")
    assert not is_under_directory("logs", ".")


def test_apply_file_filters_combines_all_conditions(tmp_path: Path) -> None:
    (tmp_path / "root.txt").write_bytes(b"a" * 10)
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "app.log").write_bytes(b"b" * 30)
    (logs / "tiny.log").write_bytes(b"c" * 1)
    result = analyze_directory_storage(str(tmp_path))

    filtered = apply_file_filters(
        df_files=result.df_files,
        selected_subdirectories=["logs"],
        selected_extensions=[".log"],
        min_size_mb=0,
        filename_query="app",
        clicked_subdirectory="logs",
        clicked_extension=".log",
    )

    assert list(filtered["File"]) == ["app.log"]
