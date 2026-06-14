"""分析結果を Dash サーバープロセス内で保持する小さな LRU キャッシュ。"""

from __future__ import annotations

from collections import OrderedDict
from uuid import uuid4

from directory_storage_analyzer.analysis import StorageAnalysisResult


class AnalysisCache:
    """ブラウザ側 Store に大きな DataFrame を置かないための結果キャッシュ。

    Args:
        max_entries: 保持する分析結果の最大件数。古い結果から破棄する。

    Raises:
        ValueError: `max_entries` が 1 未満の場合。
    """

    def __init__(self, max_entries: int = 3) -> None:
        """キャッシュの最大件数を指定して初期化する。"""

        if max_entries < 1:
            raise ValueError("max_entries must be greater than or equal to 1")
        self._max_entries = max_entries
        self._entries: OrderedDict[str, StorageAnalysisResult] = OrderedDict()

    def put(self, result: StorageAnalysisResult) -> str:
        """分析結果を保存し、参照用 ID を返す。

        Args:
            result: 保存する分析結果。

        Returns:
            Dash の `dcc.Store` に保存する短い参照 ID。
        """

        analysis_id = uuid4().hex
        self._entries[analysis_id] = result
        self._entries.move_to_end(analysis_id)

        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)

        return analysis_id

    def get(self, analysis_id: str | None) -> StorageAnalysisResult | None:
        """参照 ID から分析結果を取得する。

        Args:
            analysis_id: `put` が返した参照 ID。

        Returns:
            見つかった分析結果。存在しない場合は `None`。
        """

        if not analysis_id:
            return None

        result = self._entries.get(analysis_id)
        if result is not None:
            self._entries.move_to_end(analysis_id)
        return result
