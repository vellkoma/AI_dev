"""Local_Chat_Clientのユニットテスト。

llama-cpp-pythonライブラリがインストールされていない環境でも
テスト可能なように、モックを使用してテストします。
"""

from __future__ import annotations

import os
import time
from unittest.mock import MagicMock, patch

import pytest

from llm_chat_app.clients.base import LocalModelBackend
from llm_chat_app.clients.local_client import Local_Chat_Client
from llm_chat_app.exceptions import ModelLoadError
from llm_chat_app.models import LLMResponse, Message


def _create_llama_cpp_client_with_mock():
    """llama-cpp-pythonモックを使用してLocal_Chat_Clientインスタンスを作成する。

    llama-cpp-pythonがインストールされていない環境でも動作するよう、
    LLAMA_CPP_AVAILABLEをTrueに設定し、Llamaクラスをモックで置き換えます。
    """
    mock_llama_cls = MagicMock()
    mock_model = MagicMock()
    mock_llama_cls.return_value = mock_model

    with patch(
        "llm_chat_app.clients.local_client.LLAMA_CPP_AVAILABLE", True
    ), patch("os.path.isfile", return_value=True), patch(
        "llm_chat_app.clients.local_client.Llama",
        mock_llama_cls,
        create=True,
    ):
        client = Local_Chat_Client(
            backend=LocalModelBackend.LLAMA_CPP,
            model_path="./models/test.gguf",
        )
    return client, mock_model


class TestLocalChatClientInitialization:
    """Local_Chat_Clientの初期化テスト。"""

    def test_llama_cpp_model_file_not_found_raises_model_load_error(self):
        """存在しないモデルファイルパスでModelLoadErrorが発生することを確認。"""
        with patch(
            "llm_chat_app.clients.local_client.LLAMA_CPP_AVAILABLE", True
        ):
            with pytest.raises(ModelLoadError) as exc_info:
                Local_Chat_Client(
                    backend=LocalModelBackend.LLAMA_CPP,
                    model_path="/nonexistent/model.gguf",
                )
            assert "見つかりません" in exc_info.value.user_message

    def test_llama_cpp_not_installed_raises_model_load_error(self):
        """llama-cpp-python未インストール時にModelLoadErrorが発生することを確認。"""
        with patch(
            "llm_chat_app.clients.local_client.LLAMA_CPP_AVAILABLE", False
        ):
            with pytest.raises(ModelLoadError) as exc_info:
                Local_Chat_Client(
                    backend=LocalModelBackend.LLAMA_CPP,
                    model_path="./models/test.gguf",
                )
            assert "インストールされていません" in exc_info.value.user_message

    def test_ollama_connection_error_raises_model_load_error(self):
        """Ollamaサーバー接続失敗時にModelLoadErrorが発生することを確認。"""
        import requests

        with patch(
            "llm_chat_app.clients.local_client.REQUESTS_AVAILABLE", True
        ), patch("llm_chat_app.clients.local_client.requests") as mock_requests:
            mock_requests.get.side_effect = (
                requests.exceptions.ConnectionError("Connection refused")
            )
            mock_requests.exceptions = requests.exceptions

            with pytest.raises(ModelLoadError) as exc_info:
                Local_Chat_Client(
                    backend=LocalModelBackend.OLLAMA,
                    model_path="llama2",
                )
            assert "接続できません" in exc_info.value.user_message

    def test_ollama_requests_not_installed_raises_model_load_error(self):
        """requests未インストール時にModelLoadErrorが発生することを確認。"""
        with patch(
            "llm_chat_app.clients.local_client.REQUESTS_AVAILABLE", False
        ):
            with pytest.raises(ModelLoadError) as exc_info:
                Local_Chat_Client(
                    backend=LocalModelBackend.OLLAMA,
                    model_path="llama2",
                )
            assert "インストールされていません" in exc_info.value.user_message


class TestLocalChatClientFormatPrompt:
    """_format_prompt()メソッドのテスト。"""

    def test_format_user_message(self):
        """ユーザーメッセージが[INST]タグで囲まれることを確認。"""
        client, _ = _create_llama_cpp_client_with_mock()
        messages = [
            Message(role="user", content="こんにちは", timestamp=time.time())
        ]
        result = client._format_prompt(messages)
        assert "[INST]" in result
        assert "こんにちは" in result
        assert "[/INST]" in result

    def test_format_system_message(self):
        """システムメッセージが<<SYS>>タグで囲まれることを確認。"""
        client, _ = _create_llama_cpp_client_with_mock()
        messages = [
            Message(
                role="system",
                content="あなたはAIアシスタントです。",
                timestamp=time.time(),
            ),
            Message(role="user", content="こんにちは", timestamp=time.time()),
        ]
        result = client._format_prompt(messages)
        assert "<<SYS>>" in result
        assert "あなたはAIアシスタントです。" in result
        assert "<</SYS>>" in result

    def test_format_multi_turn_conversation(self):
        """複数ターンの会話が正しくフォーマットされることを確認。"""
        client, _ = _create_llama_cpp_client_with_mock()
        messages = [
            Message(role="user", content="質問1", timestamp=time.time()),
            Message(role="assistant", content="回答1", timestamp=time.time()),
            Message(role="user", content="質問2", timestamp=time.time()),
        ]
        result = client._format_prompt(messages)
        assert result.count("[INST]") == 2
        assert "質問1" in result
        assert "回答1" in result
        assert "質問2" in result


