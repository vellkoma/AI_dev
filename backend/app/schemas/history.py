"""会話履歴関連のPydanticスキーマ定義。

会話セッションの概要、一覧レスポンス、詳細レスポンスのデータモデルを定義する。
"""

from typing import List

from pydantic import BaseModel

from backend.app.schemas.chat import ChatMessage


class SessionSummary(BaseModel):
    """セッション概要モデル。

    会話セッション一覧表示用の要約情報を表現する。
    セッションID、作成・更新日時、メッセージ数、使用モデル、プレビューを含む。
    """

    session_id: str
    created_at: float
    updated_at: float
    message_count: int
    model_name: str
    preview: str = ""


class SessionListResponse(BaseModel):
    """セッション一覧レスポンス。

    会話セッションの概要リストを返す。
    """

    sessions: List[SessionSummary]


class SessionDetailResponse(BaseModel):
    """セッション詳細レスポンス。

    特定セッションの全メッセージと詳細情報を返す。
    """

    session_id: str
    messages: List[ChatMessage]
    created_at: float
    updated_at: float
    model_name: str
    total_tokens: int
