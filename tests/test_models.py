"""
データモデルのユニットテスト

Message, LLMResponse, Conversation, AppConfigデータクラスの
基本動作とシリアライズ/デシリアライズを検証します。
"""

from __future__ import annotations

import time

from llm_chat_app.models import AppConfig, Conversation, LLMResponse, Message


class TestMessage:
    """Messageデータクラスのテスト"""

    def test_create_message(self) -> None:
        """メッセージの基本的な作成を検証する"""
        msg = Message(role="user", content="こんにちは", timestamp=1000.0)
        assert msg.role == "user"
        assert msg.content == "こんにちは"
        assert msg.timestamp == 1000.0

    def test_to_dict(self) -> None:
        """to_dict()がすべてのフィールドを含む辞書を返すことを検証する"""
        msg = Message(role="assistant", content="お手伝いします", timestamp=1234.5)
        result = msg.to_dict()
        assert result == {
            "role": "assistant",
            "content": "お手伝いします",
            "timestamp": 1234.5,
        }

    def test_from_dict(self) -> None:
        """from_dict()が辞書からMessageを正しく復元することを検証する"""
        data = {"role": "system", "content": "あなたはAIアシスタントです", "timestamp": 999.0}
        msg = Message.from_dict(data)
        assert msg.role == "system"
        assert msg.content == "あなたはAIアシスタントです"
        assert msg.timestamp == 999.0

    def test_roundtrip(self) -> None:
        """to_dict() → from_dict() のラウンドトリップを検証する"""
        original = Message(role="user", content="テストメッセージ", timestamp=5000.0)
        restored = Message.from_dict(original.to_dict())
        assert restored.role == original.role
        assert restored.content == original.content
        assert restored.timestamp == original.timestamp


class TestLLMResponse:
    """LLMResponseデータクラスのテスト"""

    def test_create_response(self) -> None:
        """LLMResponseの基本的な作成を検証する"""
        resp = LLMResponse(
            content="応答テキスト",
            model="gpt-3.5-turbo",
            usage={"prompt_tokens": 10, "completion_tokens": 20},
            response_time=1.5,
        )
        assert resp.content == "応答テキスト"
        assert resp.model == "gpt-3.5-turbo"
        assert resp.usage == {"prompt_tokens": 10, "completion_tokens": 20}
        assert resp.response_time == 1.5

    def test_get_total_tokens_with_usage(self) -> None:
        """usageがある場合にget_total_tokens()が正しい合計を返すことを検証する"""
        resp = LLMResponse(
            content="テスト",
            model="gpt-4",
            usage={"prompt_tokens": 50, "completion_tokens": 100},
            response_time=2.0,
        )
        assert resp.get_total_tokens() == 150

    def test_get_total_tokens_without_usage(self) -> None:
        """usageがNoneの場合にget_total_tokens()が0を返すことを検証する"""
        resp = LLMResponse(
            content="テスト",
            model="local-model",
            usage=None,
            response_time=0.5,
        )
        assert resp.get_total_tokens() == 0

    def test_get_total_tokens_partial_usage(self) -> None:
        """usageの一部のキーが欠けている場合に0をデフォルトとして使用することを検証する"""
        resp = LLMResponse(
            content="テスト",
            model="gpt-3.5-turbo",
            usage={"prompt_tokens": 30},
            response_time=1.0,
        )
        assert resp.get_total_tokens() == 30