class TestLocalChatClientSendMessage:
    """send_message()メソッドのテスト。"""

    def test_send_message_non_streaming(self):
        """非ストリーミングでメッセージ送信が成功することを確認。"""
        client, mock_model = _create_llama_cpp_client_with_mock()
        mock_model.create_completion.return_value = {
            "choices": [{"text": "こんにちは！お元気ですか？"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 8},
        }

        messages = [
            Message(role="user", content="こんにちは", timestamp=time.time())
        ]
        response = client.send_message(messages, stream=False)

        assert isinstance(response, LLMResponse)
        assert "こんにちは" in response.content
        assert response.response_time > 0
        assert response.usage is not None

    def test_send_message_streaming(self):
        """ストリーミングでメッセージ送信とon_tokenコールバックが動作することを確認。"""
        client, mock_model = _create_llama_cpp_client_with_mock()

        # ストリーミングレスポンスのモック
        stream_chunks = [
            {"choices": [{"text": "こん"}]},
            {"choices": [{"text": "にちは"}]},
            {"choices": [{"text": "！"}]},
        ]
        mock_model.create_completion.return_value = iter(stream_chunks)

        messages = [
            Message(role="user", content="挨拶して", timestamp=time.time())
        ]
        received_tokens = []
        response = client.send_message(
            messages, stream=True, on_token=lambda t: received_tokens.append(t)
        )

        assert isinstance(response, LLMResponse)
        assert response.content == "こんにちは！"
        assert received_tokens == ["こん", "にちは", "！"]
        assert response.response_time > 0

    def test_send_message_measures_tokens_per_second(self):
        """推論速度（tokens/second）が計測されることを確認。"""
        client, mock_model = _create_llama_cpp_client_with_mock()

        stream_chunks = [
            {"choices": [{"text": "token1 "}]},
            {"choices": [{"text": "token2 "}]},
            {"choices": [{"text": "token3"}]},
        ]
        mock_model.create_completion.return_value = iter(stream_chunks)

        messages = [
            Message(role="user", content="テスト", timestamp=time.time())
        ]
        client.send_message(messages, stream=True)

        # tokens_per_secondが計測されている
        assert client._last_tokens_per_second is not None
        assert client._last_tokens_per_second >= 0

    def test_model_not_initialized_raises_error(self):
        """モデル未初期化状態でModelLoadErrorが発生することを確認。"""
        client, _ = _create_llama_cpp_client_with_mock()

        # モデルを明示的にNoneに設定
        client._model = None

        messages = [
            Message(role="user", content="テスト", timestamp=time.time())
        ]
        with pytest.raises(ModelLoadError) as exc_info:
            client.send_message(messages, stream=False)
        assert "初期化されていません" in exc_info.value.user_message


class TestLocalChatClientGetModelInfo:
    """get_model_info()メソッドのテスト。"""

    def test_get_model_info_returns_expected_keys(self):
        """get_model_info()が必要なキーを含む辞書を返すことを確認。"""
        mock_llama_cls = MagicMock()
        mock_llama_cls.return_value = MagicMock()

        with patch(
            "llm_chat_app.clients.local_client.LLAMA_CPP_AVAILABLE", True
        ), patch("os.path.isfile", return_value=True), patch(
            "llm_chat_app.clients.local_client.Llama",
            mock_llama_cls,
            create=True,
        ):
            client = Local_Chat_Client(
                backend=LocalModelBackend.LLAMA_CPP,
                model_path="./models/test-model.gguf",
                n_ctx=4096,
                n_gpu_layers=10,
                temperature=0.5,
                max_tokens=1000,
            )

        info = client.get_model_info()

        assert info["backend"] == "llama_cpp"
        assert info["model"] == "test-model.gguf"
        assert info["model_path"] == "./models/test-model.gguf"
        assert info["n_ctx"] == 4096
        assert info["n_gpu_layers"] == 10
        assert info["temperature"] == 0.5
        assert info["max_tokens"] == 1000

    def test_get_model_info_includes_tokens_per_second_after_generation(self):
        """推論後にtokens_per_secondが含まれることを確認。"""
        client, _ = _create_llama_cpp_client_with_mock()

        # 推論速度を設定
        client._last_tokens_per_second = 15.3

        info = client.get_model_info()
        assert "tokens_per_second" in info
        assert info["tokens_per_second"] == 15.3


class TestLocalChatClientMemoryError:
    """メモリエラーのハンドリングテスト。"""

    def test_memory_error_during_model_load_raises_model_load_error(self):
        """モデルロード時のMemoryErrorがModelLoadErrorに変換されることを確認。"""
        mock_llama_cls = MagicMock()
        mock_llama_cls.side_effect = MemoryError("Out of memory")

        with patch(
            "llm_chat_app.clients.local_client.LLAMA_CPP_AVAILABLE", True
        ), patch("os.path.isfile", return_value=True), patch(
            "llm_chat_app.clients.local_client.Llama",
            mock_llama_cls,
            create=True,
        ):
            with pytest.raises(ModelLoadError) as exc_info:
                Local_Chat_Client(
                    backend=LocalModelBackend.LLAMA_CPP,
                    model_path="./models/large-model.gguf",
                )
            assert "メモリ不足" in exc_info.value.user_message

    def test_os_error_during_model_load_raises_model_load_error(self):
        """モデルロード時のOSErrorがModelLoadErrorに変換されることを確認。"""
        mock_llama_cls = MagicMock()
        mock_llama_cls.side_effect = OSError("Insufficient memory")

        with patch(
            "llm_chat_app.clients.local_client.LLAMA_CPP_AVAILABLE", True
        ), patch("os.path.isfile", return_value=True), patch(
            "llm_chat_app.clients.local_client.Llama",
            mock_llama_cls,
            create=True,
        ):
            with pytest.raises(ModelLoadError) as exc_info:
                Local_Chat_Client(
                    backend=LocalModelBackend.LLAMA_CPP,
                    model_path="./models/large-model.gguf",
                )
            assert "メモリ不足" in exc_info.value.user_message
