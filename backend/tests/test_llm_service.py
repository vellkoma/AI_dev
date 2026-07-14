"""LLMServiceの単体テスト。

モデル切り替え、モデル一覧取得、SSEストリーミングの正当性を検証する。
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from backend.app.config import BackendConfig
from backend.app.schemas.models import ModelInfo
from backend.app.services.llm_service import LLMService
from llm_chat_app.exceptions import AuthenticationError, NetworkError, RateLimitError
from llm_chat_app.models import LLMResponse, Message


@pytest.fixture
def config():
    """テスト用のBackendConfigインスタンスを提供する。"""
    return BackendConfig(
        default_provider="openai",
        default_model="gpt-3.5-turbo",
        api_key="test-api-key",
        temperature=0.7,
        max_tokens=2000,
    )


@pytest.fixture
def config_no_key():
    """APIキーなしのBackendConfigインスタンスを提供する。"""
    return BackendConfig(
        default_provider="openai",
        default_model="gpt-3.5-turbo",
        api_key=None,
        temperature=0.7,
        max_tokens=2000,
    )


@pytest.fixture
def service(config):
    """テスト用のLLMServiceインスタンスを提供する。"""
    with patch("backend.app.services.llm_service.API_Chat_Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        svc = LLMService(config)
        return svc


@pytest.fixture
def service_no_key(config_no_key):
    """APIキーなしのLLMServiceインスタンスを提供する。"""
    with patch.dict("os.environ", {}, clear=True):
        svc = LLMService(config_no_key)
        return svc


class TestInitialization:
    """LLMService初期化のテスト。"""

    def test_初期化_APIキーあり(self, service):
        """APIキーがある場合、クライアントが正常に初期化される。"""
        assert service.is_initialized is True
        assert service.current_model == "gpt-3.5-turbo"
        assert service.current_provider == "openai"

    def test_初期化_APIキーなし(self, service_no_key):
        """APIキーがない場合、クライアントはNoneのまま。"""
        assert service_no_key.is_initialized is False
        assert service_no_key.current_model == "gpt-3.5-turbo"


class TestGetAvailableModels:
    """get_available_models() のテスト。"""

    def test_モデル一覧取得(self, service):
        """利用可能なモデル一覧を取得できる。"""
        models = service.get_available_models()
        assert len(models) == 3
        # 全てModelInfoインスタンス
        for model in models:
            assert isinstance(model, ModelInfo)
            assert model.name != ""
            assert model.provider in ("openai", "claude", "gemini")
            assert model.status in ("available", "unavailable")

    def test_モデル一覧_プロバイダー網羅(self, service):
        """3つのプロバイダーが全て含まれる。"""
        models = service.get_available_models()
        providers = {m.provider for m in models}
        assert providers == {"openai", "claude", "gemini"}


class TestSwitchModel:
    """switch_model() のテスト。"""

    def test_モデル切り替え_正常(self, config):
        """有効なモデルとプロバイダーで切り替えが成功する。"""
        with patch(
            "backend.app.services.llm_service.API_Chat_Client"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            svc = LLMService(config)

            result = svc.switch_model("gpt-4", "openai")

            assert result.name == "gpt-4"
            assert result.provider == "openai"
            assert result.status == "available"
            assert svc.current_model == "gpt-4"
            assert svc.current_provider == "openai"

    def test_モデル切り替え_未対応プロバイダー(self, service):
        """未対応のプロバイダーでValueErrorが発生する。"""
        with pytest.raises(ValueError, match="未対応のプロバイダー"):
            service.switch_model("some-model", "unknown_provider")

    def test_モデル切り替え_APIキーなし(self, config_no_key):
        """APIキーがない場合RuntimeErrorが発生する。"""
        with patch.dict("os.environ", {}, clear=True):
            svc = LLMService(config_no_key)
            with pytest.raises(RuntimeError, match="APIキーが設定されていません"):
                svc.switch_model("gpt-4", "openai")


class TestStreamResponse:
    """stream_response() のテスト。"""

    @pytest.mark.asyncio
    async def test_ストリーミング_クライアント未初期化(self, service_no_key):
        """クライアント未初期化時にerrorイベントが返される。"""
        messages = [Message(role="user", content="Hello", timestamp=time.time())]
        events = []
        async for event in service_no_key.stream_response(messages):
            events.append(event)

        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert "初期化されていません" in events[0]["data"]

    @pytest.mark.asyncio
    async def test_ストリーミング_正常応答(self, config):
        """正常なストリーミングでtokenイベントとdoneイベントが返される。"""
        with patch(
            "backend.app.services.llm_service.API_Chat_Client"
        ) as mock_client_class:
            mock_client = MagicMock()

            # send_messageのモック: on_tokenコールバックを呼び出す
            def fake_send(messages, stream=False, on_token=None):
                if stream and on_token:
                    on_token("Hello")
                    on_token(" World")
                return LLMResponse(
                    content="Hello World",
                    model="gpt-3.5-turbo",
                    usage={"prompt_tokens": 10, "completion_tokens": 5},
                    response_time=0.5,
                )

            mock_client.send_message.side_effect = fake_send
            mock_client_class.return_value = mock_client

            svc = LLMService(config)
            messages = [Message(role="user", content="Hi", timestamp=time.time())]

            events = []
            async for event in svc.stream_response(messages):
                events.append(event)

            # tokenイベントとdoneイベントが含まれる
            token_events = [e for e in events if e["type"] == "token"]
            done_events = [e for e in events if e["type"] == "done"]

            assert len(token_events) == 2
            assert token_events[0]["data"] == "Hello"
            assert token_events[1]["data"] == " World"
            assert len(done_events) == 1
            assert "metadata" in done_events[0]
            assert "response_time" in done_events[0]["metadata"]
            assert "usage" in done_events[0]["metadata"]

    @pytest.mark.asyncio
    async def test_ストリーミング_認証エラー(self, config):
        """認証エラー時にerrorイベントが返される。"""
        with patch(
            "backend.app.services.llm_service.API_Chat_Client"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.send_message.side_effect = AuthenticationError()
            mock_client_class.return_value = mock_client

            svc = LLMService(config)
            messages = [Message(role="user", content="Hi", timestamp=time.time())]

            events = []
            async for event in svc.stream_response(messages):
                events.append(event)

            assert len(events) == 1
            assert events[0]["type"] == "error"
            assert "認証" in events[0]["data"]

    @pytest.mark.asyncio
    async def test_ストリーミング_ネットワークエラー(self, config):
        """ネットワークエラー時にerrorイベントが返される。"""
        with patch(
            "backend.app.services.llm_service.API_Chat_Client"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.send_message.side_effect = NetworkError()
            mock_client_class.return_value = mock_client

            svc = LLMService(config)
            messages = [Message(role="user", content="Hi", timestamp=time.time())]

            events = []
            async for event in svc.stream_response(messages):
                events.append(event)

            assert len(events) == 1
            assert events[0]["type"] == "error"
            assert "ネットワーク" in events[0]["data"]

    @pytest.mark.asyncio
    async def test_ストリーミング_RAGコンテキスト付加(self, config):
        """RAGコンテキストが提供された場合、systemメッセージが追加される。"""
        with patch(
            "backend.app.services.llm_service.API_Chat_Client"
        ) as mock_client_class:
            mock_client = MagicMock()
            captured_messages = []

            def fake_send(messages, stream=False, on_token=None):
                captured_messages.extend(messages)
                if stream and on_token:
                    on_token("OK")
                return LLMResponse(
                    content="OK",
                    model="gpt-3.5-turbo",
                    usage=None,
                    response_time=0.1,
                )

            mock_client.send_message.side_effect = fake_send
            mock_client_class.return_value = mock_client

            svc = LLMService(config)
            messages = [Message(role="user", content="質問です", timestamp=time.time())]

            events = []
            async for event in svc.stream_response(
                messages, rag_context="参考資料の内容"
            ):
                events.append(event)

            # RAG systemメッセージが先頭に追加されている
            assert len(captured_messages) == 2
            assert captured_messages[0].role == "system"
            assert "参考資料の内容" in captured_messages[0].content
