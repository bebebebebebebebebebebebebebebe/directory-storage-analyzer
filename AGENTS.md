# Python Project Context

This repository is a Python 3.13 project for a Dash-based directory storage analyzer. Dependency state is managed with `uv.lock`; prefer `uv` commands when running the application or installing dependencies.

## Codebase Search and Inspection

- When searching, exploring, or verifying code or files, always use Serena MCP first.
- Prefer Serena MCP semantic tools such as `get_symbols_overview`, `find_symbol`, `find_referencing_symbols`, and `find_declaration` for codebase understanding.
- Use shell/file tools such as `rg`, `grep`, `find`, `ls`, `cat`, or editor search only as a fallback when Serena MCP cannot inspect the target file type or required context.
- If falling back from Serena MCP, briefly state why the fallback is necessary.

## Development Servers

検証やテストのために `uv run python main.py` または `python main.py` で Dash 開発サーバーを起動した場合は、確認後に必ず該当プロセスを終了する。バックグラウンドに開発用サーバーを残さない。

## Python Code Style

- Public class / function / method には型ヒントを書く。戻り値がない場合も `-> None` を明示する。
- 命名は PEP 8 に従う。module / file / function / variable は `snake_case`、class は `PascalCase`、module-level constant は `SCREAMING_SNAKE_CASE` を使う。
- import は標準ライブラリ、サードパーティ、ローカル import の順にグループ化する。
- 現時点で `ruff`、`pytest`、`mypy` は project configuration に含まれていないため、必須の検証コマンドとして扱わない。導入する場合は `pyproject.toml` に設定を追加してから AGENTS.md も更新する。

## Documentation Comments

- 実装コードを追加・変更するときは、public class / function / method に日本語 docstring を書き、責務・入力・返却値・重要な失敗条件が分かるようにする。
- public method / function では、意味のある場合に Google-style docstring の `Args:`, `Returns:`, `Raises:` を付ける。
- ファイルシステム走査、Dash callback、データ集計、フィルタ条件の組み合わせ、エラー隔離、開発サーバーの lifecycle など、意図が読み取りにくい private helper には短い意図コメントを書く。
- 実装をそのまま言い換えるだけのコメントは避け、目的・契約・非自明な tradeoff を説明する。
- テストファイルを追加する場合は、原則として説明的な test name で仕様を表現する。コメントは、非自明な setup、race condition、timing behavior、微妙な filesystem expectation がある場合だけ短く追加する。
- この repository では documentation comment を日本語で書く。
