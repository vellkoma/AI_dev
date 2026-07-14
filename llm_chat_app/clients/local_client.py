"""ローカルLLMクライアント実装モジュール。

オープンソースLLMをローカル環境で実行するクライアントを提供します。
llama-cpp-pythonバックエンドとOllamaバックエンドに対応し、
ストリーミング生成と推論速度計測を実装します。

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.2, 9.4
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional

from llm_chat_app.clients.base import BaseLLMClient, LocalModelBackend
from llm_chat_app.exceptions import ModelLoadError
from llm_chat_app.models import LLMResponse, Message

# llama-cpp-pythonはオプショナル依存関係
try:
    from llama_cpp import Llama

    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False

# requestsはOllamaバックエンド用（オプショナル）
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)


class Local_Chat_Client(BaseLLMClient):
    """ローカルLLMを使用するクライアント実装。

    llama-cpp-pythonまたはOllamaバックエンドを使用して、
    ローカル環境でLLM推論を実行します。
    ストリーミング生成と推論速度（tokens/second）の計測に対応します。

    Attributes:
        backend: 使用するローカルモデルバックエンド
        model_path: モデルファイルのパス（llama.cpp用）またはモデル名（Ollama用）
        n_ctx: コンテキストウィンドウサイズ
        n_gpu_layers: GPU使用レイヤー数（0=CPUのみ）
        temperature: 生成時の温度パラメータ
        max_tokens: 1回のレスポンスの最大トークン数
    """

    # Ollamaのデフォルトエンドポイント
    OLLAMA_BASE_URL = "http://localhost:11434"

    def __init__(
        self,
        backend: LocalModelBackend,
        model_path: str,
        n_ctx: int = 2048,
        n_gpu_layers: int = 0,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> None:
        """Local_Chat_Clientを初期化する。

        Args:
            backend: ローカルモデルバックエンド（LLAMA_CPPまたはOLLAMA）
            model_path: モデルファイルのパス（.gguf等）またはOllamaモデル名
            n_ctx: コンテキストウィンドウサイズ（デフォルト: 2048）
            n_gpu_layers: GPU使用レイヤー数（0=CPUのみ、デフォルト: 0）
            temperature: 生成時の温度パラメータ（デフォルト: 0.7）
            max_tokens: 最大トークン数（デフォルト: 2000）

        Raises:
            ModelLoadError: モデルのロードに失敗した場合
        """
        self.backend = backend
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._model: Any = None
        self._last_tokens_per_second: Optional[float] = None

        self._initialize_model()

    def _initialize_model(self) -> None:
        """ローカルモデルをロードして初期化する。

        バックエンドに応じてllama-cpp-pythonまたはOllamaの
        モデルを初期化します。

        Raises:
            ModelLoadError: モデルファイル不在、メモリ不足、
                           ライブラリ未インストール等の場合
        """
        if self.backend == LocalModelBackend.LLAMA_CPP:
            self._initialize_llama_cpp()
        elif self.backend == LocalModelBackend.OLLAMA:
            self._initialize_ollama()
        else:
            raise ModelLoadError(
                message=f"未対応のバックエンドです: {self.backend}",
                details="LLAMA_CPPまたはOLLAMAを指定してください。",
            )

    def _initialize_llama_cpp(self) -> None:
        """llama-cpp-pythonバックエンドでモデルを初期化する。

        Raises:
            ModelLoadError: ライブラリ未インストール、ファイル不在、
                           メモリ不足の場合
        """
        if not LLAMA_CPP_AVAILABLE:
            raise ModelLoadError(
                message="llama-cpp-pythonがインストールされていません。",
                details=(
                    "pip install llama-cpp-python を実行してインストールしてください。"
                ),
            )

        # モデルファイルの存在確認
        if not os.path.isfile(self.model_path):
            raise ModelLoadError(
                message=f"モデルファイルが見つかりません: {self.model_path}",
                details=(
                    "モデルファイルのパスが正しいか確認してください。\n"
                    "GGUFフォーマットのモデルは https://huggingface.co/models?library=gguf "
                    "からダウンロードできます。"
                ),
            )

        try:
            logger.info(
                "llama-cpp-pythonモデルをロード中: %s (n_ctx=%d, n_gpu_layers=%d)",
                self.model_path,
                self.n_ctx,
                self.n_gpu_layers,
            )
            self._model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
                verbose=False,
            )
            logger.info("モデルのロードが完了しました: %s", self.model_path)
        except (MemoryError, OSError) as e:
            raise ModelLoadError(
                message="メモリ不足によりモデルのロードに失敗しました。",
                details=(
                    f"エラー詳細: {e}\n"
                    "対処法:\n"
                    "  - より小さいモデル（7Bパラメータ推奨）を使用してください\n"
                    "  - 他のアプリケーションを終了してメモリを確保してください\n"
                    f"  - n_ctx={self.n_ctx}を小さくしてください（推奨: 512-2048）"
                ),
            ) from e
        except Exception as e:
            raise ModelLoadError(
                message="モデルのロードに失敗しました。",
                details=f"予期しないエラー: {e}",
            ) from e

    def _initialize_ollama(self) -> None:
        """Ollamaバックエンドの接続を検証する。

        Ollamaサーバーが稼働していることを確認します。

        Raises:
            ModelLoadError: requestsライブラリ未インストール、
                           Ollamaサーバー接続失敗の場合
        """
        if not REQUESTS_AVAILABLE:
            raise ModelLoadError(
                message="requestsライブラリがインストールされていません。",
                details="pip install requests を実行してインストールしてください。",
            )

        try:
            # Ollamaサーバーの稼働確認
            response = requests.get(f"{self.OLLAMA_BASE_URL}/api/tags", timeout=5)
            response.raise_for_status()
            logger.info("Ollamaサーバーに接続しました: %s", self.OLLAMA_BASE_URL)
        except requests.exceptions.ConnectionError:
            raise ModelLoadError(
                message="Ollamaサーバーに接続できません。",
                details=(
                    f"Ollamaサーバー ({self.OLLAMA_BASE_URL}) が起動しているか確認してください。\n"
                    "Ollamaのインストール: https://ollama.ai/"
                ),
            )
        except requests.exceptions.Timeout:
            raise ModelLoadError(
                message="Ollamaサーバーへの接続がタイムアウトしました。",
                details=f"サーバー ({self.OLLAMA_BASE_URL}) の応答を確認してください。",
            )
        except Exception as e:
            raise ModelLoadError(
                message="Ollamaサーバーの初期化に失敗しました。",
                details=f"エラー詳細: {e}",
            ) from e

    def _format_prompt(self, messages: List[Message]) -> str:
        """メッセージリストをプロンプト文字列に変換する。

        ChatML形式（Qwen等）でフォーマットします。
        多くの最新モデルがこの形式に対応しています。

        Args:
            messages: 会話履歴のメッセージリスト

        Returns:
            フォーマット済みのプロンプト文字列
        """
        formatted_parts: List[str] = []

        for msg in messages:
            formatted_parts.append(f"<|im_start|>{msg.role}\n{msg.content}<|im_end|>")

        # アシスタントの応答開始トークンを追加
        formatted_parts.append("<|im_start|>assistant\n")

        return "\n".join(formatted_parts)

    def send_message(
        self,
        messages: List[Message],
        stream: bool = False,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> LLMResponse:
        """メッセージを送信してローカルLLMからレスポンスを取得する。

        ストリーミングが有効な場合、各トークン生成時にon_tokenコールバックを呼び出します。
        推論速度（tokens/second）を計測します。

        Args:
            messages: 会話履歴を含むメッセージリスト
            stream: ストリーミング生成を有効化するフラグ
            on_token: ストリーミング時の各トークン受信コールバック関数

        Returns:
            LLMResponse: レスポンスデータ（本文、モデル名、トークン使用量、応答時間）

        Raises:
            ModelLoadError: モデルが初期化されていない場合
        """
        if self.backend == LocalModelBackend.LLAMA_CPP:
            return self._send_message_llama_cpp(messages, stream, on_token)
        elif self.backend == LocalModelBackend.OLLAMA:
            return self._send_message_ollama(messages, stream, on_token)
        else:
            raise ModelLoadError(
                message=f"未対応のバックエンドです: {self.backend}",
            )

    def _send_message_llama_cpp(
        self,
        messages: List[Message],
        stream: bool = False,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> LLMResponse:
        """llama-cpp-pythonバックエンドでメッセージを送信する。

        Args:
            messages: 会話履歴を含むメッセージリスト
            stream: ストリーミング生成を有効化するフラグ
            on_token: ストリーミング時の各トークン受信コールバック

        Returns:
            LLMResponse: レスポンスデータ
        """
        if self._model is None:
            raise ModelLoadError(
                message="モデルが初期化されていません。",
                details="_initialize_model()でモデルをロードしてください。",
            )

        prompt = self._format_prompt(messages)
        start_time = time.time()
        generated_text = ""
        token_count = 0

        if stream:
            # ストリーミング生成
            generation_start = time.time()
            for output in self._model.create_completion(
                prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stop=["<|im_end|>", "<|im_start|>"],
                stream=True,
            ):
                token_text = output["choices"][0]["text"]
                generated_text += token_text
                token_count += 1

                if on_token:
                    on_token(token_text)

            generation_time = time.time() - generation_start
        else:
            # 非ストリーミング生成
            generation_start = time.time()
            output = self._model.create_completion(
                prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stop=["<|im_end|>", "<|im_start|>"],
                stream=False,
            )
            generated_text = output["choices"][0]["text"]
            token_count = output.get("usage", {}).get("completion_tokens", 0)
            generation_time = time.time() - generation_start

        response_time = time.time() - start_time

        # 推論速度の計測（tokens/second）
        if generation_time > 0 and token_count > 0:
            self._last_tokens_per_second = token_count / generation_time
        else:
            self._last_tokens_per_second = 0.0

        logger.info(
            "推論完了: %d tokens, %.2f秒, %.1f tokens/s",
            token_count,
            response_time,
            self._last_tokens_per_second or 0.0,
        )

        # プロンプトトークン数の推定（文字数ベース、4文字≒1トークン）
        estimated_prompt_tokens = len(prompt) // 4

        return LLMResponse(
            content=generated_text.strip(),
            model=os.path.basename(self.model_path),
            usage={
                "prompt_tokens": estimated_prompt_tokens,
                "completion_tokens": token_count,
            },
            response_time=response_time,
        )

    def _send_message_ollama(
        self,
        messages: List[Message],
        stream: bool = False,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> LLMResponse:
        """Ollamaバックエンドでメッセージを送信する。

        Ollama APIのHTTPストリーミングエンドポイントを使用します。

        Args:
            messages: 会話履歴を含むメッセージリスト
            stream: ストリーミング生成を有効化するフラグ
            on_token: ストリーミング時の各トークン受信コールバック

        Returns:
            LLMResponse: レスポンスデータ

        Raises:
            ModelLoadError: Ollamaサーバーとの通信に失敗した場合
        """
        if not REQUESTS_AVAILABLE:
            raise ModelLoadError(
                message="requestsライブラリがインストールされていません。",
            )

        # Ollamaのchat APIフォーマットに変換
        ollama_messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        payload: Dict[str, Any] = {
            "model": self.model_path,
            "messages": ollama_messages,
            "stream": stream,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
                "num_ctx": self.n_ctx,
            },
        }

        start_time = time.time()
        generated_text = ""
        token_count = 0

        try:
            if stream:
                # ストリーミングリクエスト
                generation_start = time.time()
                response = requests.post(
                    f"{self.OLLAMA_BASE_URL}/api/chat",
                    json=payload,  # type: ignore[arg-type]
                    stream=True,
                    timeout=120,
                )
                response.raise_for_status()

                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line.decode("utf-8"))
                        if "message" in chunk and "content" in chunk["message"]:
                            token_text = chunk["message"]["content"]
                            generated_text += token_text
                            token_count += 1

                            if on_token:
                                on_token(token_text)

                        # 完了チェック
                        if chunk.get("done", False):
                            break

                generation_time = time.time() - generation_start
            else:
                # 非ストリーミングリクエスト
                generation_start = time.time()
                response = requests.post(
                    f"{self.OLLAMA_BASE_URL}/api/chat",
                    json=payload,  # type: ignore[arg-type]
                    timeout=120,
                )
                response.raise_for_status()

                result = response.json()
                generated_text = result.get("message", {}).get("content", "")
                token_count = result.get("eval_count", len(generated_text) // 4)
                generation_time = time.time() - generation_start

        except requests.exceptions.ConnectionError:
            raise ModelLoadError(
                message="Ollamaサーバーとの通信に失敗しました。",
                details="サーバーが起動しているか確認してください。",
            )
        except requests.exceptions.Timeout:
            raise ModelLoadError(
                message="Ollamaサーバーへのリクエストがタイムアウトしました。",
                details="モデルが重い場合はタイムアウト値の調整を検討してください。",
            )
        except Exception as e:
            raise ModelLoadError(
                message="Ollamaでの推論に失敗しました。",
                details=f"エラー詳細: {e}",
            ) from e

        response_time = time.time() - start_time

        # 推論速度の計測（tokens/second）
        if generation_time > 0 and token_count > 0:
            self._last_tokens_per_second = token_count / generation_time
        else:
            self._last_tokens_per_second = 0.0

        logger.info(
            "Ollama推論完了: %d tokens, %.2f秒, %.1f tokens/s",
            token_count,
            response_time,
            self._last_tokens_per_second or 0.0,
        )

        # プロンプトトークン数の推定
        prompt_text = " ".join(msg.content for msg in messages)
        estimated_prompt_tokens = len(prompt_text) // 4

        return LLMResponse(
            content=generated_text.strip(),
            model=self.model_path,
            usage={
                "prompt_tokens": estimated_prompt_tokens,
                "completion_tokens": token_count,
            },
            response_time=response_time,
        )

    def get_model_info(self) -> Dict[str, Any]:
        """使用中のモデル情報を取得する。

        Returns:
            モデル情報を含む辞書（バックエンド、モデルパス、設定パラメータ等）
        """
        info: Dict[str, Any] = {
            "backend": self.backend.value,
            "model": os.path.basename(self.model_path),
            "model_path": self.model_path,
            "n_ctx": self.n_ctx,
            "n_gpu_layers": self.n_gpu_layers,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        # 推論速度情報がある場合は追加
        if self._last_tokens_per_second is not None:
            info["tokens_per_second"] = round(self._last_tokens_per_second, 1)

        return info
