"""CLI と環境変数から Dash アプリ起動設定を組み立てる。"""

from __future__ import annotations

import os
from dataclasses import dataclass

ENV_HOST = "DIRECTORY_STORAGE_ANALYZER_HOST"
ENV_PORT = "DIRECTORY_STORAGE_ANALYZER_PORT"
ENV_DEBUG = "DIRECTORY_STORAGE_ANALYZER_DEBUG"
ENV_CACHE_SIZE = "DIRECTORY_STORAGE_ANALYZER_CACHE_SIZE"


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Dash アプリの起動設定を表す。

    Attributes:
        target_path: 画面の対象パス入力欄に入れる初期値。
        host: Dash サーバーの bind host。
        port: Dash サーバーの bind port。
        debug: Dash debug mode を有効にするか。
        cache_size: サーバー側に保持する分析結果の最大件数。
    """

    target_path: str
    host: str = "127.0.0.1"
    port: int = 8050
    debug: bool = False
    cache_size: int = 3


def load_settings(
    target_path: str | None = None,
    host: str | None = None,
    port: int | None = None,
    debug: bool | None = None,
    cache_size: int | None = None,
) -> AppSettings:
    """CLI 引数と環境変数からアプリ設定を読み込む。

    CLI 引数として渡された値を最優先し、未指定の項目は環境変数、
    それも未指定の場合はローカル開発向けの既定値を使う。

    Args:
        target_path: 分析対象パスの初期値。
        host: Dash サーバーの host。
        port: Dash サーバーの port。
        debug: Dash debug mode。
        cache_size: 分析結果 cache の最大件数。

    Returns:
        型変換済みのアプリ設定。

    Raises:
        ValueError: port または cache size が範囲外の場合。
    """

    resolved_target_path = os.path.abspath(os.path.expanduser(target_path or os.getcwd()))
    resolved_host = host or os.environ.get(ENV_HOST, "127.0.0.1")
    resolved_port = port if port is not None else _read_int_env(ENV_PORT, 8050)
    resolved_debug = debug if debug is not None else _read_bool_env(ENV_DEBUG, False)
    resolved_cache_size = cache_size if cache_size is not None else _read_int_env(ENV_CACHE_SIZE, 3)

    if resolved_port < 1 or resolved_port > 65535:
        raise ValueError("port must be between 1 and 65535")

    if resolved_cache_size < 1:
        raise ValueError("cache_size must be greater than or equal to 1")

    return AppSettings(
        target_path=resolved_target_path,
        host=resolved_host,
        port=resolved_port,
        debug=resolved_debug,
        cache_size=resolved_cache_size,
    )


def _read_int_env(name: str, default: int) -> int:
    """環境変数を整数として読み取り、未指定なら既定値を返す。"""

    raw_value = os.environ.get(name)
    if raw_value is None or raw_value == "":
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _read_bool_env(name: str, default: bool) -> bool:
    """環境変数を bool として読み取り、未指定なら既定値を返す。"""

    raw_value = os.environ.get(name)
    if raw_value is None or raw_value == "":
        return default

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"{name} must be a boolean value")
