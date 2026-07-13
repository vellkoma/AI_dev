"""統計APIルーター。

パフォーマンス統計の累積値、モデル別集計、時系列集計を提供する。
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.dependencies import get_stats_service
from backend.app.schemas.stats import (
    ModelStatsResponse,
    StatsResponse,
    TimelineStatsResponse,
)
from backend.app.services.stats_service import StatsService

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
def get_stats(
    stats_service: StatsService = Depends(get_stats_service),
) -> StatsResponse:
    """累積統計を取得する。

    全リクエストの合計リクエスト数、合計トークン数、
    平均応答時間、推定コストを返す。
    """
    cumulative = stats_service.get_cumulative_stats()
    return StatsResponse(stats=cumulative)


@router.get("/by-model", response_model=ModelStatsResponse)
def get_stats_by_model(
    stats_service: StatsService = Depends(get_stats_service),
) -> ModelStatsResponse:
    """モデル別統計を取得する。

    各モデルのリクエスト数、トークン数、平均応答時間を返す。
    """
    models = stats_service.get_stats_by_model()
    return ModelStatsResponse(models=models)


@router.get("/timeline", response_model=TimelineStatsResponse)
def get_stats_timeline(
    period: str = Query(default="daily", description="集計期間: daily, weekly, monthly"),
    stats_service: StatsService = Depends(get_stats_service),
) -> TimelineStatsResponse:
    """時系列統計を取得する。

    指定した期間（日別/週別/月別）ごとのリクエスト数とトークン数を返す。
    """
    try:
        timeline = stats_service.get_timeline_stats(period=period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return TimelineStatsResponse(timeline=timeline, period=period)
