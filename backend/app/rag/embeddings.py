"""埋め込み生成とChromaDB統合モジュール。

sentence-transformersを使用してテキストのベクトル埋め込みを計算し、
ChromaDBに格納・検索・削除する機能を提供する。
"""

import logging
from typing import Any, Dict, List, Optional

import chromadb

logger = logging.getLogger(__name__)


class EmbeddingService:
    """テキスト埋め込み生成とChromaDBベクトル検索を担当するサービス。

    sentence-transformers（all-MiniLM-L6-v2）で埋め込みを計算し、
    ChromaDBコレクションに格納する。類似度検索と削除もサポート。
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        persist_directory: str = "./data/chroma",
        collection_name: str = "documents",
    ):
        """EmbeddingServiceを初期化する。

        Args:
            model_name: sentence-transformersのモデル名
            persist_directory: ChromaDBの永続化ディレクトリ
            collection_name: ChromaDBコレクション名
        """
        self.model_name = model_name
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        # ChromaDBクライアント初期化
        self._chroma_client = chromadb.PersistentClient(path=persist_directory)
        self._collection = self._chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # sentence-transformersモデル（遅延ロード）
        self._model = None

    def _get_model(self):
        """sentence-transformersモデルを遅延ロードする。"""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            logger.info(f"Embeddingモデルをロードしました: {self.model_name}")
        return self._model

    def compute_embeddings(self, texts: List[str]) -> List[List[float]]:
        """テキストリストの埋め込みベクトルを計算する。

        Args:
            texts: 埋め込みを計算するテキストのリスト

        Returns:
            埋め込みベクトルのリスト
        """
        model = self._get_model()
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def add_chunks(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        embeddings: Optional[List[List[float]]] = None,
    ) -> None:
        """チャンクをChromaDBコレクションに追加する。

        embeddingsが未指定の場合、documentsから自動計算する。

        Args:
            ids: 各チャンクの一意なID
            documents: チャンクテキストのリスト
            metadatas: 各チャンクのメタデータ辞書
            embeddings: 事前計算された埋め込み（オプション）
        """
        if embeddings is None:
            embeddings = self.compute_embeddings(documents)

        self._collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def search(
        self,
        query: str,
        top_k: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """クエリテキストで類似度検索を実行する。

        Args:
            query: 検索クエリテキスト
            top_k: 取得する上位件数
            where: フィルター条件（オプション）

        Returns:
            ChromaDBの検索結果辞書（ids, documents, metadatas, distances）
        """
        query_embedding = self.compute_embeddings([query])[0]

        query_kwargs: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
        }
        if where is not None:
            query_kwargs["where"] = where

        results = self._collection.query(**query_kwargs)

        return results

    def delete_by_document_id(self, document_id: str) -> None:
        """指定ドキュメントIDに属するすべてのチャンクを削除する。

        Args:
            document_id: 削除対象のドキュメントID
        """
        self._collection.delete(where={"document_id": document_id})

    @property
    def count(self) -> int:
        """コレクション内のドキュメント数を返す。"""
        return self._collection.count()
