"""EmbeddingServiceのユニットテスト。

ChromaDBとの統合テストを含む。
sentence-transformersモデルはモックで代替する。
"""

import tempfile
import shutil
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

from backend.app.rag.embeddings import EmbeddingService


@pytest.fixture
def temp_dir():
    """テスト用一時ディレクトリを作成・クリーンアップする。"""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def mock_model():
    """sentence-transformersモデルのモックを返す。"""
    model = MagicMock()
    # encode()が呼ばれたら、テキスト数 x 384次元のダミー埋め込みを返す
    def fake_encode(texts, convert_to_numpy=True):
        return np.random.rand(len(texts), 384).astype(np.float32)
    model.encode = MagicMock(side_effect=fake_encode)
    return model


@pytest.fixture
def embedding_service(temp_dir, mock_model):
    """モックモデルを注入したEmbeddingServiceインスタンスを返す。"""
    service = EmbeddingService(
        model_name="all-MiniLM-L6-v2",
        persist_directory=temp_dir,
        collection_name="test_collection",
    )
    # 遅延ロードをバイパスしてモックモデルを設定
    service._model = mock_model
    return service


class TestEmbeddingServiceInit:
    """EmbeddingServiceの初期化テスト。"""

    def test_creates_chroma_client_and_collection(self, temp_dir):
        """ChromaDBクライアントとコレクションが正しく初期化される。"""
        service = EmbeddingService(
            persist_directory=temp_dir,
            collection_name="init_test",
        )
        assert service._chroma_client is not None
        assert service._collection is not None
        assert service.count == 0

    def test_lazy_model_loading(self, temp_dir):
        """モデルはインスタンス化時にロードされない（遅延ロード）。"""
        service = EmbeddingService(
            persist_directory=temp_dir,
            collection_name="lazy_test",
        )
        assert service._model is None


class TestComputeEmbeddings:
    """compute_embeddingsメソッドのテスト。"""

    def test_returns_list_of_lists(self, embedding_service):
        """埋め込み結果がリストのリストで返される。"""
        result = embedding_service.compute_embeddings(["hello", "world"])
        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], list)
        assert len(result[0]) == 384

    def test_calls_model_encode(self, embedding_service, mock_model):
        """モデルのencodeメソッドが正しく呼ばれる。"""
        texts = ["テスト文字列"]
        embedding_service.compute_embeddings(texts)
        mock_model.encode.assert_called_once_with(texts, convert_to_numpy=True)


class TestAddChunks:
    """add_chunksメソッドのテスト。"""

    def test_add_chunks_with_auto_embeddings(self, embedding_service):
        """embeddingsを指定しない場合、自動計算して格納される。"""
        embedding_service.add_chunks(
            ids=["chunk_1", "chunk_2"],
            documents=["ドキュメント1のテキスト", "ドキュメント2のテキスト"],
            metadatas=[
                {"document_id": "doc1", "chunk_index": 0},
                {"document_id": "doc1", "chunk_index": 1},
            ],
        )
        assert embedding_service.count == 2

    def test_add_chunks_with_precomputed_embeddings(self, embedding_service):
        """事前計算された埋め込みを使って格納できる。"""
        embeddings = np.random.rand(2, 384).tolist()
        embedding_service.add_chunks(
            ids=["pre_1", "pre_2"],
            documents=["テキストA", "テキストB"],
            metadatas=[
                {"document_id": "docA", "chunk_index": 0},
                {"document_id": "docA", "chunk_index": 1},
            ],
            embeddings=embeddings,
        )
        assert embedding_service.count == 2


class TestSearch:
    """searchメソッドのテスト。"""

    def test_search_returns_results(self, embedding_service):
        """検索結果がChromaDB形式の辞書で返される。"""
        # チャンクを追加
        embedding_service.add_chunks(
            ids=["s1", "s2", "s3"],
            documents=["Python入門", "機械学習入門", "データ分析入門"],
            metadatas=[
                {"document_id": "doc1", "chunk_index": 0},
                {"document_id": "doc1", "chunk_index": 1},
                {"document_id": "doc2", "chunk_index": 0},
            ],
        )

        results = embedding_service.search("プログラミング", top_k=2)
        assert "ids" in results
        assert "documents" in results
        assert "metadatas" in results
        assert "distances" in results
        # top_k=2なので最大2件
        assert len(results["ids"][0]) <= 2

    def test_search_with_where_filter(self, embedding_service):
        """whereフィルターを使用して検索結果を絞り込める。"""
        embedding_service.add_chunks(
            ids=["f1", "f2", "f3"],
            documents=["テキスト1", "テキスト2", "テキスト3"],
            metadatas=[
                {"document_id": "docA", "chunk_index": 0},
                {"document_id": "docB", "chunk_index": 0},
                {"document_id": "docA", "chunk_index": 1},
            ],
        )

        results = embedding_service.search(
            "テスト", top_k=10, where={"document_id": "docA"}
        )
        # docAのチャンクのみ返される
        for metadata in results["metadatas"][0]:
            assert metadata["document_id"] == "docA"


class TestDeleteByDocumentId:
    """delete_by_document_idメソッドのテスト。"""

    def test_deletes_all_chunks_for_document(self, embedding_service):
        """指定ドキュメントIDのチャンクがすべて削除される。"""
        embedding_service.add_chunks(
            ids=["d1", "d2", "d3", "d4"],
            documents=["テキスト1", "テキスト2", "テキスト3", "テキスト4"],
            metadatas=[
                {"document_id": "docX", "chunk_index": 0},
                {"document_id": "docX", "chunk_index": 1},
                {"document_id": "docY", "chunk_index": 0},
                {"document_id": "docY", "chunk_index": 1},
            ],
        )
        assert embedding_service.count == 4

        embedding_service.delete_by_document_id("docX")
        assert embedding_service.count == 2

    def test_delete_nonexistent_document_does_not_error(self, embedding_service):
        """存在しないドキュメントIDの削除はエラーにならない。"""
        # 空のコレクションに対して削除を実行してもエラーにならない
        embedding_service.delete_by_document_id("nonexistent_doc")
        assert embedding_service.count == 0


class TestCount:
    """countプロパティのテスト。"""

    def test_count_initially_zero(self, embedding_service):
        """初期状態ではカウントが0。"""
        assert embedding_service.count == 0

    def test_count_increments_after_add(self, embedding_service):
        """チャンク追加後にカウントが増加する。"""
        embedding_service.add_chunks(
            ids=["c1"],
            documents=["テスト"],
            metadatas=[{"document_id": "doc1", "chunk_index": 0}],
        )
        assert embedding_service.count == 1


class TestLazyModelLoading:
    """モデルの遅延ロードテスト。"""

    def test_get_model_loads_on_first_call(self, temp_dir):
        """_get_model()が初回呼び出しでモデルをロードする。"""
        service = EmbeddingService(
            persist_directory=temp_dir,
            collection_name="lazy_load_test",
        )

        with patch(
            "backend.app.rag.embeddings.EmbeddingService._get_model"
        ) as mock_get:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.random.rand(1, 384)
            mock_get.return_value = mock_model

            service.compute_embeddings(["テスト"])
            mock_get.assert_called_once()
