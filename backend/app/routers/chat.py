"""チャットAPIルーター。

SSEストリーミングによるチャットメッセージ送受信を提供する。
POST /api/chat/send エンドポイントで、LLMレスポンスを
トークン単位でリアルタイム配信する。

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
"""

from __future__ import annotations

import json
import logging
import time
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from backend.app.dependencies import (
    get_llm_service,
    get_rag_service,
    get_session_service,
    get_stats_service,
)
from backend.app.schemas.chat import ChatRequest
from backend.app.schemas.stats import RequestRecord
from backend.app.services.llm_service import LLMService
from backend.app.services.session_service import SessionService
from backend.app.services.stats_service import StatsService
from llm_chat_app.models import Message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _convert_history_to_messages(request: ChatRequest) -> list[Message]:
    """ChatRequestの履歴とメッセージをllm_chat_appのMessageリストに変換する。

    スキーマのChatMessageからllm_chat_appのMessageデータクラスへ変換し、
    最新のユーザーメッセージを末尾に追加する。

    Args:
        request: チャットリクエスト

    Returns:
        llm_chat_app.models.Message のリスト
    """
    messages: list[Message] = []

    # 会話履歴を変換
    for chat_msg in request.history:
        messages.append(
            Message(
                role=chat_msg.role,
                content=chat_msg.content,
                timestamp=time.time(),
            )
        )

    # 最新のユーザーメッセージを追加
    messages.append(
        Message(
            role="user",
            content=request.message,
            timestamp=time.time(),
        )
    )

    return messages


async def _get_rag_context(
    request: ChatRequest,
    rag_service: Optional[object],
) -> Optional[str]:
    """RAGモードが有効な場合、関連ドキュメントコンテキストを取得する。

    RAGServiceが未実装（None）の場合はNoneを返す。
    エラーが発生した場合もNoneを返し、通常応答にフォールバックする。

    Args:
        request: チャットリクエスト
        rag_service: RAGサービスインスタンス（Noneの場合あり）

    Returns:
        RAGコンテキスト文字列。取得できない場合はNone。
    """
    if not request.rag_enabled:
        return None

    if rag_service is None:
        logger.warning("RAGモードが有効ですが、RAGServiceが未初期化です。")
        return None

    try:
        # RAGServiceのsearch_relevant_chunks + build_rag_contextを呼び出す
        chunks = rag_service.search_relevant_chunks(request.message)
        if not chunks:
            return None
        context = rag_service.build_rag_context(chunks)
        logger.info(f"RAGコンテキスト構築完了: {len(chunks)}件のチャンクを使用")
        return context
        if not chunks:
            return None
        context = rag_service.build_rag_context(chunks)
        logger.info(f"RAGコンテキスト構築完了: {len(context)}文字")
        return context
    except Exception as e:
        logger.error(f"RAGコンテキスト取得エラー: {e}")
        return None


async def _stream_chat_events(
    request: ChatRequest,
    llm_service: LLMService,
    session_service: SessionService,
    stats_service: StatsService,
    rag_service: Optional[object],
) -> AsyncGenerator[dict, None]:
    """チャットSSEイベントを生成する非同期ジェネレーター。

    LLMServiceからトークンをストリーミング受信し、SSEイベント形式で
    逐次返す。完了時にStatsServiceへの記録とSessionServiceの更新を行う。

    Args:
        request: チャットリクエスト
        llm_service: LLMサービス
        session_service: セッション管理サービス
        stats_service: 統計サービス
        rag_service: RAGサービス（Noneの場合あり）

    Yields:
        SSEイベント辞書（event, data フィールドを含む）
    """
    # メッセージ変換
    messages = _convert_history_to_messages(request)

    # RAGコンテキスト取得
    rag_context = await _get_rag_context(request, rag_service)

    # LLMストリーミング開始
    collected_response = ""
    metadata = {}

    try:
        async for event in llm_service.stream_response(
            messages=messages,
            rag_context=rag_context,
        ):
            event_type = event.get("type", "")

            if event_type == "token":
                # トークンイベント: 逐次配信
                token_data = event.get("data", "")
                collected_response += token_data
                yield {
                    "event": "token",
                    "data": json.dumps({"token": token_data}, ensure_ascii=False),
                }

            elif event_type == "done":
                # 完了イベント: メタデータ付き
                metadata = event.get("metadata", {})
                done_data = {
                    "message": collected_response,
                    "metadata": metadata,
                }
                yield {
                    "event": "done",
                    "data": json.dumps(done_data, ensure_ascii=False),
                }

            elif event_type == "error":
                # エラーイベント
                error_message = event.get("data", "不明なエラー")
                yield {
                    "event": "error",
                    "data": json.dumps({"error": error_message}, ensure_ascii=False),
                }
                return  # エラー発生時はストリーム終了

    except Exception as e:
        logger.error(f"ストリーミング中に予期しないエラー: {e}")
        yield {
            "event": "error",
            "data": json.dumps(
                {"error": f"ストリーミングエラー: {str(e)}"}, ensure_ascii=False
            ),
        }
        return

    # ストリーミング完了後の処理
    try:
        # StatsService: リクエスト記録
        usage = metadata.get("usage", {})
        response_time = metadata.get("response_time", 0.0)

        record = RequestRecord(
            timestamp=time.time(),
            model_name=llm_service.current_model,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            response_time=response_time,
        )
        stats_service.record_request(record)

    except Exception as e:
        logger.error(f"統計記録エラー: {e}")

    try:
        # SessionService: セッション更新
        if request.session_id:
            # アシスタントの応答メッセージを追加してセッション更新
            assistant_message = Message(
                role="assistant",
                content=collected_response,
                timestamp=time.time(),
            )
            all_messages = messages + [assistant_message]
            session_service.update_session(
                session_id=request.session_id,
                messages=all_messages,
                model_name=llm_service.current_model,
            )

    except FileNotFoundError:
        logger.warning(f"セッションが見つかりません: {request.session_id}")
    except Exception as e:
        logger.error(f"セッション更新エラー: {e}")


@router.post("/send")
async def send_message(
    request: ChatRequest,
    llm_service: LLMService = Depends(get_llm_service),
    session_service: SessionService = Depends(get_session_service),
    stats_service: StatsService = Depends(get_stats_service),
    rag_service=Depends(get_rag_service),
) -> EventSourceResponse:
    """SSEストリーミングでチャットレスポンスを配信する。

    ユーザーのメッセージを受け取り、LLMからのレスポンスを
    トークン単位でSSEイベントとしてストリーミング配信する。

    SSEイベント形式:
        - event: token → {"token": "<トークン文字列>"}
        - event: done  → {"message": "<完全な応答>", "metadata": {...}}
        - event: error → {"error": "<エラーメッセージ>"}

    RAGモードが有効な場合、関連ドキュメントから取得したコンテキストを
    プロンプトに付加してからLLMに送信する。

    ストリーミング完了時にStatsServiceへリクエスト記録し、
    session_idが指定されている場合はSessionServiceでセッションを更新する。

    Args:
        request: チャットリクエスト（message, history, rag_enabled, session_id）
        llm_service: LLMサービス（DI）
        session_service: セッション管理サービス（DI）
        stats_service: 統計サービス（DI）
        rag_service: RAGサービス（DI、未実装時はNone）

    Returns:
        EventSourceResponse: SSEストリーミングレスポンス
    """
    return EventSourceResponse(
        _stream_chat_events(
            request=request,
            llm_service=llm_service,
            session_service=session_service,
            stats_service=stats_service,
            rag_service=rag_service,
        )
    )
