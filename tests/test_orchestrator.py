"""ChatOrchestratorのユニットテスト。

send_message、clear_history、save_history、load_history、
get_model_info、get_stats、_update_stats、エラー時のストリーミング復旧を検証する。
"""

from __future__ import annotations

import io
import time
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from llm_chat_app.core.history import History_Manager
from llm_chat_app.core.orchestrator import ChatOrchestrator
from llm_chat_app.core.stream import Stream_Handler
from llm_chat_app.models import LLMResponse, Message


class FakeLLMClient:
    """テスト用のフェイクLLMクライアント。"""

    def __init__(
        self,
        response_content: str = "こんにちは！",
        usage: Optional[Dict[str, int]] = None,
        response_time: float = 0.5,
        should_raise: Optional[Exception] = None,
    ) -> None:
        self.response_content = response_content
        self.usage = usage or {"prompt_tokens": 10, "completion_tokens": 20}
        self.response_time = response_time
        self.should_raise = should_raise
        self.last_messages: List[Message] = []

    def send_message(
        self,
        messages: List[Message],
        stream: bool = False,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> LLMResponse:
        """メッセージを送信してフェイクレスポンスを返す。"""
        if self.should_raise:
            raise self.should_raise

        self.last_messages = messages

        # ストリーミングモードの場合、トークンごとにコールバックを呼び出す
        if stream and on_token:
            for char in self.response_content:
                on_token(char)

        return LLMResponse(
            content=self.response_content,
            model="test-model",
            usage=self.usage,
            response_time=self.response_time,
        )

    def get_model_info(self) -> Dict[str, Any]:
        """テスト用モデル情報を返す。"""
        return {
            "model": "test-model",
            "provider": "test",
            "temperature": 0.7,
            "max_tokens": 2000,
        }


@pytest.fixture
def output_stream() -> io.StringIO:
    """テスト用出力ストリーム。"""
    return io.StringIO()


@pytest.fixture
def orchestrator(output_stream: io.StringIO) -> ChatOrchestrator:
    """テスト用ChatOrchestratorを生成する。"""
    client = FakeLLMClient()
    history_manager = History_Manager(max_tokens=4000)
    stream_handler = Stream_Handler(output_stream=output_stream)
    return ChatOrchestrator(
        client=client,
        history_manager=history_manager,
        stream_handler=stream_handler,
    )


class TestSendMessage:
    """send_message()のテスト。"""

    def test_send_message_returns_response_content(
        self, orchestrator: ChatOrchestrator
    ) -> None:
        """レスポンス内容が正しく返されることを確認。"""
        result = orchestrator.send_message("テストメッセージ")
        assert result == "こんにちは！"

    def test_send_message_adds_user_message_to_history(
        self, orchestrator: ChatOrchestrator
    ) -> None:
        """ユーザーメッセージが履歴に追加されることを確認。"""
        orchestrator.send_message("テスト入力")
        messages = orchestrator.history_manager.get_messages()
        # ユーザーメッセージとアシスタントメッセージが追加される
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "テスト入力"

    def test_send_message_adds_assistant_message_to_history(
        self, orchestrator: ChatOrchestrator
    ) -> None:
        """アシスタントメッセージが履歴に追加されることを確認。"""
        orchestrator.send_message("テスト入力")
        messages = orchestrator.history_manager.get_messages()
        assert messages[1].role == "assistant"
        assert messages[1].content == "こんにちは！"

    def test_send_message_updates_stats(
        self, orchestrator: ChatOrchestrator
    ) -> None:
        """統計情報が更新されることを確認。"""
        orchestrator.send_message("テスト")
        stats = orchestrator.get_stats()
        assert stats["total_requests"] == 1
        assert stats["total_tokens"] == 30  # 10 + 20
        assert stats["total_time"] == 0.5

    def test_send_message_streams_response(
        self, orchestrator: ChatOrchestrator, output_stream: io.StringIO
    ) -> None:
        """ストリーミングでレスポンスが表示されることを確認。"""
        orchestrator.send_message("テスト")
        output = output_stream.getvalue()
        # ストリーミングプレフィックスとレスポンスが含まれる
        assert "Assistant: " in output
        assert "こんにちは！" in output

    def test_send_message_error_recovers_streaming_state(
        self, output_stream: io.StringIO
    ) -> None:
        """エラー発生時にストリーミング状態が復旧されることを確認。"""
        error_client = FakeLLMClient(should_raise=RuntimeError("テストエラー"))
        history_manager = History_Manager()
        stream_handler = Stream_Handler(output_stream=output_stream)
        orch = ChatOrchestrator(
            client=error_client,
            history_manager=history_manager,
            stream_handler=stream_handler,
        )

        with pytest.raises(RuntimeError, match="テストエラー"):
            orch.send_message("テスト")

        # ストリーミング状態が復旧されている
        assert stream_handler.is_streaming is False

    def test_send_message_passes_history_to_client(
        self, output_stream: io.StringIO
    ) -> None:
        """LLMクライアントに会話履歴が渡されることを確認。"""
        client = FakeLLMClient()
        history_manager = History_Manager()
        stream_handler = Stream_Handler(output_stream=output_stream)
        orch = ChatOrchestrator(
            client=client,
            history_manager=history_manager,
            stream_handler=stream_handler,
        )

        orch.send_message("最初のメッセージ")
        orch.send_message("2番目のメッセージ")

        # 2回目の呼び出し時に最初のメッセージとレスポンスも含まれている
        assert len(client.last_messages) == 3  # user1, assistant1, user2


class TestClearHistory:
    """clear_history()のテスト。"""

    def test_clear_history_removes_all_messages(
        self, orchestrator: ChatOrchestrator
    ) -> None:
        """履歴クリアですべてのメッセージが削除されることを確認。"""
        orchestrator.send_message("テスト")
        assert len(orchestrator.history_manager.get_messages()) > 0

        orchestrator.clear_history()
        assert len(orchestrator.history_manager.get_messages()) == 0


class TestSaveAndLoadHistory:
    """save_history()とload_history()のテスト。"""

    def test_save_and_load_history(
        self, orchestrator: ChatOrchestrator, tmp_path
    ) -> None:
        """保存と読み込みのラウンドトリップを確認。"""
        orchestrator.send_message("テスト保存")
        filepath = str(tmp_path / "history.json")

        orchestrator.save_history(filepath)
        orchestrator.clear_history()
        assert len(orchestrator.history_manager.get_messages()) == 0

        orchestrator.load_history(filepath)
        messages = orchestrator.history_manager.get_messages()
        assert len(messages) == 2
        assert messages[0].content == "テスト保存"
        assert messages[1].content == "こんにちは！"


class TestGetModelInfo:
    """get_model_info()のテスト。"""

    def test_get_model_info_returns_client_info(
        self, orchestrator: ChatOrchestrator
    ) -> None:
        """クライアントのモデル情報が返されることを確認。"""
        info = orchestrator.get_model_info()
        assert info["model"] == "test-model"
        assert info["provider"] == "test"


class TestGetStats:
    """get_stats()のテスト。"""

    def test_initial_stats_are_zero(
        self, orchestrator: ChatOrchestrator
    ) -> None:
        """初期状態の統計がゼロであることを確認。"""
        stats = orchestrator.get_stats()
        assert stats["total_requests"] == 0
        assert stats["total_tokens"] == 0
        assert stats["total_time"] == 0.0
        assert stats["average_response_time"] == 0.0
        assert stats["estimated_cost"] == 0.0

    def test_stats_accumulate_over_multiple_requests(
        self, orchestrator: ChatOrchestrator
    ) -> None:
        """複数リクエストで統計が累積されることを確認。"""
        orchestrator.send_message("テスト1")
        orchestrator.send_message("テスト2")
        stats = orchestrator.get_stats()
        assert stats["total_requests"] == 2
        assert stats["total_tokens"] == 60  # 30 * 2
        assert stats["total_time"] == 1.0  # 0.5 * 2
        assert stats["average_response_time"] == 0.5

    def test_stats_calculates_estimated_cost(
        self, orchestrator: ChatOrchestrator
    ) -> None:
        """推定コストが正しく計算されることを確認。"""
        orchestrator.send_message("テスト")
        stats = orchestrator.get_stats()
        # (10 * 0.00003) + (20 * 0.00006) = 0.0003 + 0.0012 = 0.0015
        expected_cost = (10 * 0.00003) + (20 * 0.00006)
        assert abs(stats["estimated_cost"] - expected_cost) < 1e-10


class TestUpdateStats:
    """_update_stats()のテスト。"""

    def test_update_stats_with_none_usage(
        self, orchestrator: ChatOrchestrator
    ) -> None:
        """usageがNoneの場合でもエラーにならないことを確認。"""
        response = LLMResponse(
            content="テスト",
            model="test-model",
            usage=None,
            response_time=1.0,
        )
        orchestrator._update_stats(response)
        stats = orchestrator.get_stats()
        assert stats["total_requests"] == 1
        assert stats["total_tokens"] == 0
        assert stats["total_time"] == 1.0
        assert stats["estimated_cost"] == 0.0
