"""チャット関連のPydanticスキーマ定義。

チャットリクエスト・レスポンスのデータモデルを定義する。
SSEストリーミングのメタデータ情報も含む。
"""

from typing import List, Optional

from pydantic import BaseModel


class ChatMessage(BaseModel):
    """チャットメッセージモデル。

    ユーザー、アシスタント、システムの各ロールを持つメッセージを表現する。
    """

    role: str  # "user" | "assistant" | "system"
    content: str


class ChatRequest(BaseModel):
    """チャットリクエストモデル。

    ユーザーからのチャットメッセージ送信時のリクエストボディを定義する。
    会話履歴やRAGモード設定を含む。
    """

    message: str
    history: List[ChatMessage] = []
    rag_enabled: bool = False
    session_id: Optional[str] = None


class ChatMetadata(BaseModel):
    """チャットレスポンスメタデータ。

    ストリーミング完了時に送信されるトークン使用量、応答時間、
    RAGソース情報を含む。
    """

    usage: Optional[dict] = None
    response_time: float = 0.0
    rag_sources: Optional[List[dict]] = None
