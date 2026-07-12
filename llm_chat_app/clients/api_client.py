"""API_Chat_Clientモジュール。

商用LLM API（OpenAI/Claude/Gemini）を使用するチャットクライアント実装。
ストリーミングレスポンス、エラーハンドリング、エクスポネンシャルバックオフ
によるリトライ機能を提供します。

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 3.1
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional

from llm_chat_app.clients.base import APIProvider, BaseLLMClient
from llm_chat_app.exceptions import (
    AuthenticationError,
    NetworkError,
    RateLimitError,
)
from llm_chat_app.models import LLMResponse, Message

logger = logging.getLogger(__name__)

# リトライ設定
MAX_RETRIES = 3
BASE_DELAY_SECONDS = 1.0


class API_Chat_Client(BaseLLMClient):
    """商用LLM APIを使用するクライアント実装。

    OpenAI、Claude、GeminiのAPIに対応し、ストリーミングレスポンスと
    エラーハンドリング（リトライ含む）を提供します。

    Attributes:
        provider: APIプロバイダー（OpenAI/Claude/Gemini）
        api_key: API認証キー
        model: 使用するモデル名
        temperature: 生成時の温度パラメータ
        max_tokens: 最大トークン数
        client: 初期化されたSDKクライアントインスタンス
    """

    def __init__(
        self,
        provider: APIProvider,
        api_key: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> None:
        """API_Chat_Clientを初期化する。

        Args:
            provider: APIプロバイダー（OpenAI/Claude/Gemini）
            api_key: API認証キー
            model: 使用するモデル名（例: "gpt-4", "claude-3-sonnet-20240229"）
            temperature: 生成時の温度パラメータ（0.0〜2.0）
            max_tokens: 1回のレスポンスの最大トークン数
        """
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client: Any = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """プロバイダーに応じたSDKクライアントを初期化する。

        Raises:
            NetworkError: クライアント初期化中にネットワークエラーが発生した場合
            AuthenticationError: API_Keyが無効な場合
        """
        if self.provider == APIProvider.OPENAI:
            import openai

            self.client = openai.OpenAI(api_key=self.api_key)
        elif self.provider == APIProvider.CLAUDE:
            import anthropic

            self.client = anthropic.Anthropic(api_key=self.api_key)
        elif self.provider == APIProvider.GEMINI:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model)

    def send_message(
        self,
        messages: List[Message],
        stream: bool = False,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> LLMResponse:
        """メッセージを送信してLLMレスポンスを取得する。

        会話履歴を含むメッセージリストをLLMに送信し、レスポンスを返す。
        ストリーミングが有効な場合、各トークン受信時にon_tokenコールバックを呼び出す。
        レート制限エラー時はエクスポネンシャルバックオフでリトライを行う。

        Args:
            messages: 会話履歴を含むメッセージリスト
            stream: ストリーミングレスポンスを有効化するフラグ
            on_token: ストリーミング時の各トークン受信コールバック関数

        Returns:
            LLMResponse: 完全なレスポンスデータ（本文、モデル名、トークン使用量、応答時間）

        Raises:
            NetworkError: ネットワーク接続に失敗した場合
            AuthenticationError: API認証に失敗した場合
            RateLimitError: リトライ上限到達後もレート制限が解除されない場合
        """
        if self.provider == APIProvider.OPENAI:
            return self._send_openai(messages, stream, on_token)
        elif self.provider == APIProvider.CLAUDE:
            return self._send_claude(messages, stream, on_token)
        elif self.provider == APIProvider.GEMINI:
            return self._send_gemini(messages, stream, on_token)
        else:
            raise ValueError(f"未対応のプロバイダー: {self.provider}")

    def get_model_info(self) -> Dict[str, Any]:
        """使用中のモデル情報を取得する。

        Returns:
            モデル情報を含む辞書（model、provider、temperature、max_tokens）
        """
        return {
            "model": self.model,
            "provider": self.provider.value,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

    # =========================================================================
    # OpenAI API実装
    # =========================================================================

    def _send_openai(
        self,
        messages: List[Message],
        stream: bool,
        on_token: Optional[Callable[[str], None]],
    ) -> LLMResponse:
        """OpenAI APIにメッセージを送信する。

        Args:
            messages: 会話履歴を含むメッセージリスト
            stream: ストリーミング有効化フラグ
            on_token: トークン受信コールバック

        Returns:
            LLMResponse: レスポンスデータ
        """
        import openai

        # メッセージをOpenAI形式に変換
        formatted_messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        for attempt in range(MAX_RETRIES + 1):
            try:
                start_time = time.time()

                if stream:
                    return self._stream_openai(
                        formatted_messages, on_token, start_time
                    )
                else:
                    return self._non_stream_openai(formatted_messages, start_time)

            except openai.AuthenticationError as e:
                logger.error(f"OpenAI認証エラー: {e}")
                raise AuthenticationError(
                    details=str(e),
                )
            except openai.RateLimitError as e:
                if attempt < MAX_RETRIES:
                    delay = BASE_DELAY_SECONDS * (2**attempt)
                    logger.warning(
                        f"OpenAIレート制限 (試行 {attempt + 1}/{MAX_RETRIES})"
                        f" - {delay}秒後にリトライ"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"OpenAIレート制限: リトライ上限到達: {e}")
                    raise RateLimitError(
                        details=str(e),
                    )
            except openai.APIConnectionError as e:
                logger.error(f"OpenAIネットワークエラー: {e}")
                raise NetworkError(
                    details=str(e),
                )
            except (openai.APITimeoutError, openai.APIStatusError) as e:
                # ステータスコード別にハンドリング
                if hasattr(e, "status_code"):
                    if e.status_code in (401, 403):
                        logger.error(f"OpenAI認証エラー (HTTP {e.status_code}): {e}")
                        raise AuthenticationError(details=str(e))
                    elif e.status_code == 429:
                        if attempt < MAX_RETRIES:
                            delay = BASE_DELAY_SECONDS * (2**attempt)
                            logger.warning(
                                f"OpenAIレート制限 (試行 {attempt + 1}/{MAX_RETRIES})"
                                f" - {delay}秒後にリトライ"
                            )
                            time.sleep(delay)
                            continue
                        else:
                            logger.error(
                                f"OpenAIレート制限: リトライ上限到達: {e}"
                            )
                            raise RateLimitError(details=str(e))
                logger.error(f"OpenAI APIエラー: {e}")
                raise NetworkError(details=str(e))

        # リトライ上限到達（理論上到達しないが安全のため）
        raise RateLimitError(details="リトライ上限に到達しました")

    def _stream_openai(
        self,
        formatted_messages: List[Dict[str, str]],
        on_token: Optional[Callable[[str], None]],
        start_time: float,
    ) -> LLMResponse:
        """OpenAI APIのストリーミングレスポンスを処理する。

        Args:
            formatted_messages: OpenAI形式のメッセージリスト
            on_token: トークン受信コールバック
            start_time: リクエスト開始時刻

        Returns:
            LLMResponse: 構築された完全なレスポンス
        """
        collected_content = ""
        response_stream = self.client.chat.completions.create(
            model=self.model,
            messages=formatted_messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
        )

        for chunk in response_stream:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                collected_content += token
                if on_token:
                    on_token(token)

        response_time = time.time() - start_time

        return LLMResponse(
            content=collected_content,
            model=self.model,
            usage=None,  # ストリーミング時はusage情報が取得できない場合がある
            response_time=response_time,
        )

    def _non_stream_openai(
        self,
        formatted_messages: List[Dict[str, str]],
        start_time: float,
    ) -> LLMResponse:
        """OpenAI APIの非ストリーミングレスポンスを処理する。

        Args:
            formatted_messages: OpenAI形式のメッセージリスト
            start_time: リクエスト開始時刻

        Returns:
            LLMResponse: レスポンスデータ
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=formatted_messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=False,
        )

        response_time = time.time() - start_time
        content = response.choices[0].message.content or ""
        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            }

        return LLMResponse(
            content=content,
            model=self.model,
            usage=usage,
            response_time=response_time,
        )

    # =========================================================================
    # Claude API実装
    # =========================================================================

    def _send_claude(
        self,
        messages: List[Message],
        stream: bool,
        on_token: Optional[Callable[[str], None]],
    ) -> LLMResponse:
        """Claude APIにメッセージを送信する。

        Args:
            messages: 会話履歴を含むメッセージリスト
            stream: ストリーミング有効化フラグ
            on_token: トークン受信コールバック

        Returns:
            LLMResponse: レスポンスデータ
        """
        import anthropic

        # systemメッセージとユーザー/アシスタントメッセージを分離
        # Claude APIはsystemを別パラメータで渡す必要がある
        system_message = ""
        formatted_messages = []
        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                formatted_messages.append(
                    {"role": msg.role, "content": msg.content}
                )

        for attempt in range(MAX_RETRIES + 1):
            try:
                start_time = time.time()

                if stream:
                    return self._stream_claude(
                        formatted_messages, system_message, on_token, start_time
                    )
                else:
                    return self._non_stream_claude(
                        formatted_messages, system_message, start_time
                    )

            except anthropic.AuthenticationError as e:
                logger.error(f"Claude認証エラー: {e}")
                raise AuthenticationError(
                    details=str(e),
                )
            except anthropic.RateLimitError as e:
                if attempt < MAX_RETRIES:
                    delay = BASE_DELAY_SECONDS * (2**attempt)
                    logger.warning(
                        f"Claudeレート制限 (試行 {attempt + 1}/{MAX_RETRIES})"
                        f" - {delay}秒後にリトライ"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Claudeレート制限: リトライ上限到達: {e}")
                    raise RateLimitError(
                        details=str(e),
                    )
            except anthropic.APIConnectionError as e:
                logger.error(f"Claudeネットワークエラー: {e}")
                raise NetworkError(
                    details=str(e),
                )
            except anthropic.APIStatusError as e:
                # ステータスコード別にハンドリング
                if e.status_code in (401, 403):
                    logger.error(f"Claude認証エラー (HTTP {e.status_code}): {e}")
                    raise AuthenticationError(details=str(e))
                elif e.status_code == 429:
                    if attempt < MAX_RETRIES:
                        delay = BASE_DELAY_SECONDS * (2**attempt)
                        logger.warning(
                            f"Claudeレート制限 (試行 {attempt + 1}/{MAX_RETRIES})"
                            f" - {delay}秒後にリトライ"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(
                            f"Claudeレート制限: リトライ上限到達: {e}"
                        )
                        raise RateLimitError(details=str(e))
                logger.error(f"Claude APIエラー: {e}")
                raise NetworkError(details=str(e))

        # リトライ上限到達
        raise RateLimitError(details="リトライ上限に到達しました")

    def _stream_claude(
        self,
        formatted_messages: List[Dict[str, str]],
        system_message: str,
        on_token: Optional[Callable[[str], None]],
        start_time: float,
    ) -> LLMResponse:
        """Claude APIのストリーミングレスポンスを処理する。

        Args:
            formatted_messages: Claude形式のメッセージリスト
            system_message: システムメッセージ
            on_token: トークン受信コールバック
            start_time: リクエスト開始時刻

        Returns:
            LLMResponse: 構築された完全なレスポンス
        """
        collected_content = ""
        input_tokens = 0
        output_tokens = 0

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if system_message:
            kwargs["system"] = system_message

        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                collected_content += text
                if on_token:
                    on_token(text)

            # ストリーム完了後にusage情報を取得
            final_message = stream.get_final_message()
            if final_message.usage:
                input_tokens = final_message.usage.input_tokens
                output_tokens = final_message.usage.output_tokens

        response_time = time.time() - start_time

        usage = {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
        }

        return LLMResponse(
            content=collected_content,
            model=self.model,
            usage=usage,
            response_time=response_time,
        )

    def _non_stream_claude(
        self,
        formatted_messages: List[Dict[str, str]],
        system_message: str,
        start_time: float,
    ) -> LLMResponse:
        """Claude APIの非ストリーミングレスポンスを処理する。

        Args:
            formatted_messages: Claude形式のメッセージリスト
            system_message: システムメッセージ
            start_time: リクエスト開始時刻

        Returns:
            LLMResponse: レスポンスデータ
        """
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if system_message:
            kwargs["system"] = system_message

        response = self.client.messages.create(**kwargs)

        response_time = time.time() - start_time

        # レスポンスからコンテンツを抽出
        content = ""
        if response.content:
            content = response.content[0].text

        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
            }

        return LLMResponse(
            content=content,
            model=self.model,
            usage=usage,
            response_time=response_time,
        )

    # =========================================================================
    # Gemini API実装
    # =========================================================================

    def _send_gemini(
        self,
        messages: List[Message],
        stream: bool,
        on_token: Optional[Callable[[str], None]],
    ) -> LLMResponse:
        """Gemini APIにメッセージを送信する。

        Args:
            messages: 会話履歴を含むメッセージリスト
            stream: ストリーミング有効化フラグ
            on_token: トークン受信コールバック

        Returns:
            LLMResponse: レスポンスデータ
        """
        from google.api_core import exceptions as google_exceptions

        # メッセージをGemini形式に変換
        # Geminiはroleが "user" と "model" のみ対応
        formatted_contents = []
        for msg in messages:
            if msg.role == "system":
                # systemメッセージはuserメッセージとして追加
                formatted_contents.append(
                    {"role": "user", "parts": [msg.content]}
                )
            elif msg.role == "assistant":
                formatted_contents.append(
                    {"role": "model", "parts": [msg.content]}
                )
            else:
                formatted_contents.append(
                    {"role": "user", "parts": [msg.content]}
                )

        for attempt in range(MAX_RETRIES + 1):
            try:
                start_time = time.time()

                if stream:
                    return self._stream_gemini(
                        formatted_contents, on_token, start_time
                    )
                else:
                    return self._non_stream_gemini(formatted_contents, start_time)

            except google_exceptions.Unauthenticated as e:
                logger.error(f"Gemini認証エラー: {e}")
                raise AuthenticationError(
                    details=str(e),
                )
            except google_exceptions.PermissionDenied as e:
                logger.error(f"Gemini権限エラー: {e}")
                raise AuthenticationError(
                    details=str(e),
                )
            except google_exceptions.ResourceExhausted as e:
                if attempt < MAX_RETRIES:
                    delay = BASE_DELAY_SECONDS * (2**attempt)
                    logger.warning(
                        f"Geminiレート制限 (試行 {attempt + 1}/{MAX_RETRIES})"
                        f" - {delay}秒後にリトライ"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Geminiレート制限: リトライ上限到達: {e}")
                    raise RateLimitError(
                        details=str(e),
                    )
            except (
                google_exceptions.ServiceUnavailable,
                google_exceptions.DeadlineExceeded,
                ConnectionError,
                OSError,
            ) as e:
                logger.error(f"Geminiネットワークエラー: {e}")
                raise NetworkError(
                    details=str(e),
                )
            except google_exceptions.InvalidArgument as e:
                logger.error(f"Gemini APIエラー（無効な引数）: {e}")
                raise NetworkError(details=str(e))

        # リトライ上限到達
        raise RateLimitError(details="リトライ上限に到達しました")

    def _stream_gemini(
        self,
        formatted_contents: List[Dict[str, Any]],
        on_token: Optional[Callable[[str], None]],
        start_time: float,
    ) -> LLMResponse:
        """Gemini APIのストリーミングレスポンスを処理する。

        Args:
            formatted_contents: Gemini形式のコンテンツリスト
            on_token: トークン受信コールバック
            start_time: リクエスト開始時刻

        Returns:
            LLMResponse: 構築された完全なレスポンス
        """
        import google.generativeai as genai

        collected_content = ""

        generation_config = genai.types.GenerationConfig(
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
        )

        response = self.client.generate_content(
            formatted_contents,
            generation_config=generation_config,
            stream=True,
        )

        for chunk in response:
            if chunk.text:
                collected_content += chunk.text
                if on_token:
                    on_token(chunk.text)

        response_time = time.time() - start_time

        # Geminiはusage情報を別途取得
        usage = None
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = {
                "prompt_tokens": getattr(
                    response.usage_metadata, "prompt_token_count", 0
                ),
                "completion_tokens": getattr(
                    response.usage_metadata, "candidates_token_count", 0
                ),
            }

        return LLMResponse(
            content=collected_content,
            model=self.model,
            usage=usage,
            response_time=response_time,
        )

    def _non_stream_gemini(
        self,
        formatted_contents: List[Dict[str, Any]],
        start_time: float,
    ) -> LLMResponse:
        """Gemini APIの非ストリーミングレスポンスを処理する。

        Args:
            formatted_contents: Gemini形式のコンテンツリスト
            start_time: リクエスト開始時刻

        Returns:
            LLMResponse: レスポンスデータ
        """
        import google.generativeai as genai

        generation_config = genai.types.GenerationConfig(
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
        )

        response = self.client.generate_content(
            formatted_contents,
            generation_config=generation_config,
            stream=False,
        )

        response_time = time.time() - start_time
        content = response.text if response.text else ""

        usage = None
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = {
                "prompt_tokens": getattr(
                    response.usage_metadata, "prompt_token_count", 0
                ),
                "completion_tokens": getattr(
                    response.usage_metadata, "candidates_token_count", 0
                ),
            }

        return LLMResponse(
            content=content,
            model=self.model,
            usage=usage,
            response_time=response_time,
        )
