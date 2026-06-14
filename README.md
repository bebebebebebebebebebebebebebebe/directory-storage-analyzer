# directory-storage-analyzer

Dash でディレクトリ配下のストレージ使用状況を可視化する Python アプリケーションです。対象ディレクトリを走査し、容量の大きい場所、拡張子別の容量/件数、個別ファイルの一覧をブラウザ上で確認できます。

Last reviewed: 2026-06-14

## Quick start

このプロジェクトは Python 3.13 を前提にし、依存関係は `uv.lock` で管理しています。

```bash
uv sync
uv run directory-storage-analyzer [target_path]
```

`target_path` を省略した場合は、コマンドを実行した作業ディレクトリが初期表示の分析対象になります。起動後、ブラウザで Dash の表示 URL を開き、対象パスを確認して「分析を実行」を押してください。

開発時に `main.py` から起動する場合は次を使います。

```bash
uv run python main.py
```

## 画面でできること

- 対象ディレクトリのパスを入力し、ボタン操作で分析を実行する。
- KPI で総使用量、総ファイル数、最大ファイル、最大ディレクトリ、最大拡張子、読み取り不能ファイル数を確認する。
- ディレクトリ treemap で、容量が大きい階層を視覚的に確認する。
- 拡張子別グラフで、拡張子ごとの合計容量とファイル数を比較する。
- treemap または拡張子グラフをクリックして、ファイル一覧を該当条件で絞り込む。
- サブディレクトリ、拡張子、最小サイズ MB、ファイル名/パス検索を組み合わせてファイル一覧を絞り込む。
- 容量上位ファイルと全ファイル一覧を Dash DataTable で確認する。

## 起動設定

CLI 引数が最優先され、未指定の項目は環境変数、それも未指定の場合は既定値が使われます。

| 設定 | CLI | 環境変数 | 既定値 |
| --- | --- | --- | --- |
| 分析対象パス | `target_path` | なし | 現在の作業ディレクトリ |
| bind host | `--host` | `DIRECTORY_STORAGE_ANALYZER_HOST` | `127.0.0.1` |
| bind port | `--port` | `DIRECTORY_STORAGE_ANALYZER_PORT` | `8050` |
| debug mode | `--debug` | `DIRECTORY_STORAGE_ANALYZER_DEBUG` | `false` |
| 分析結果 cache 件数 | `--cache-size` | `DIRECTORY_STORAGE_ANALYZER_CACHE_SIZE` | `3` |

例:

```bash
uv run directory-storage-analyzer ~/Downloads --host 0.0.0.0 --port 8050 --cache-size 5
```

`DIRECTORY_STORAGE_ANALYZER_DEBUG` は `1`, `true`, `yes`, `on` を true、`0`, `false`, `no`, `off` を false として扱います。

## 開発者向けメモ

主要な実装は `src/directory_storage_analyzer/` にあります。

| モジュール | 役割 |
| --- | --- |
| `analysis.py` | ファイルシステム走査、容量集計、空ディレクトリ/読み取り不能ファイルの扱い |
| `app.py`, `layout.py`, `callbacks.py` | Dash アプリの生成、画面構造、UI callback |
| `filters.py`, `charts.py`, `tables.py` | ファイル一覧の絞り込み、Plotly 図表、DataTable 用データ |
| `cli.py`, `profiling.py`, `config.py` | CLI entry point、cProfile 実行、CLI/環境変数からの設定読み込み |

分析結果はサーバー側の `AnalysisCache` に保持され、Dash の `dcc.Store` には cache 参照用の軽量な情報を保存します。`--cache-size` を小さくすると、古い分析結果が削除され、画面側で cache miss として表示される場合があります。

## 開発と検証

変更後は、原則として以下を実行します。

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

分析処理の CPU プロファイルを取得する場合は、専用 entry point を使います。

```bash
uv run directory-storage-analyzer-profile <target_path> --output profile.prof --limit 30
```

`profile.prof` は `pstats` や互換ツールで追加確認できます。標準出力には累積時間順の上位関数が表示されます。

## 注意点

- 対象パスが存在しない場合は `FileNotFoundError`、ディレクトリでない場合は `NotADirectoryError` として分析に失敗します。
- 権限エラーなどで読み取れなかったファイルは `skipped_files` として記録され、KPI とステータスメッセージに読み取り不能件数として表示されます。
- 分析対象にファイルがない場合は空結果として扱い、グラフやテーブルには空状態を表示します。
- Dash 開発サーバーを手動確認で起動した場合は、確認後にプロセスを終了してください。
