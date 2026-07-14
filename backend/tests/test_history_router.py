"""会話履歴APIルーターのユニットテスト。

GET/POST/DELETE /api/history/sessions エンドポイントと
GET /api/history/search エンドポイントを検証する。
"""

import time
import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.routers.history import router
from backend.app.schemas.history import SessionSummary
from backend.app.services.session_service import SessionService
from llm_chat_app.models import Conversation, Message


@pytest.fixture
def mock_service():
    """モックのSessionServiceを生成する。"""
    return MagicMock(spec=SessionService)


@pytest.fixture
def app(mock_service):
    """テスト用FastAPIアプリを生成する。"""
    from backend.app.dependencies import get_session_service

    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_session_service] = lambda: mock_service
    return test_app


@pytest.fixture
def client(app):
    """テスト用HTTPクライアントを生成する。"""
    return TestClient(app)


class TestListSessions:
    """GET /api/history/sessions のテスト。"""

    def test_空のセッション一覧を返す(self, client, mock_service):
        """セッションがない場合に空リストを返すことを確認。"""
        mock_service.list_sessions.return_value = []

        response = client.get("/api/history/sessions")

        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []

    def test_セッション一覧を返す(self, client, mock_service):
        """セッション一覧が正しく返されることを確認。"""
        now = time.time()
        summaries = [
            SessionSummary(
                session_id="sess-1",
                created_at=now,
                updated_at=now,
                message_count=3,
                model_name="gpt-4",
                preview="こんにちは",
            ),
            SessionSummary(
                session_id="sess-2",
                created_at=now - 100,
                updated_at=now - 50,
                message_count=1,
                model_name="gpt-3.5-turbo",
                preview="テスト",
            ),
        ]
        mock_service.list_sessions.return_value = summaries

        response = client.get("/api/history/sessions")

        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 2
        assert data["sessions"][0]["session_id"] == "sess-1"
        assert data["sessions"][1]["session_id"] == "sess-2"


class TestGetSession:
    """GET /api/history/sessions/{session_id} のテスト。"""

    def test_セッション詳細を返す(self, client, mock_service):
        """セッション詳細が正しく返されることを確認。"""
        now = time.time()
        conversation = Conversation(
            session_id="sess-1",
            messages=[
                Message(role="user", content="こんにちは", timestamp=now),
                Message(
                    role="assistant", content="はい、こんにちは！", timestamp=now + 1
                ),
            ],
            created_at=now,
            updated_at=now + 1,
            model_name="gpt-4",
            total_tokens=150,
        )
        mock_service.get_session.return_value = conversation

        response = client.get("/api/history/sessions/sess-1")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "sess-1"
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][0]["content"] == "こんにちは"
        assert data["messages"][1]["role"] == "assistant"
        assert data["model_name"] == "gpt-4"
        assert data["total_tokens"] == 150

    def test_存在しないセッションで404を返す(self, client, mock_service):
        """存在しないセッションIDの場合に404を返すことを確認。"""
        mock_service.get_session.side_effect = FileNotFoundError(
            "セッションが見つかりません"
        )

        response = client.get("/api/history/sessions/nonexistent")

        assert response.status_code == 404
        assert "セッションが見つかりません" in response.json()["detail"]


class TestCreateSession:
    """POST /api/history/sessions のテスト。"""

    def test_新しいセッションを作成する(self, client, mock_service):
        """新しいセッションが作成されることを確認。"""
        now = time.time()
        session_id = str(uuid.uuid4())
        conversation = Conversation(
            session_id=session_id,
            messages=[],
            created_at=now,
            updated_at=now,
            model_name="gpt-4",
            total_tokens=0,
        )
        mock_service.create_session.return_value = conversation

        response = client.post("/api/history/sessions?model_name=gpt-4")

        assert response.status_code == 201
        data = response.json()
        assert data["session_id"] == session_id
        assert data["messages"] == []
        assert data["model_name"] == "gpt-4"
        assert data["total_tokens"] == 0
        mock_service.create_session.assert_called_once_with(model_name="gpt-4")

    def test_モデル名なしで作成する(self, client, mock_service):
        """モデル名を指定しない場合でもセッションが作成されることを確認。"""
        now = time.time()
        conversation = Conversation(
            session_id="new-sess",
            messages=[],
            created_at=now,
            updated_at=now,
            model_name="",
            total_tokens=0,
        )
        mock_service.create_session.return_value = conversation

        response = client.post("/api/history/sessions")

        assert response.status_code == 201
        data = response.json()
        assert data["model_name"] == ""
        mock_service.create_session.assert_called_once_with(model_name="")


class TestDeleteSession:
    """DELETE /api/history/sessions/{session_id} のテスト。"""

    def test_セッションを削除する(self, client, mock_service):
        """セッションが正常に削除されることを確認。"""
        mock_service.delete_session.return_value = None

        response = client.delete("/api/history/sessions/sess-1")

        assert response.status_code == 204
        mock_service.delete_session.assert_called_once_with("sess-1")

    def test_存在しないセッションの削除で404を返す(self, client, mock_service):
        """存在しないセッションの削除で404を返すことを確認。"""
        mock_service.delete_session.side_effect = FileNotFoundError(
            "セッションが見つかりません"
        )

        response = client.delete("/api/history/sessions/nonexistent")

        assert response.status_code == 404


class TestSearchSessions:
    """GET /api/history/search のテスト。"""

    def test_キーワードで検索する(self, client, mock_service):
        """キーワード検索が正しく動作することを確認。"""
        now = time.time()
        results = [
            SessionSummary(
                session_id="sess-1",
                created_at=now,
                updated_at=now,
                message_count=2,
                model_name="gpt-4",
                preview="Pythonについて",
            ),
        ]
        mock_service.search_sessions.return_value = results

        response = client.get("/api/history/search?keyword=Python")

        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["preview"] == "Pythonについて"
        mock_service.search_sessions.assert_called_once_with("Python")

    def test_空キーワードで全セッションを返す(self, client, mock_service):
        """キーワードが空の場合に全セッションを返すことを確認。"""
        mock_service.search_sessions.return_value = []

        response = client.get("/api/history/search?keyword=")

        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []
        mock_service.search_sessions.assert_called_once_with("")

    def test_キーワード未指定で全セッションを返す(self, client, mock_service):
        """キーワードパラメータがない場合に空文字列で検索されることを確認。"""
        mock_service.search_sessions.return_value = []

        response = client.get("/api/history/search")

        assert response.status_code == 200
        mock_service.search_sessions.assert_called_once_with("")
