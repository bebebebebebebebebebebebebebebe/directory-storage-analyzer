"""標準ライブラリだけで分析処理の CPU プロファイルを取得する CLI。"""

from __future__ import annotations

import argparse
import cProfile
import pstats
from collections.abc import Sequence
from pathlib import Path

from directory_storage_analyzer.analysis import analyze_directory_storage


def main(argv: Sequence[str] | None = None) -> None:
    """`directory-storage-analyzer-profile` コマンドのエントリポイント。

    Args:
        argv: テスト用に差し替え可能な引数列。`None` の場合は `sys.argv` を使う。
    """

    parser = _build_parser()
    args = parser.parse_args(argv)
    run_profile(target_path=args.target_path, output_path=args.output, limit=args.limit)


def run_profile(target_path: str, output_path: str, limit: int) -> None:
    """分析処理を cProfile で計測し、上位関数を標準出力へ表示する。

    Args:
        target_path: 計測対象のディレクトリ。
        output_path: `.prof` ファイルの保存先。
        limit: 標準出力に表示する関数数。
    """

    profiler = cProfile.Profile()
    profiler.enable()
    analyze_directory_storage(target_path)
    profiler.disable()

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    profiler.dump_stats(output)

    stats = pstats.Stats(profiler)
    stats.sort_stats(pstats.SortKey.CUMULATIVE)
    stats.print_stats(limit)
    print(f"\nProfile saved to: {output}")


def _build_parser() -> argparse.ArgumentParser:
    """profile CLI 引数定義を作成する。"""

    parser = argparse.ArgumentParser(
        prog="directory-storage-analyzer-profile",
        description="Profile directory storage analysis with cProfile.",
    )
    parser.add_argument("target_path", help="CPU プロファイルを取得する分析対象ディレクトリ。")
    parser.add_argument("--output", default="profile.prof", help="cProfile stats の保存先。")
    parser.add_argument("--limit", type=int, default=30, help="標準出力に表示する上位関数数。")
    return parser
