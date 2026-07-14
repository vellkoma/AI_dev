"""チャットオーケストレーターモジュール。

LLMクライアント、会話履歴マネージャー、ストリーミングハンドラーを統合し、
チャット処理全体のフローを調整するファサードパターンの実装。

Requirements: 1.2, 1.3, 2.2, 2.3, 4.2, 9.1, 9.2, 9.3
"""

from __future__ import annotations

import time
from typing import Any, Dict

from llm_chat_app.clients.base import BaseLLMClient
from llm_chat_app.core.history import History_Manager
from llm_chat_app.core.stream import Stream_Handler
from llm_chat_app.models import LLMResponse, Message


class ChatOrchestrator:
    """チャット処理の統合オーケストレーター。

    LLMクライアント、会話履歴マネージャー、ストリーミングハンドラーの
    3つのコンポーネントを統合し、ユーザーメッセージ送信からレスポンス受信、
    履歴追加までの一連のフローを管理する。

    パフォーマンス統計（リクエスト数、トークン数、応答時間、推定コスト）の
    追跡機能も提供する。

    Attributes:
        client: LLMクライアント（API版またはローカル版）
        history_manager: 会話履歴マネージャー
        stream_handler: ストリーミングハンドラー
    """

    def __init__(
        self,
        client: BaseLLMClient,
        history_manager: History_Manager,
        stream_handler: Stream_Handler,
    ) -> None:
        """ChatOrchestratorを初期化する。

        Args:
            client: LLMクライアント（API版またはローカル版）
            history_manager: 会話履歴マネージャー
            stream_handler: ストリーミングハンドラー
        """
        self.client: BaseLLMClient = client
        self.history_manager: History_Manager = history_manager
        self.stream_handler: Stream_Handler = stream_handler
        self._stats: Dict[str, Any] = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_time": 0.0,
            "estimated_cost": 0.0,
        }

    def send_message(self, user_input: str) -> str:
        """ユーザーメッセージを送信し、LLMレスポンスを取得する。

        以下の一連のフローを実行する:
        1. ユーザーメッセージをMessageとして作成し履歴に追加
        2. ストリーミングを開始
        3. LLMクライアントにメッセージを送信（ストリーミングモード）
        4. ストリーミングを終了
        5. アシスタントレスポンスを履歴に追加
        6. パフォーマンス統計を更新
        7. レスポンス内容を返す

        エラー発生時はストリーミング状態を復旧してから例外を再送出する。

        Args:
            user_input: ユーザーが入力したメッセージ文字列

        Returns:
            LLMからのレスポンステキスト

        Raises:
            NetworkError: ネットワーク接続に失敗した場合
            AuthenticationError: API認証に失敗した場合
            RateLimitError: レート制限に達した場合
            ModelLoadError: ローカルモデルのロードに失敗した場合
        """
        # ユーザーメッセージを作成して履歴に追加
        user_message = Message(
            role="user",
            content=user_input,
            timestamp=time.time(),
        )
        self.history_manager.add_message(user_message)

        # ストリーミング開始
        self.stream_handler.start_streaming()

        try:
            # LLMにメッセージを送信（ストリーミングモード）
            response: LLMResponse = self.client.send_message(
                messages=self.history_manager.get_messages(),
                stream=True,
                on_token=self.stream_handler.on_token,
            )

            # ストリーミング終了
            self.stream_handler.end_streaming()

            # アシスタントレスポンスを履歴に追加
            assistant_message = Message(
                role="assistant",
                content=response.content,
                timestamp=time.time(),
            )
            self.history_manager.add_message(assistant_message)

            # パフォーマンス統計を更新
            self._update_stats(response)

            return response.content

        except Exception:
            # エラー発生時: ストリーミング中であれば状態を復旧する
            if self.stream_handler.is_streaming:
                self.stream_handler.end_streaming()
            raise

    def clear_history(self) -> None:
        """会話履歴をクリアする。

        History_Managerに委譲して会話履歴を初期化する。
        """
        self.history_manager.clear_history()

    def save_history(self, filepath: str) -> None:
        """会話履歴をファイルに保存する。

        History_Managerに委譲してJSON形式でファイルに永続化する。

        Args:
            filepath: 保存先ファイルパス
        """
        self.history_manager.save_to_file(filepath)

    def load_history(self, filepath: str) -> None:
        """ファイルから会話履歴を読み込む。

        History_Managerに委譲してJSONファイルから会話履歴を復元する。

        Args:
            filepath: 読み込み元ファイルパス

        Raises:
            FileNotFoundError: ファイルが存在しない場合
            FileFormatError: ファイル形式が不正な場合
        """
        self.history_manager.load_from_file(filepath)

    def get_model_info(self) -> Dict[str, Any]:
        """使用中のモデル情報を取得する。

        LLMクライアントに委譲してモデル名、プロバイダー、パラメータ等の
        情報を辞書形式で返す。

        Returns:
            モデル情報を含む辞書
        """
        return self.client.get_model_info()

    def get_stats(self) -> Dict[str, Any]:
        """パフォーマンス統計を取得する。

        累積のリクエスト数、トークン数、応答時間、平均応答時間、
        推定コストを辞書形式で返す。

        Returns:
            以下のキーを含む辞書:
            - total_requests: 累積リクエスト数
            - total_tokens: 累積トークン数
            - total_time: 累積応答時間（秒）
            - average_response_time: 平均応答時間（秒）
            - estimated_cost: 推定コスト（USD）
        """
        stats = self._stats.copy()
        # 平均応答時間を計算
        if stats["total_requests"] > 0:
            stats["average_response_time"] = (
                stats["total_time"] / stats["total_requests"]
            )
        else:
            stats["average_response_time"] = 0.0
        return stats

    def _update_stats(self, response: LLMResponse) -> None:
        """パフォーマンス統計を更新する。

        LLMレスポンスからトークン使用量と応答時間を取得し、
        累積統計を更新する。推定コストはトークン単価ベースの
        ヒューリスティックで計算する。

        Args:
            response: LLMからのレスポンスデータ
        """
        self._stats["total_requests"] += 1
        self._stats["total_time"] += response.response_time

        if response.usage:
            prompt_tokens = response.usage.get("prompt_tokens", 0)
            completion_tokens = response.usage.get("completion_tokens", 0)
            total_tokens = prompt_tokens + completion_tokens

            self._stats["total_tokens"] += total_tokens

            # 推定コスト計算（簡易ヒューリスティック）
            # プロンプトトークン: $0.00003/token、完了トークン: $0.00006/token
            estimated_cost = (prompt_tokens * 0.00003) + (completion_tokens * 0.00006)
            self._stats["estimated_cost"] += estimated_cost
