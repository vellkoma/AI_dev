"""LLMクライアント抽象基底クラスモジュール。

LLM実行の共通インターフェースを定義する抽象基底クラスと、
サポートするプロバイダー/バックエンドを示すEnum型を提供します。

Requirements: 1.1, 2.1
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from llm_chat_app.models import LLMResponse, Message


class APIProvider(Enum):
    """サポートするAPIプロバイダーを示すEnum。

    商用LLM APIの提供者を定義します。

    Attributes:
        OPENAI: OpenAI API（GPTモデル）
        CLAUDE: Anthropic Claude API
        GEMINI: Google Gemini API
    """

    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"


class LocalModelBackend(Enum):
    """サポートするローカルモデルバックエンドを示すEnum。

    ローカル環境でLLMを実行するためのバックエンドを定義します。

    Attributes:
        LLAMA_CPP: llama-cpp-pythonバックエンド
        OLLAMA: Ollamaバックエンド
    """

    LLAMA_CPP = "llama_cpp"
    OLLAMA = "ollama"


class BaseLLMClient(ABC):
    """LLM実行の共通インターフェースを定義する抽象基底クラス。

    API版（OpenAI/Claude/Gemini）とローカル版（llama.cpp/Ollama）の
    両方で共通のインターフェースを提供します。
    サブクラスはsend_message()とget_model_info()を実装する必要があります。
    """

    @abstractmethod
    def send_message(
        self,
        messages: List[Message],
        stream: bool = False,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> LLMResponse:
        """メッセージを送信してLLMレスポンスを取得する。

        会話履歴を含むメッセージリストをLLMに送信し、レスポンスを返す。
        ストリーミングが有効な場合、各トークン受信時にon_tokenコールバックを呼び出す。

        Args:
            messages: 会話履歴を含むメッセージリスト
            stream: ストリーミングレスポンスを有効化するフラグ
            on_token: ストリーミング時の各トークン受信コールバック関数

        Returns:
            LLMResponse: 完全なレスポンスデータ（本文、モデル名、トークン使用量、応答時間）

        Raises:
            NetworkError: ネットワーク接続に失敗した場合
            AuthenticationError: API認証に失敗した場合
            RateLimitError: レート制限に達した場合
            ModelLoadError: ローカルモデルのロードに失敗した場合
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """使用中のモデル情報を取得する。

        モデル名、プロバイダー/バックエンド、パラメータ設定などの
        情報を辞書形式で返す。

        Returns:
            モデル情報を含む辞書。以下のキーを含むことを推奨:
            - "model": モデル名
            - "provider" または "backend": プロバイダー/バックエンド名
            - "temperature": 温度パラメータ
            - "max_tokens": 最大トークン数
        """
        pass
