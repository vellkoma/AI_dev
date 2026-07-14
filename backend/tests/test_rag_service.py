"""RAGServiceのユニットテスト。

RAGServiceの各メソッド（ingest_document, search_relevant_chunks,
build_rag_context, delete_document, list_documents）の動作を検証する。
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.app.config import BackendConfig
from backend.app.schemas.rag import ChunkResult, DocumentMetadata
from backend.app.services.rag_service import RAGService


@pytest.fixture
def temp_dir():
    """一時ディレクトリを作成するフィクスチャ。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def config(temp_dir):
    """テスト用BackendConfigを作成するフィクスチャ。"""
    return BackendConfig(
        documents_dir=str(Path(temp_dir) / "documents"),
        chroma_persist_dir=str(Path(temp_dir) / "chroma"),
        embedding_model="all-MiniLM-L6-v2",
        chunk_size=500,
        chunk_overlap=50,
        rag_top_k=5,
    )


@pytest.fixture
def mock_embedding_service():
    """モックEmbeddingServiceを作成するフィクスチャ。"""
    mock = MagicMock()
    mock.compute_embeddings.return_value = [[0.1, 0.2, 0.3]]
    mock.add_chunks.return_value = None
    mock.delete_by_document_id.return_value = None
    mock.search.return_value = {
        "ids": [["doc1_chunk_0", "doc1_chunk_1"]],
        "documents": [["チャンク内容1", "チャンク内容2"]],
        "metadatas": [
            [
                {"document_id": "doc1", "chunk_index": 0, "filename": "test.txt"},
                {"document_id": "doc1", "chunk_index": 1, "filename": "test.txt"},
            ]
        ],
        "distances": [[0.1, 0.3]],
    }
    return mock


@pytest.fixture
def rag_service(config, mock_embedding_service):
    """モックを使ったRAGServiceを作成するフィクスチャ。"""
    with patch(
        "backend.app.services.rag_service.EmbeddingService",
        return_value=mock_embedding_service,
    ):
        service = RAGService(config)
        service._embedding_service = mock_embedding_service
        service._embedding_available = True
        return service


class TestIngestDocument:
    """ingest_documentメソッドのテスト。"""

    def test_ingest_text_document(self, rag_service, mock_embedding_service):
        """テキストドキュメントの取り込みが正常に動作する。"""
        content = b"Hello, this is a test document with some content."
        result = rag_service.ingest_document(content, "test.txt", "text/plain")

        assert isinstance(result, DocumentMetadata)
        assert result.filename == "test.txt"
        assert result.content_type == "text/plain"
        assert result.chunk_count >= 1
        assert result.file_size == len(content)
        assert result.document_id

    def test_ingest_stores_metadata(self, rag_service):
        """取り込み後にメタデータがJSONファイルに保存される。"""
        content = b"Test content for metadata storage."
        rag_service.ingest_document(content, "meta_test.txt", "text/plain")

        metadata_path = rag_service._metadata_path
        assert metadata_path.exists()

        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == 1
        assert data[0]["filename"] == "meta_test.txt"

    def test_ingest_calls_embedding_service(
        self, rag_service, mock_embedding_service
    ):
        """取り込み時にEmbeddingServiceが呼ばれる。"""
        content = b"Some text to embed."
        rag_service.ingest_document(content, "embed.txt", "text/plain")

        mock_embedding_service.compute_embeddings.assert_called()
        mock_embedding_service.add_chunks.assert_called()

    def test_ingest_without_embedding_raises_error(self, config):
        """埋め込みモデルが利用不可の場合RuntimeErrorが発生する。"""
        with patch(
            "backend.app.services.rag_service.EmbeddingService",
            side_effect=Exception("Model not found"),
        ):
            service = RAGService(config)

        with pytest.raises(RuntimeError, match="埋め込みモデルが利用できない"):
            service.ingest_document(b"test", "test.txt", "text/plain")

    def test_ingest_multiple_documents(self, rag_service):
        """複数ドキュメントの取り込みでメタデータが蓄積される。"""
        rag_service.ingest_document(b"First doc", "first.txt", "text/plain")
        rag_service.ingest_document(b"Second doc", "second.txt", "text/plain")

        docs = rag_service.list_documents()
        assert len(docs) == 2


