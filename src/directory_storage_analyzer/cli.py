"""外部コマンドとして Dash アプリを起動する CLI。"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from directory_storage_analyzer.app import create_dash_app
from directory_storage_analyzer.config import load_settings


def main(argv: Sequence[str] | None = None) -> None:
    """`directory-storage-analyzer` コマンドのエントリポイント。

    Args:
        argv: テスト用に差し替え可能な引数列。`None` の場合は `sys.argv` を使う。

    Raises:
        SystemExit: argparse の入力エラー、または Dash サーバー終了時。
    """

    parser = _build_parser()
    args = parser.parse_args(argv)
    settings = load_settings(
        target_path=args.target_path,
        host=args.host,
        port=args.port,
        debug=args.debug,
        cache_size=args.cache_size,
    )
    app = create_dash_app(settings)
    app.run(host=settings.host, port=settings.port, debug=settings.debug)


def _build_parser() -> argparse.ArgumentParser:
    """CLI 引数定義を作成する。"""

    parser = argparse.ArgumentParser(
        prog="directory-storage-analyzer",
        description="Dash dashboard for analyzing directory storage usage.",
    )
    parser.add_argument(
        "target_path",
        nargs="?",
        default=None,
        help="分析対象ディレクトリ。未指定時は現在の作業ディレクトリを使います。",
    )
    parser.add_argument("--host", default=None, help="Dash サーバーの bind host。")
    parser.add_argument("--port", type=int, default=None, help="Dash サーバーの bind port。")
    parser.add_argument("--debug", action="store_true", default=None, help="Dash debug mode を有効にします。")
    parser.add_argument("--cache-size", type=int, default=None, help="サーバー側に保持する分析結果の最大件数。")
    return parser