class TestConversation:
    """Conversationデータクラスのテスト"""

    def test_create_conversation(self) -> None:
        """Conversationの基本的な作成を検証する"""
        conv = Conversation(
            session_id="test-session-123",
            messages=[],
            created_at=1000.0,
            updated_at=1000.0,
            model_name="gpt-3.5-turbo",
            total_tokens=0,
        )
        assert conv.session_id == "test-session-123"
        assert conv.messages == []
        assert conv.model_name == "gpt-3.5-turbo"
        assert conv.total_tokens == 0

    def test_to_dict(self) -> None:
        """to_dict()が全フィールドを含む辞書を返すことを検証する"""
        msg = Message(role="user", content="テスト", timestamp=100.0)
        conv = Conversation(
            session_id="session-1",
            messages=[msg],
            created_at=100.0,
            updated_at=200.0,
            model_name="gpt-4",
            total_tokens=50,
        )
        result = conv.to_dict()
        assert result["session_id"] == "session-1"
        assert len(result["messages"]) == 1
        assert result["messages"][0]["role"] == "user"
        assert result["created_at"] == 100.0
        assert result["updated_at"] == 200.0
        assert result["model_name"] == "gpt-4"
        assert result["total_tokens"] == 50

    def test_from_dict(self) -> None:
        """from_dict()が辞書からConversationを正しく復元することを検証する"""
        data = {
            "session_id": "session-abc",
            "messages": [
                {"role": "user", "content": "質問", "timestamp": 1.0},
                {"role": "assistant", "content": "回答", "timestamp": 2.0},
            ],
            "created_at": 1.0,
            "updated_at": 2.0,
            "model_name": "claude-3",
            "total_tokens": 100,
        }
        conv = Conversation.from_dict(data)
        assert conv.session_id == "session-abc"
        assert len(conv.messages) == 2
        assert conv.messages[0].role == "user"
        assert conv.messages[1].content == "回答"
        assert conv.model_name == "claude-3"
        assert conv.total_tokens == 100

    def test_roundtrip(self) -> None:
        """to_dict() → from_dict() のラウンドトリップを検証する"""
        messages = [
            Message(role="system", content="システムプロンプト", timestamp=10.0),
            Message(role="user", content="こんにちは", timestamp=20.0),
            Message(role="assistant", content="はい、お手伝いします", timestamp=30.0),
        ]
        original = Conversation(
            session_id="roundtrip-test",
            messages=messages,
            created_at=10.0,
            updated_at=30.0,
            model_name="gemini-pro",
            total_tokens=250,
        )
        restored = Conversation.from_dict(original.to_dict())
        assert restored.session_id == original.session_id
        assert len(restored.messages) == len(original.messages)
        for orig_msg, rest_msg in zip(original.messages, restored.messages):
            assert orig_msg.role == rest_msg.role
            assert orig_msg.content == rest_msg.content
            assert orig_msg.timestamp == rest_msg.timestamp
        assert restored.created_at == original.created_at
        assert restored.updated_at == original.updated_at
        assert restored.model_name == original.model_name
        assert restored.total_tokens == original.total_tokens


class TestAppConfig:
    """AppConfigデータクラスのテスト"""

    def test_default_values(self) -> None:
        """デフォルト値が正しく設定されることを検証する"""
        config = AppConfig()
        # API設定
        assert config.api_provider is None
        assert config.api_key is None
        assert config.api_model == "gpt-3.5-turbo"
        # ローカルモデル設定
        assert config.local_backend is None
        assert config.local_model_path is None
        assert config.local_n_ctx == 2048
        assert config.local_n_gpu_layers == 0
        # 共通設定
        assert config.temperature == 0.7
        assert config.max_tokens == 2000
        assert config.history_max_tokens == 4000
        # ログ設定
        assert config.log_enabled is True
        assert config.log_level == "INFO"
        assert config.log_file == "chat.log"

    def test_custom_values(self) -> None:
        """カスタム値を指定して作成できることを検証する"""
        config = AppConfig(
            api_provider="openai",
            api_key="sk-test-key",
            api_model="gpt-4",
            local_backend="llama_cpp",
            local_model_path="./models/test.gguf",
            local_n_ctx=4096,
            local_n_gpu_layers=10,
            temperature=0.9,
            max_tokens=4000,
            history_max_tokens=8000,
            log_enabled=False,
            log_level="DEBUG",
            log_file="debug.log",
        )
        assert config.api_provider == "openai"
        assert config.api_key == "sk-test-key"
        assert config.api_model == "gpt-4"
        assert config.local_backend == "llama_cpp"
        assert config.local_model_path == "./models/test.gguf"
        assert config.local_n_ctx == 4096
        assert config.local_n_gpu_layers == 10
        assert config.temperature == 0.9
        assert config.max_tokens == 4000
        assert config.history_max_tokens == 8000
        assert config.log_enabled is False
        assert config.log_level == "DEBUG"
        assert config.log_file == "debug.log"
