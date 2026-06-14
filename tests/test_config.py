from __future__ import annotations

import os

import pytest

from directory_storage_analyzer.config import load_settings


def test_load_settings_uses_environment_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("DIRECTORY_STORAGE_ANALYZER_HOST", "0.0.0.0")
    monkeypatch.setenv("DIRECTORY_STORAGE_ANALYZER_PORT", "9000")
    monkeypatch.setenv("DIRECTORY_STORAGE_ANALYZER_DEBUG", "true")
    monkeypatch.setenv("DIRECTORY_STORAGE_ANALYZER_CACHE_SIZE", "5")

    settings = load_settings(target_path=str(tmp_path))

    assert settings.target_path == os.path.abspath(str(tmp_path))
    assert settings.host == "0.0.0.0"
    assert settings.port == 9000
    assert settings.debug is True
    assert settings.cache_size == 5


def test_load_settings_cli_values_override_environment(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("DIRECTORY_STORAGE_ANALYZER_HOST", "0.0.0.0")
    monkeypatch.setenv("DIRECTORY_STORAGE_ANALYZER_PORT", "9000")
    monkeypatch.setenv("DIRECTORY_STORAGE_ANALYZER_DEBUG", "true")
    monkeypatch.setenv("DIRECTORY_STORAGE_ANALYZER_CACHE_SIZE", "5")

    settings = load_settings(
        target_path=str(tmp_path),
        host="127.0.0.1",
        port=8051,
        debug=False,
        cache_size=2,
    )

    assert settings.host == "127.0.0.1"
    assert settings.port == 8051
    assert settings.debug is False
    assert settings.cache_size == 2


def test_load_settings_rejects_invalid_port(tmp_path) -> None:
    with pytest.raises(ValueError):
        load_settings(target_path=str(tmp_path), port=70000)
