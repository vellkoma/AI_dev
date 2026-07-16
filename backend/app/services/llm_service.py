"""LLMサービスモジュール。

既存のBaseLLMClientをラップし、Web API用のSSEストリーミング、
モデル切り替え、モデル一覧取得機能を提供する。

Requirements: 1.2, 2.1, 2.2, 2.3, 3.2, 3.3
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from backend.app.config import BackendConfig
from backend.app.schemas.models import ModelInfo
from llm_chat_app.clients.api_client import API_Chat_Client
from llm_chat_app.clients.base import APIProvider, BaseLLMClient
from llm_chat_app.exceptions import (
    AuthenticationError,
    ChatAppError,
    ModelLoadError,
    NetworkError,
    RateLimitError,
)
from llm_chat_app.models import LLMResponse, Message

logger = logging.getLogger(__name__)

# プロバイダー名からAPIProviderへのマッピング
PROVIDER_MAP: Dict[str, APIProvider] = {
    "openai": APIProvider.OPENAI,
    "claude": APIProvider.CLAUDE,
    "gemini": APIProvider.GEMINI,
}

# プロバイダーごとのデフォルトモデル
DEFAULT_MODELS: Dict[str, str] = {
    "openai": "gpt-3.5-turbo",
    "claude": "claude-3-haiku-20240307",
    "gemini": "gemini-1.5-flash",
}

# プロバイダーごとのAPIキー環境変数名
API_KEY_ENV_VARS: Dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


class LLMService:
    """LLMクライアント管理とメッセージ送信を担当するサービス。

    既存のBaseLLMClientをラップし、SSEストリーミング用の
    非同期ジェネレーターを提供する。モデル切り替えや
    利用可能モデル一覧取得機能も含む。
    """

    def __init__(self, config: BackendConfig) -> None:
        """LLMServiceを初期化する。

        Args:
            config: バックエンド設定
        """
        self.config = config
        self._current_client: Optional[BaseLLMClient] = None
        self._current_model: str = config.default_model
        self._current_provider: str = config.default_provider
        self._initialize_client()

    def _initialize_client(self) -> None:
        """設定に基づいてLLMクライアントを初期化する。

        APIキーが見つからない場合はクライアントをNoneに設定し、
        ログに警告を出力する。
        """
        api_key = self._get_api_key(self._current_provider)
        if not api_key:
            logger.warning(
                f"APIキーが見つかりません (provider={self._current_provider})。"
                "クライアントは未初期化状態です。"
            )
            self._current_client = None
            return

        provider_enum = PROVIDER_MAP.get(self._current_provider)
        if not provider_enum:
            logger.warning(
                f"未対応のプロバイダー: {self._current_provider}。"
                "クライアントは未初期化状態です。"
            )
            self._current_client = None
            return

        try:
            self._current_client = API_Chat_Client(
                provider=provider_enum,
                api_key=api_key,
                model=self._current_model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            logger.info(
                f"LLMクライアント初期化完了: "
                f"provider={self._current_provider}, model={self._current_model}"
            )
        except Exception as e:
            logger.error(f"LLMクライアント初期化失敗: {e}")
            self._current_client = None

    def _get_api_key(self, provider: str) -> Optional[str]:
        """プロバイダーに対応するAPIキーを取得する。

        設定のapi_keyフィールド、または環境変数から取得する。

        Args:
            provider: プロバイダー名

        Returns:
            APIキー文字列。見つからない場合はNone。
        """
        # 設定に直接指定されている場合
        if self.config.api_key:
            return self.config.api_key

        # 環境変数から取得
        env_var = API_KEY_ENV_VARS.get(provider)
        if env_var:
            return os.getenv(env_var)

        return None

    async def stream_response(
        self,
        messages: List[Message],
        rag_context: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """SSEイベントとしてトークンをストリーミング配信する。

        トークンを逐次生成し、完了時にはusageとresponse_timeを含む
        doneイベントを返す。エラー発生時はerrorイベントを返す。

        Args:
            messages: 会話履歴を含むメッセージリスト
            rag_context: RAGで取得したコンテキスト（オプション）

        Yields:
            dict: SSEイベント辞書。typeは "token", "done", "error" のいずれか。
                - token: {"type": "token", "data": "<トークン文字列>"}
                - done: {"type": "done", "data": "", "metadata": {...}}
                - error: {"type": "error", "data": "<エラーメッセージ>"}
        """
        # クライアント未初期化チェック
        if self._current_client is None:
            yield {
                "type": "error",
                "data": "LLMクライアントが初期化されていません。APIキーを確認してください。",
            }
            return

        # RAGコンテキストがある場合、systemメッセージとして先頭に追加
        effective_messages = list(messages)
        if rag_context:
            rag_system_message = Message(
                role="system",
                content=(
                    "あなたはRAG（検索拡張生成）アシスタントです。"
                    "ユーザーから提供された以下のドキュメントデータに基づいて回答してください。"
                    "ドキュメントの内容を直接参照し、具体的に回答してください。"
                    "「ファイルが見られない」「添付ファイルの内容は提供されていない」などとは絶対に言わないでください。"
                    "以下がユーザーが提供したドキュメントの内容です:\n\n"
                    f"{rag_context}"
                ),
                timestamp=time.time(),
            )
            effective_messages.insert(0, rag_system_message)

        # トークン収集用リスト
        collected_tokens: List[str] = []
        start_time = time.time()

        try:
            # on_tokenコールバックでトークンを収集する
            # send_messageは同期メソッドなのでrun_in_executorで非同期化
            def on_token_callback(token: str) -> None:
                """トークン受信コールバック。"""
                collected_tokens.append(token)

            # 別スレッドでLLM呼び出しを実行（ストリーミング）
            loop = asyncio.get_event_loop()
            response: LLMResponse = await loop.run_in_executor(
                None,
                lambda: self._current_client.send_message(
                    messages=effective_messages,
                    stream=True,
                    on_token=on_token_callback,
                ),
            )

            # 収集したトークンを逐次yield
            for token in collected_tokens:
                yield {"type": "token", "data": token}

            # 完了イベント
            response_time = time.time() - start_time
            metadata: Dict[str, Any] = {
                "response_time": response_time,
            }
            if response.usage:
                metadata["usage"] = response.usage

            yield {
                "type": "done",
                "data": "",
                "metadata": metadata,
            }

        except AuthenticationError as e:
            logger.error(f"認証エラー: {e}")
            yield {
                "type": "error",
                "data": f"API認証エラー: {e.user_message}",
            }
        except RateLimitError as e:
            logger.error(f"レート制限エラー: {e}")
            yield {
                "type": "error",
                "data": f"レート制限エラー: {e.user_message}",
            }
        except NetworkError as e:
            logger.error(f"ネットワークエラー: {e}")
            yield {
                "type": "error",
                "data": f"ネットワークエラー: {e.user_message}",
            }
        except ChatAppError as e:
            logger.error(f"LLMエラー: {e}")
            yield {
                "type": "error",
                "data": f"LLMエラー: {e.user_message}",
            }
        except Exception as e:
            logger.error(f"予期しないエラー: {e}")
            yield {
                "type": "error",
                "data": f"予期しないエラーが発生しました: {str(e)}",
            }

    def switch_model(self, model_name: str, provider: str) -> ModelInfo:
        """使用モデルを切り替え、LLMClientを再構成する。

        Args:
            model_name: 切り替え先のモデル名
            provider: プロバイダー名（"openai", "claude", "gemini"）

        Returns:
            ModelInfo: 切り替え後のモデル情報

        Raises:
            ValueError: 未対応のプロバイダーが指定された場合
            RuntimeError: クライアントの初期化に失敗した場合
        """
        # プロバイダー検証
        if provider not in PROVIDER_MAP:
            raise ValueError(
                f"未対応のプロバイダー: {provider}。"
                f"利用可能: {list(PROVIDER_MAP.keys())}"
            )

        # APIキー取得
        api_key = self._get_api_key(provider)
        if not api_key:
            raise RuntimeError(
                f"プロバイダー '{provider}' のAPIキーが設定されていません。"
            )

        # クライアント再構成
        provider_enum = PROVIDER_MAP[provider]
        try:
            self._current_client = API_Chat_Client(
                provider=provider_enum,
                api_key=api_key,
                model=model_name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            self._current_model = model_name
            self._current_provider = provider
            logger.info(f"モデル切り替え完了: provider={provider}, model={model_name}")
        except Exception as e:
            logger.error(f"モデル切り替え失敗: {e}")
            raise RuntimeError(f"モデル切り替えに失敗しました: {str(e)}")

        return ModelInfo(
            name=model_name,
            provider=provider,
            status="available",
            parameters={
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            },
        )

    def get_available_models(self) -> List[ModelInfo]:
        """利用可能なモデル一覧を返す。

        各プロバイダーのAPIキーの有無に基づいてステータスを判定し、
        デフォルトモデルのリストを返す。

        Returns:
            ModelInfo のリスト
        """
        models: List[ModelInfo] = []

        for provider_name, default_model in DEFAULT_MODELS.items():
            api_key = self._get_api_key(provider_name)
            status = "available" if api_key else "unavailable"

            models.append(
                ModelInfo(
                    name=default_model,
                    provider=provider_name,
                    status=status,
                    parameters={
                        "temperature": self.config.temperature,
                        "max_tokens": self.config.max_tokens,
                    },
                )
            )

        return models

    @property
    def current_model(self) -> str:
        """現在使用中のモデル名を返す。"""
        return self._current_model

    @property
    def current_provider(self) -> str:
        """現在使用中のプロバイダー名を返す。"""
        return self._current_provider

    @property
    def is_initialized(self) -> bool:
        """クライアントが初期化済みかどうかを返す。"""
        return self._current_client is not None
