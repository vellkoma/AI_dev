"""RAGドキュメント管理APIルーターの単体テスト。

POST /api/rag/documents/upload, GET /api/rag/documents,
DELETE /api/rag/documents/{document_id} の正当性を検証する。
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.dependencies import get_rag_service
from backend.app.rag.document_loader import UnsupportedFormatError
from backend.app.routers.rag import router
from backend.app.schemas.rag import DocumentMetadata


def _create_test_app(service) -> FastAPI:
    """テスト用のFastAPIアプリを作成する。"""
    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_rag_service] = lambda: service
    return test_app


@pytest.fixture
def mock_rag_service():
    """モックRAGサービスインスタンスを提供する。"""
    return MagicMock()


@pytest.fixture
def client(mock_rag_service):
    """テスト用のFastAPI TestClientを提供する。"""
    test_app = _create_test_app(mock_rag_service)
    return TestClient(test_app)


@pytest.fixture
def sample_metadata():
    """テスト用のDocumentMetadataを提供する。"""
    return DocumentMetadata(
        document_id="test-doc-id-123",
        filename="test.txt",
        content_type="text/plain",
        chunk_count=3,
        uploaded_at=1700000000.0,
        file_size=1024,
    )


class TestUploadDocument:
    """POST /api/rag/documents/upload のテスト。"""

    def test_upload_success(self, client, mock_rag_service, sample_metadata):
        """正常なファイルアップロードが成功する。"""
        mock_rag_service.ingest_document.return_value = sample_metadata

        response = client.post(
            "/api/rag/documents/upload",
            files={"file": ("test.txt", b"Hello world", "text/plain")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["document"]["document_id"] == "test-doc-id-123"
        assert data["document"]["filename"] == "test.txt"
        assert "正常にアップロード" in data["message"]

    def test_upload_calls_ingest_document(
        self, client, mock_rag_service, sample_metadata
    ):
        """アップロード時にingest_documentが正しい引数で呼ばれる。"""
        mock_rag_service.ingest_document.return_value = sample_metadata

        client.post(
            "/api/rag/documents/upload",
            files={"file": ("test.txt", b"content data", "text/plain")},
        )

        mock_rag_service.ingest_document.assert_called_once()
        call_kwargs = mock_rag_service.ingest_document.call_args
        assert call_kwargs.kwargs["file_content"] == b"content data"
        assert call_kwargs.kwargs["filename"] == "test.txt"
        assert call_kwargs.kwargs["content_type"] == "text/plain"

    def test_upload_unsupported_format_returns_415(
        self, client, mock_rag_service
    ):
        """サポート外形式でHTTP 415を返す。"""
        mock_rag_service.ingest_document.side_effect = UnsupportedFormatError(
            content_type="application/zip",
            supported_formats=[
                "application/pdf",
                "text/plain",
                "text/markdown",
            ],
        )

        response = client.post(
            "/api/rag/documents/upload",
            files={"file": ("archive.zip", b"PK\x03\x04", "application/zip")},
        )

        assert response.status_code == 415
        data = response.json()
        assert "supported_formats" in data["detail"]
        assert "application/pdf" in data["detail"]["supported_formats"]

    def test_upload_embedding_unavailable_returns_503(
        self, client, mock_rag_service
    ):
        """埋め込みモデル利用不可でHTTP 503を返す。"""
        mock_rag_service.ingest_document.side_effect = RuntimeError(
            "埋め込みモデルが利用できません"
        )

        response = client.post(
            "/api/rag/documents/upload",
            files={"file": ("test.txt", b"Hello", "text/plain")},
        )

        assert response.status_code == 503
        data = response.json()
        assert "埋め込みサービスが利用できません" in data["detail"]["error"]


class TestListDocuments:
    """GET /api/rag/documents のテスト。"""

    def test_list_returns_documents(
        self, client, mock_rag_service, sample_metadata
    ):
        """ドキュメント一覧を正しく返す。"""
        mock_rag_service.list_documents.return_value = [sample_metadata]

        response = client.get("/api/rag/documents")

        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert len(data["documents"]) == 1
        assert data["documents"][0]["document_id"] == "test-doc-id-123"
        assert data["documents"][0]["filename"] == "test.txt"

    def test_list_empty_returns_empty_list(self, client, mock_rag_service):
        """ドキュメントがない場合は空リストを返す。"""
        mock_rag_service.list_documents.return_value = []

        response = client.get("/api/rag/documents")

        assert response.status_code == 200
        data = response.json()
        assert data["documents"] == []


class TestDeleteDocument:
    """DELETE /api/rag/documents/{document_id} のテスト。"""

    def test_delete_success_returns_204(self, client, mock_rag_service):
        """正常な削除でHTTP 204を返す。"""
        mock_rag_service.delete_document.return_value = None

        response = client.delete("/api/rag/documents/test-doc-id-123")

        assert response.status_code == 204
        mock_rag_service.delete_document.assert_called_once_with(
            "test-doc-id-123"
        )

    def test_delete_not_found_returns_404(self, client, mock_rag_service):
        """存在しないドキュメントでHTTP 404を返す。"""
        mock_rag_service.delete_document.side_effect = ValueError(
            "ドキュメントが見つかりません"
        )

        response = client.delete("/api/rag/documents/nonexistent-id")

        assert response.status_code == 404
        data = response.json()
        assert "ドキュメントが見つかりません" in data["detail"]["error"]
        assert data["detail"]["document_id"] == "nonexistent-id"
