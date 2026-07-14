"""Pydanticスキーマパッケージ。

バックエンドAPIのリクエスト・レスポンスモデルを提供する。
"""

from backend.app.schemas.chat import ChatMessage, ChatMetadata, ChatRequest
from backend.app.schemas.history import (
    SessionDetailResponse,
    SessionListResponse,
    SessionSummary,
)
from backend.app.schemas.models import (
    ModelInfo,
    ModelListResponse,
    ModelSwitchRequest,
    ModelSwitchResponse,
)
from backend.app.schemas.rag import (
    ChunkResult,
    DocumentListResponse,
    DocumentMetadata,
    DocumentUploadResponse,
)
from backend.app.schemas.stats import (
    CumulativeStats,
    ModelStats,
    ModelStatsResponse,
    RequestRecord,
    StatsResponse,
    TimelineBucket,
    TimelineStatsResponse,
)

__all__ = [
    # chat
    "ChatMessage",
    "ChatRequest",
    "ChatMetadata",
    # models
    "ModelInfo",
    "ModelListResponse",
    "ModelSwitchRequest",
    "ModelSwitchResponse",
    # history
    "SessionSummary",
    "SessionListResponse",
    "SessionDetailResponse",
    # stats
    "CumulativeStats",
    "ModelStats",
    "TimelineBucket",
    "RequestRecord",
    "StatsResponse",
    "ModelStatsResponse",
    "TimelineStatsResponse",
    # rag
    "DocumentMetadata",
    "DocumentListResponse",
    "ChunkResult",
    "DocumentUploadResponse",
]