class TestSearchRelevantChunks:
    """search_relevant_chunksメソッドのテスト。"""

    def test_search_returns_chunk_results(self, rag_service):
        """検索結果がChunkResultのリストで返される。"""
        results = rag_service.search_relevant_chunks("test query")

        assert len(results) == 2
        assert all(isinstance(r, ChunkResult) for r in results)

    def test_search_results_sorted_by_score_descending(self, rag_service):
        """検索結果がスコア降順でソートされる。"""
        results = rag_service.search_relevant_chunks("test query")

        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score

    def test_search_converts_distances_to_scores(self, rag_service):
        """コサイン距離が類似度スコア（1-distance）に変換される。"""
        results = rag_service.search_relevant_chunks("test query")

        # distance=0.1 → score=0.9, distance=0.3 → score=0.7
        assert results[0].score == pytest.approx(0.9, abs=0.01)
        assert results[1].score == pytest.approx(0.7, abs=0.01)

    def test_search_with_custom_top_k(
        self, rag_service, mock_embedding_service
    ):
        """カスタムtop_kが検索に使用される。"""
        rag_service.search_relevant_chunks("query", top_k=3)
        mock_embedding_service.search.assert_called_with(query="query", top_k=3)

    def test_search_without_embedding_returns_empty(self, config):
        """埋め込みモデルが利用不可の場合空リストを返す。"""
        with patch(
            "backend.app.services.rag_service.EmbeddingService",
            side_effect=Exception("Model not found"),
        ):
            service = RAGService(config)

        results = service.search_relevant_chunks("test")
        assert results == []

    def test_search_empty_results(self, rag_service, mock_embedding_service):
        """ChromaDBが空結果を返した場合空リストを返す。"""
        mock_embedding_service.search.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        results = rag_service.search_relevant_chunks("query")
        assert results == []


class TestBuildRagContext:
    """build_rag_contextメソッドのテスト。"""

    def test_build_context_with_chunks(self, rag_service):
        """チャンクからコンテキスト文字列が構築される。"""
        chunks = [
            ChunkResult(
                content="最初のチャンク内容",
                document_id="doc1",
                document_name="test.txt",
                score=0.9,
                chunk_index=0,
            ),
            ChunkResult(
                content="二番目のチャンク内容",
                document_id="doc1",
                document_name="test.txt",
                score=0.7,
                chunk_index=1,
            ),
        ]

        context = rag_service.build_rag_context(chunks)

        assert "最初のチャンク内容" in context
        assert "二番目のチャンク内容" in context
        assert "test.txt" in context
        assert "0.90" in context
        assert "0.70" in context

    def test_build_context_empty_chunks(self, rag_service):
        """空のチャンクリストの場合空文字列を返す。"""
        context = rag_service.build_rag_context([])
        assert context == ""

    def test_build_context_includes_instructions(self, rag_service):
        """コンテキストにユーザーへの指示が含まれる。"""
        chunks = [
            ChunkResult(
                content="テスト内容",
                document_id="doc1",
                document_name="test.txt",
                score=0.8,
                chunk_index=0,
            ),
        ]

        context = rag_service.build_rag_context(chunks)
        assert "関連ドキュメント" in context
        assert "回答してください" in context


class TestDeleteDocument:
    """delete_documentメソッドのテスト。"""

    def test_delete_existing_document(
        self, rag_service, mock_embedding_service
    ):
        """既存ドキュメントが正常に削除される。"""
        # まずドキュメントを追加
        result = rag_service.ingest_document(
            b"Content to delete", "delete_me.txt", "text/plain"
        )
        doc_id = result.document_id

        # 削除
        rag_service.delete_document(doc_id)

        # メタデータから削除されている
        docs = rag_service.list_documents()
        assert all(d.document_id != doc_id for d in docs)

        # ChromaDBからも削除が呼ばれている
        mock_embedding_service.delete_by_document_id.assert_called_with(doc_id)

    def test_delete_nonexistent_document_raises_error(self, rag_service):
        """存在しないドキュメントIDの削除でValueErrorが発生する。"""
        with pytest.raises(ValueError, match="ドキュメントが見つかりません"):
            rag_service.delete_document("nonexistent-id")


class TestListDocuments:
    """list_documentsメソッドのテスト。"""

    def test_list_empty(self, rag_service):
        """ドキュメントがない場合空リストを返す。"""
        docs = rag_service.list_documents()
        assert docs == []

    def test_list_after_ingest(self, rag_service):
        """取り込み後にドキュメント一覧に含まれる。"""
        rag_service.ingest_document(b"Doc content", "list_test.txt", "text/plain")

        docs = rag_service.list_documents()
        assert len(docs) == 1
        assert docs[0].filename == "list_test.txt"
        assert isinstance(docs[0], DocumentMetadata)

    def test_list_returns_all_documents(self, rag_service):
        """複数のドキュメントがすべて返される。"""
        rag_service.ingest_document(b"Doc 1", "doc1.txt", "text/plain")
        rag_service.ingest_document(b"Doc 2", "doc2.txt", "text/plain")
        rag_service.ingest_document(b"Doc 3", "doc3.md", "text/markdown")

        docs = rag_service.list_documents()
        assert len(docs) == 3
        filenames = [d.filename for d in docs]
        assert "doc1.txt" in filenames
        assert "doc2.txt" in filenames
        assert "doc3.md" in filenames
