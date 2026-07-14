"""パフォーマンス統計関連のPydanticスキーマ定義。

累積統計、モデル別統計、時系列統計、リクエスト記録のデータモデルを定義する。
"""

from typing import List

from pydantic import BaseModel


class CumulativeStats(BaseModel):
    """累積統計モデル。

    全体のリクエスト数、トークン数、平均応答時間、推定コストを集計する。
    """

    total_requests: int
    total_tokens: int
    average_response_time: float
    estimated_cost: float


class ModelStats(BaseModel):
    """モデル別統計モデル。

    特定モデルのリクエスト数、トークン数、平均応答時間を集計する。
    """

    model_name: str
    request_count: int
    token_count: int
    average_response_time: float


class TimelineBucket(BaseModel):
    """時系列統計バケットモデル。

    日別・週別・月別の期間ごとのリクエスト数とトークン数を表現する。
    periodの形式: "2024-01-15"（日別）、"2024-W03"（週別）、"2024-01"（月別）
    """

    period: str
    request_count: int
    token_count: int


class RequestRecord(BaseModel):
    """リクエスト記録モデル。

    統計記録用の内部データモデル。
    各リクエストのタイムスタンプ、モデル名、トークン数、応答時間を保持する。
    """

    timestamp: float
    model_name: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    response_time: float = 0.0


class StatsResponse(BaseModel):
    """累積統計レスポンス。

    累積統計情報をラップして返す。
    """

    stats: CumulativeStats


class ModelStatsResponse(BaseModel):
    """モデル別統計レスポンス。

    各モデルの統計情報リストを返す。
    """

    models: List[ModelStats]


class TimelineStatsResponse(BaseModel):
    """時系列統計レスポンス。

    時系列統計バケットリストと集計期間の種別を返す。
    """

    timeline: List[TimelineBucket]
    period: str
