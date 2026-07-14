"""パフォーマンス統計の集計と管理を担当するサービス。

リクエスト記録のインメモリ保持とJSONファイルへの永続化を行い、
累積統計、モデル別統計、時系列統計（日別/週別/月別）を提供する。
"""

import json
import threading
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from backend.app.schemas.stats import (
    CumulativeStats,
    ModelStats,
    RequestRecord,
    TimelineBucket,
)

# デフォルトコスト: $0.002 / 1Kトークン
DEFAULT_COST_PER_1K_TOKENS = 0.002


class StatsService:
    """パフォーマンス統計の集計と管理を担当するサービス。

    インメモリリストにリクエスト記録を保持し、JSONファイルに永続化する。
    累積統計、モデル別統計、時系列統計（日別/週別/月別）を提供する。
    """

    def __init__(self, storage_path: Path):
        """StatsServiceを初期化する。

        Args:
            storage_path: 統計データを永続化するJSONファイルのパス
        """
        self.storage_path = Path(storage_path)
        self._records: List[RequestRecord] = []
        self._lock = threading.Lock()
        self._load_records()

    def _load_records(self) -> None:
        """既存のJSONファイルからリクエスト記録を読み込む。

        ファイルが存在しない場合や読み込みに失敗した場合は空リストで開始する。
        """
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._records = [RequestRecord(**record) for record in data]
            except (json.JSONDecodeError, TypeError, KeyError, ValueError):
                # ファイルが破損している場合は空リストで開始
                self._records = []

    def _save_records(self) -> None:
        """リクエスト記録をJSONファイルに永続化する。

        ディレクトリが存在しない場合は自動作成する。
        """
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(
                [record.model_dump() for record in self._records],
                f,
                ensure_ascii=False,
                indent=2,
            )

    def record_request(self, record: RequestRecord) -> None:
        """リクエスト完了時に統計を記録する。

        インメモリリストに追加し、JSONファイルに永続化する。

        Args:
            record: リクエスト記録データ
        """
        with self._lock:
            self._records.append(record)
            self._save_records()

    def get_cumulative_stats(self) -> CumulativeStats:
        """累積統計を返す。

        全リクエストの合計リクエスト数、合計トークン数、
        平均応答時間、推定コストを計算する。

        Returns:
            CumulativeStats: 累積統計データ
        """
        with self._lock:
            total_requests = len(self._records)

            if total_requests == 0:
                return CumulativeStats(
                    total_requests=0,
                    total_tokens=0,
                    average_response_time=0.0,
                    estimated_cost=0.0,
                )

            total_tokens = sum(
                r.prompt_tokens + r.completion_tokens for r in self._records
            )
            total_response_time = sum(r.response_time for r in self._records)
            average_response_time = total_response_time / total_requests
            estimated_cost = (total_tokens / 1000) * DEFAULT_COST_PER_1K_TOKENS

            return CumulativeStats(
                total_requests=total_requests,
                total_tokens=total_tokens,
                average_response_time=round(average_response_time, 4),
                estimated_cost=round(estimated_cost, 6),
            )

    def get_stats_by_model(self) -> List[ModelStats]:
        """モデルごとの統計を返す。

        リクエスト記録をモデル名でグループ化し、
        各モデルのリクエスト数、トークン数、平均応答時間を計算する。

        Returns:
            List[ModelStats]: モデル別統計のリスト
        """
        with self._lock:
            if not self._records:
                return []

            # モデル名でグループ化
            model_groups: Dict[str, List[RequestRecord]] = defaultdict(list)
            for record in self._records:
                model_groups[record.model_name].append(record)

            result: List[ModelStats] = []
            for model_name, records in model_groups.items():
                request_count = len(records)
                token_count = sum(
                    r.prompt_tokens + r.completion_tokens for r in records
                )
                total_response_time = sum(r.response_time for r in records)
                average_response_time = total_response_time / request_count

                result.append(
                    ModelStats(
                        model_name=model_name,
                        request_count=request_count,
                        token_count=token_count,
                        average_response_time=round(average_response_time, 4),
                    )
                )

            return result

    def get_timeline_stats(self, period: str = "daily") -> List[TimelineBucket]:
        """時系列統計を返す。

        リクエスト記録を指定した期間（日別/週別/月別）でバケットに集約し、
        各バケットのリクエスト数とトークン数を返す。

        Args:
            period: 集計期間。"daily", "weekly", "monthly" のいずれか。

        Returns:
            List[TimelineBucket]: 時系列統計バケットのリスト（期間昇順）

        Raises:
            ValueError: periodが不正な値の場合
        """
        if period not in ("daily", "weekly", "monthly"):
            raise ValueError(
                f"Invalid period: {period}. Must be 'daily', 'weekly', or 'monthly'."
            )

        with self._lock:
            if not self._records:
                return []

            # タイムスタンプをバケットキーに変換
            buckets: Dict[str, Dict[str, int]] = defaultdict(
                lambda: {"request_count": 0, "token_count": 0}
            )

            for record in self._records:
                bucket_key = self._get_bucket_key(record.timestamp, period)
                buckets[bucket_key]["request_count"] += 1
                buckets[bucket_key]["token_count"] += (
                    record.prompt_tokens + record.completion_tokens
                )

            # 期間昇順でソートして返す
            result: List[TimelineBucket] = []
            for bucket_key in sorted(buckets.keys()):
                result.append(
                    TimelineBucket(
                        period=bucket_key,
                        request_count=buckets[bucket_key]["request_count"],
                        token_count=buckets[bucket_key]["token_count"],
                    )
                )

            return result

    @staticmethod
    def _get_bucket_key(timestamp: float, period: str) -> str:
        """タイムスタンプを期間に応じたバケットキーに変換する。

        Args:
            timestamp: Unixタイムスタンプ
            period: 集計期間（"daily", "weekly", "monthly"）

        Returns:
            str: バケットキー文字列
                - daily: "2024-01-15"
                - weekly: "2024-W03"
                - monthly: "2024-01"
        """
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)

        if period == "daily":
            return dt.strftime("%Y-%m-%d")
        elif period == "weekly":
            # ISO週番号を使用
            iso_year, iso_week, _ = dt.isocalendar()
            return f"{iso_year}-W{iso_week:02d}"
        elif period == "monthly":
            return dt.strftime("%Y-%m")
        else:
            return dt.strftime("%Y-%m-%d")
