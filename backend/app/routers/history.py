"""会話履歴APIルーター。

会話セッションのCRUD操作とキーワード検索エンドポイントを提供する。
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.dependencies import get_session_service
from backend.app.schemas.chat import ChatMessage
from backend.app.schemas.history import (
    SessionDetailResponse,
    SessionListResponse,
)
from backend.app.services.session_service import SessionService

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/sessions", response_model=SessionListResponse)
def list_sessions(
    service: SessionService = Depends(get_session_service),
) -> SessionListResponse:
    """全セッション一覧を更新日時降順で取得する。

    Returns:
        SessionListResponse: セッション概要のリスト
    """
    sessions = service.list_sessions()
    return SessionListResponse(sessions=sessions)


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(
    session_id: str,
    service: SessionService = Depends(get_session_service),
) -> SessionDetailResponse:
    """指定されたセッションの詳細情報を取得する。

    Args:
        session_id: セッション識別子

    Returns:
        SessionDetailResponse: セッションの全メッセージと詳細情報

    Raises:
        HTTPException(404): セッションが見つからない場合
    """
    try:
        conversation = service.get_session(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")

    # ConversationのメッセージをChatMessageスキーマに変換
    messages = [
        ChatMessage(role=msg.role, content=msg.content) for msg in conversation.messages
    ]

    return SessionDetailResponse(
        session_id=conversation.session_id,
        messages=messages,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        model_name=conversation.model_name,
        total_tokens=conversation.total_tokens,
    )


@router.post("/sessions", response_model=SessionDetailResponse, status_code=201)
def create_session(
    model_name: Optional[str] = Query(default="", description="使用するモデル名"),
    service: SessionService = Depends(get_session_service),
) -> SessionDetailResponse:
    """新しい会話セッションを作成する。

    Args:
        model_name: 使用するモデル名（オプション）

    Returns:
        SessionDetailResponse: 作成されたセッションの詳細情報
    """
    conversation = service.create_session(model_name=model_name or "")

    return SessionDetailResponse(
        session_id=conversation.session_id,
        messages=[],
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        model_name=conversation.model_name,
        total_tokens=conversation.total_tokens,
    )


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: str,
    service: SessionService = Depends(get_session_service),
) -> None:
    """指定されたセッションを削除する。

    Args:
        session_id: セッション識別子

    Raises:
        HTTPException(404): セッションが見つからない場合
    """
    try:
        service.delete_session(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")


@router.get("/search", response_model=SessionListResponse)
def search_sessions(
    keyword: str = Query(default="", description="検索キーワード"),
    service: SessionService = Depends(get_session_service),
) -> SessionListResponse:
    """キーワードでセッションを全文検索する。

    メッセージ内容にキーワードが含まれるセッションを返す。
    キーワードが空の場合は全セッションを返す。

    Args:
        keyword: 検索キーワード

    Returns:
        SessionListResponse: 検索結果のセッション概要リスト
    """
    sessions = service.search_sessions(keyword)
    return SessionListResponse(sessions=sessions)
