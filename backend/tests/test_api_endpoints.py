"""FastAPI TestClientによる各エンドポイントの統合テスト。

モックされたサービスを使用して、全APIエンドポイントの
リクエスト/レスポンスの正当性を検証する。
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.dependencies import (
    get_llm_service,
    get_rag_service,
    get_session_service,
    get_stats_service,
)
from backend.app.main import app
from backend.app.schemas.history import SessionSummary
from backend.app.schemas.models import ModelInfo
from backend.app.schemas.rag import DocumentMetadata
from backend.app.schemas.stats import (
    CumulativeStats,
    ModelStats,
    TimelineBucket,
)


# --- モックサービスのファクトリ ---


def create_mock_llm_service():
    """モックLLMServiceを生成する。"""
    mock = MagicMock()
    mock.current_model = "gpt-3.5-turbo"
    mock.get_available_models.return_value = [
        ModelInfo(
            name="gpt-3.5-turbo",
            provider="openai",
            status="available",
            parameters={"temperature": 0.7, "max_tokens": 2048},
        ),
        ModelInfo(
            name="gpt-4",
            provider="openai",
            status="available",
            parameters={"temperature": 0.7, "max_tokens": 2048},
        ),
    ]
    mock.switch_model.return_value = ModelInfo(
        name="gpt-4",
        provider="openai",
        status="available",
        parameters={"temperature": 0.7, "max_tokens": 2048},
    )
    return mock


def create_mock_session_service():
    """モックSessionServiceを生成する。"""
    mock = MagicMock()
    mock.list_sessions.return_value = [
        SessionSummary(
            session_id="session-1",
            created_at=1704067200.0,
            updated_at=1704067200.0,
            message_count=3,
            model_name="gpt-4",
            preview="テストメッセージ",
        ),
    ]
    mock.search_sessions.return_value = [
        SessionSummary(
            session_id="session-1",
            created_at=1704067200.0,
            updated_at=1704067200.0,
            message_count=3,
            model_name="gpt-4",
            preview="テストメッセージ",
        ),
    ]

    # create_sessionのモック
    from llm_chat_app.models import Conversation

    mock_conversation = MagicMock(spec=Conversation)
    mock_conversation.session_id = "new-session-id"
    mock_conversation.messages = []
    mock_conversation.created_at = 1704067200.0
    mock_conversation.updated_at = 1704067200.0
    mock_conversation.model_name = "gpt-4"
    mock_conversation.total_tokens = 0
    mock.create_session.return_value = mock_conversation

    mock.delete_session.return_value = None
    return mock


def create_mock_stats_service():
    """モックStatsServiceを生成する。"""
    mock = MagicMock()
    mock.get_cumulative_stats.return_value = CumulativeStats(
        total_requests=100,
        total_tokens=50000,
        average_response_time=1.5,
        estimated_cost=0.1,
    )
    mock.get_stats_by_model.return_value = [
        ModelStats(
            model_name="gpt-4",
            request_count=60,
            token_count=30000,
            average_response_time=2.0,
        ),
        ModelStats(
            model_name="gpt-3.5-turbo",
            request_count=40,
            token_count=20000,
            average_response_time=0.8,
        ),
    ]
    mock.get_timeline_stats.return_value = [
        TimelineBucket(
            period="2024-01-01",
            request_count=10,
            token_count=5000,
        ),
        TimelineBucket(
            period="2024-01-02",
            request_count=15,
            token_count=7500,
        ),
    ]
    return mock


def create_mock_rag_service():
    """モックRAGServiceを生成する。"""
    mock = MagicMock()
    mock.list_documents.return_value = [
        DocumentMetadata(
            document_id="doc-1",
            filename="test.pdf",
            content_type="application/pdf",
            chunk_count=5,
            uploaded_at=1704067200.0,
            file_size=1024,
        ),
    ]
    mock.ingest_document.return_value = DocumentMetadata(
        document_id="doc-new",
        filename="uploaded.txt",
        content_type="text/plain",
        chunk_count=3,
        uploaded_at=time.time(),
        file_size=256,
    )
    mock.delete_document.return_value = None
    return mock


# --- テストフィクスチャ ---


@pytest.fixture
def mock_llm_service():
    return create_mock_llm_service()


@pytest.fixture
def mock_session_service():
    return create_mock_session_service()


@pytest.fixture
def mock_stats_service():
    return create_mock_stats_service()


@pytest.fixture
def mock_rag_service():
    return create_mock_rag_service()


@pytest.fixture
def client(mock_llm_service, mock_session_service, mock_stats_service, mock_rag_service):
    """モックサービスを注入したTestClientを提供する。"""
    app.dependency_overrides[get_llm_service] = lambda: mock_llm_service
    app.dependency_overrides[get_session_service] = lambda: mock_session_service
    app.dependency_overrides[get_stats_service] = lambda: mock_stats_service
    app.dependency_overrides[get_rag_service] = lambda: mock_rag_service

    with TestClient(app) as c:
        yield c

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()


# --- モデルAPIテスト ---


class TestModelsAPI:
    """GET /api/models, POST /api/models/switch のテスト。"""

    def test_get_models(self, client, mock_llm_service):
        """GET /api/models がモデル一覧を返す。"""
        response = client.get("/api/models")

        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "current_model" in data
        assert data["current_model"] == "gpt-3.5-turbo"
        assert len(data["models"]) == 2
        assert data["models"][0]["name"] == "gpt-3.5-turbo"

    def test_switch_model_success(self, client, mock_llm_service):
        """POST /api/models/switch が正常にモデルを切り替える。"""
        response = client.post(
            "/api/models/switch",
            json={"model": "gpt-4", "provider": "openai"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["model"] == "gpt-4"
        mock_llm_service.switch_model.assert_called_once_with(
            model_name="gpt-4", provider="openai"
        )

    def test_switch_model_invalid(self, client, mock_llm_service):
        """POST /api/models/switch で無効モデル指定時に400を返す。"""
        mock_llm_service.switch_model.side_effect = ValueError(
            "未対応のプロバイダー: invalid"
        )

        response = client.post(
            "/api/models/switch",
            json={"model": "invalid-model", "provider": "invalid"},
        )

        assert response.status_code == 400


# --- 会話履歴APIテスト ---


class TestHistoryAPI:
    """会話履歴エンドポイントのテスト。"""

    def test_list_sessions(self, client, mock_session_service):
        """GET /api/history/sessions がセッション一覧を返す。"""
        response = client.get("/api/history/sessions")

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["session_id"] == "session-1"

    def test_create_session(self, client, mock_session_service):
        """POST /api/history/sessions が新規セッションを作成する。"""
        response = client.post("/api/history/sessions?model_name=gpt-4")

        assert response.status_code == 201
        data = response.json()
        assert data["session_id"] == "new-session-id"
        assert data["model_name"] == "gpt-4"
        assert data["messages"] == []

    def test_delete_session(self, client, mock_session_service):
        """DELETE /api/history/sessions/{id} がセッションを削除する。"""
        response = client.delete("/api/history/sessions/session-1")

        assert response.status_code == 204
        mock_session_service.delete_session.assert_called_once_with("session-1")

    def test_delete_session_not_found(self, client, mock_session_service):
        """DELETE /api/history/sessions/{id} で存在しないセッションに404を返す。"""
        mock_session_service.delete_session.side_effect = FileNotFoundError(
            "セッションが見つかりません"
        )

        response = client.delete("/api/history/sessions/nonexistent")

        assert response.status_code == 404

    def test_search_sessions(self, client, mock_session_service):
        """GET /api/history/search がキーワードで検索結果を返す。"""
        response = client.get("/api/history/search?keyword=テスト")

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert len(data["sessions"]) == 1
        mock_session_service.search_sessions.assert_called_once_with("テスト")


# --- 統計APIテスト ---


class TestStatsAPI:
    """統計エンドポイントのテスト。"""

    def test_get_cumulative_stats(self, client, mock_stats_service):
        """GET /api/stats が累積統計を返す。"""
        response = client.get("/api/stats")

        assert response.status_code == 200
        data = response.json()
        assert "stats" in data
        assert data["stats"]["total_requests"] == 100
        assert data["stats"]["total_tokens"] == 50000
        assert data["stats"]["average_response_time"] == 1.5
        assert data["stats"]["estimated_cost"] == 0.1

    def test_get_stats_by_model(self, client, mock_stats_service):
        """GET /api/stats/by-model がモデル別統計を返す。"""
        response = client.get("/api/stats/by-model")

        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) == 2
        assert data["models"][0]["model_name"] == "gpt-4"
        assert data["models"][0]["request_count"] == 60

    def test_get_stats_timeline(self, client, mock_stats_service):
        """GET /api/stats/timeline が時系列統計を返す。"""
        response = client.get("/api/stats/timeline?period=daily")

        assert response.status_code == 200
        data = response.json()
        assert "timeline" in data
        assert "period" in data
        assert data["period"] == "daily"
        assert len(data["timeline"]) == 2
        assert data["timeline"][0]["period"] == "2024-01-01"

    def test_get_stats_timeline_invalid_period(self, client, mock_stats_service):
        """GET /api/stats/timeline で無効なperiodに400を返す。"""
        mock_stats_service.get_timeline_stats.side_effect = ValueError(
            "Invalid period: yearly"
        )

        response = client.get("/api/stats/timeline?period=yearly")

        assert response.status_code == 400


# --- RAG APIテスト ---


class TestRAGAPI:
    """RAGドキュメント管理エンドポイントのテスト。"""

    def test_list_documents(self, client, mock_rag_service):
        """GET /api/rag/documents がドキュメント一覧を返す。"""
        response = client.get("/api/rag/documents")

        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert len(data["documents"]) == 1
        assert data["documents"][0]["document_id"] == "doc-1"
        assert data["documents"][0]["filename"] == "test.pdf"

    def test_upload_document(self, client, mock_rag_service):
        """POST /api/rag/documents/upload がドキュメントをアップロードする。"""
        response = client.post(
            "/api/rag/documents/upload",
            files={"file": ("uploaded.txt", b"test content", "text/plain")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["document"]["document_id"] == "doc-new"
        assert data["document"]["filename"] == "uploaded.txt"
        mock_rag_service.ingest_document.assert_called_once()

    def test_upload_document_unsupported_format(self, client, mock_rag_service):
        """POST /api/rag/documents/upload でサポート外形式に415を返す。"""
        from backend.app.rag.document_loader import UnsupportedFormatError

        mock_rag_service.ingest_document.side_effect = UnsupportedFormatError(
            content_type="image/png",
            supported_formats=["application/pdf", "text/plain", "text/markdown"],
        )

        response = client.post(
            "/api/rag/documents/upload",
            files={"file": ("image.png", b"\x89PNG", "image/png")},
        )

        assert response.status_code == 415

    def test_upload_document_embedding_unavailable(self, client, mock_rag_service):
        """POST /api/rag/documents/upload で埋め込みサービス利用不可時に503を返す。"""
        mock_rag_service.ingest_document.side_effect = RuntimeError(
            "埋め込みモデルが利用できません"
        )

        response = client.post(
            "/api/rag/documents/upload",
            files={"file": ("test.txt", b"content", "text/plain")},
        )

        assert response.status_code == 503

    def test_delete_document(self, client, mock_rag_service):
        """DELETE /api/rag/documents/{id} がドキュメントを削除する。"""
        response = client.delete("/api/rag/documents/doc-1")

        assert response.status_code == 204
        mock_rag_service.delete_document.assert_called_once_with("doc-1")

    def test_delete_document_not_found(self, client, mock_rag_service):
        """DELETE /api/rag/documents/{id} で存在しないドキュメントに404を返す。"""
        mock_rag_service.delete_document.side_effect = ValueError(
            "ドキュメントが見つかりません"
        )

        response = client.delete("/api/rag/documents/nonexistent")

        assert response.status_code == 404


# --- ヘルスチェックテスト ---


class TestHealthEndpoints:
    """ヘルスチェックエンドポイントのテスト。"""

    def test_root(self, client):
        """GET / がステータス情報を返す。"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "version" in data

    def test_health(self, client):
        """GET /health がhealthyを返す。"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
