"""
データモデル定義モジュール

LLMチャットアプリケーションで使用するデータクラスを定義します。
- Message: 会話メッセージ
- LLMResponse: LLMからのレスポンス
- Conversation: 会話セッション
- AppConfig: アプリケーション設定
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Message:
    """会話メッセージを表すデータクラス。

    Attributes:
        role: メッセージの役割（"user" | "assistant" | "system"）
        content: メッセージ本文
        timestamp: メッセージ作成時のUNIXタイムスタンプ
    """

    role: str
    content: str
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換する。

        Returns:
            メッセージデータを含む辞書
        """
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Message:
        """辞書からMessageインスタンスを復元する。

        Args:
            data: メッセージデータを含む辞書

        Returns:
            復元されたMessageインスタンス
        """
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data["timestamp"],
        )


@dataclass
class LLMResponse:
    """LLMレスポンスを表すデータクラス。

    Attributes:
        content: レスポンス本文
        model: 使用されたモデル名
        usage: トークン使用量（{"prompt_tokens": int, "completion_tokens": int}）
        response_time: レスポンス時間（秒）
    """

    content: str
    model: str
    usage: Optional[Dict[str, int]]
    response_time: float

    def get_total_tokens(self) -> int:
        """総トークン数を取得する。

        Returns:
            prompt_tokensとcompletion_tokensの合計値。
            usageがNoneの場合は0を返す。
        """
        if self.usage:
            return self.usage.get("prompt_tokens", 0) + self.usage.get(
                "completion_tokens", 0
            )
        return 0


@dataclass
class Conversation:
    """会話セッションを表すデータクラス。

    Attributes:
        session_id: セッション識別子（UUID文字列）
        messages: 会話メッセージのリスト
        created_at: セッション作成時のUNIXタイムスタンプ
        updated_at: 最終更新時のUNIXタイムスタンプ
        model_name: 使用中のモデル名
        total_tokens: セッション全体の累積トークン数
    """

    session_id: str
    messages: List[Message] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0
    model_name: str = ""
    total_tokens: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換する（JSON保存用）。

        Returns:
            会話セッションデータを含む辞書
        """
        return {
            "session_id": self.session_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "model_name": self.model_name,
            "total_tokens": self.total_tokens,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Conversation:
        """辞書からConversationインスタンスを復元する（JSONロード用）。

        Args:
            data: 会話セッションデータを含む辞書

        Returns:
            復元されたConversationインスタンス
        """
        return cls(
            session_id=data["session_id"],
            messages=[Message.from_dict(msg) for msg in data["messages"]],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            model_name=data["model_name"],
            total_tokens=data["total_tokens"],
        )


@dataclass
class AppConfig:
    """アプリケーション設定を表すデータクラス。

    Attributes:
        api_provider: APIプロバイダー名（"openai" | "claude" | "gemini"）
        api_key: API認証キー
        api_model: 使用するAPIモデル名
        local_backend: ローカルモデルバックエンド（"llama_cpp" | "ollama"）
        local_model_path: ローカルモデルファイルのパス
        local_n_ctx: コンテキストウィンドウサイズ
        local_n_gpu_layers: GPU使用レイヤー数（0=CPUのみ）
        temperature: 生成時の温度パラメータ
        max_tokens: 1回のレスポンスの最大トークン数
        history_max_tokens: 会話履歴の最大トークン数
        log_enabled: ログ出力の有効/無効
        log_level: ログレベル（"DEBUG" | "INFO" | "WARNING" | "ERROR"）
        log_file: ログファイルのパス
    """

    # API設定
    api_provider: Optional[str] = None
    api_key: Optional[str] = None
    api_model: str = "gpt-3.5-turbo"

    # ローカルモデル設定
    local_backend: Optional[str] = None
    local_model_path: Optional[str] = None
    local_n_ctx: int = 2048
    local_n_gpu_layers: int = 0

    # 共通設定
    temperature: float = 0.7
    max_tokens: int = 2000
    history_max_tokens: int = 4000

    # ログ設定
    log_enabled: bool = True
    log_level: str = "INFO"
    log_file: str = "chat.log"
