"""RAGオーケストレーションサービス。

ドキュメントのアップロード、チャンキング、埋め込み生成、
類似度検索、コンテキスト構築を統合管理する。
"""

import json
import logging
import time
import uuid
from pathlib import Path
from typing import List, Optional

from backend.app.config import BackendConfig
from backend.app.rag.chunker import TextChunker
from backend.app.rag.document_loader import DocumentLoader
from backend.app.rag.embeddings import EmbeddingService
from backend.app.schemas.rag import ChunkResult, DocumentMetadata

logger = logging.getLogger(__name__)


class RAGService:
    """RAGオーケストレーションサービス。

    ドキュメントのアップロード、チャンキング、埋め込み生成、
    類似度検索、コンテキスト構築を統合管理する。
    埋め込みモデルが利用できない場合もグレースフルに動作する。
    """

    def __init__(self, config: BackendConfig):
        """RAGServiceを初期化する。

        Args:
            config: バックエンド設定
        """
        self.config = config
        self.top_k = config.rag_top_k
        self.documents_dir = Path(config.documents_dir)
        self.documents_dir.mkdir(parents=True, exist_ok=True)

        # メタデータファイルパス
        self._metadata_path = self.documents_dir / "metadata.json"

        # コンポーネント初期化
        self._document_loader = DocumentLoader()
        self._chunker = TextChunker(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )

        # EmbeddingService初期化（モデルが利用不可の場合に備える）
        self._embedding_service: Optional[EmbeddingService] = None
        self._embedding_available = False
        try:
            self._embedding_service = EmbeddingService(
                model_name=config.embedding_model,
                persist_directory=config.chroma_persist_dir,
                collection_name="documents",
            )
            self._embedding_available = True
            logger.info("EmbeddingServiceを初期化しました")
        except Exception as e:
            logger.warning(
                f"EmbeddingServiceの初期化に失敗しました。"
                f"RAG機能は制限されます: {e}"
            )

    def _load_metadata(self) -> List[dict]:
        """メタデータストアからドキュメントメタデータを読み込む。

        Returns:
            ドキュメントメタデータの辞書リスト
        """
        if not self._metadata_path.exists():
            return []
        try:
            with open(self._metadata_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"メタデータの読み込みに失敗しました: {e}")
            return []

    def _save_metadata(self, metadata_list: List[dict]) -> None:
        """メタデータストアにドキュメントメタデータを保存する。

        Args:
            metadata_list: ドキュメントメタデータの辞書リスト
        """
        self._metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata_list, f, ensure_ascii=False, indent=2)

    def ingest_document(
        self, file_content: bytes, filename: str, content_type: str
    ) -> DocumentMetadata:
        """ドキュメントを取り込み、チャンキング→埋め込み→格納を実行する。

        ドキュメントをテキストに変換し、チャンクに分割し、
        埋め込みベクトルを計算してChromaDBに格納する。
        メタデータはJSONファイルに保存する。

        Args:
            file_content: ファイルのバイナリデータ
            filename: ファイル名
            content_type: MIMEタイプ

        Returns:
            DocumentMetadata: ドキュメントのメタデータ

        Raises:
            UnsupportedFormatError: サポート外の形式の場合
            RuntimeError: 埋め込みモデルが利用不可の場合
        """
        if not self._embedding_available or self._embedding_service is None:
            raise RuntimeError(
                "埋め込みモデルが利用できないため、ドキュメントの取り込みができません。"
            )

        # ドキュメントIDを生成
        document_id = str(uuid.uuid4())

        # テキスト抽出
        text = self._document_loader.load(file_content, filename, content_type)

        # チャンク分割
        chunks = self._chunker.split(text, document_id)

        # 埋め込み計算とChromaDBへの格納
        if chunks:
            chunk_ids = [
                f"{document_id}_chunk_{chunk.chunk_index}" for chunk in chunks
            ]
            chunk_documents = [chunk.content for chunk in chunks]
            chunk_metadatas = [
                {
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "filename": filename,
                }
                for chunk in chunks
            ]

            # 埋め込みを計算して格納
            embeddings = self._embedding_service.compute_embeddings(
                chunk_documents
            )
            self._embedding_service.add_chunks(
                ids=chunk_ids,
                documents=chunk_documents,
                metadatas=chunk_metadatas,
                embeddings=embeddings,
            )

        # メタデータを作成
        metadata = DocumentMetadata(
            document_id=document_id,
            filename=filename,
            content_type=content_type,
            chunk_count=len(chunks),
            uploaded_at=time.time(),
            file_size=len(file_content),
        )

        # メタデータをJSONファイルに保存
        metadata_list = self._load_metadata()
        metadata_list.append(metadata.model_dump())
        self._save_metadata(metadata_list)

        logger.info(
            f"ドキュメントを取り込みました: {filename} "
            f"(ID: {document_id}, チャンク数: {len(chunks)})"
        )

        return metadata

    def search_relevant_chunks(
        self, query: str, top_k: Optional[int] = None
    ) -> List[ChunkResult]:
        """クエリに関連するチャンクを類似度検索する。

        クエリテキストの埋め込みを計算し、ChromaDBで類似度検索を行い、
        結果をスコア降順でソートして上位N件を返す。

        Args:
            query: 検索クエリテキスト
            top_k: 取得する上位件数（Noneの場合は設定値を使用）

        Returns:
            類似度スコア降順でソートされた上位N件のChunkResult
        """
        if not self._embedding_available or self._embedding_service is None:
            logger.warning(
                "埋め込みモデルが利用できないため、検索できません。"
            )
            return []

        k = top_k if top_k is not None else self.top_k

        # ChromaDBで類似度検索
        results = self._embedding_service.search(query=query, top_k=k)

        # 結果をChunkResultオブジェクトに変換
        chunk_results: List[ChunkResult] = []

        if results and results.get("ids") and results["ids"][0]:
            ids = results["ids"][0]
            documents = results["documents"][0] if results.get("documents") else []
            metadatas = results["metadatas"][0] if results.get("metadatas") else []
            distances = results["distances"][0] if results.get("distances") else []

            for i in range(len(ids)):
                # コサイン距離を類似度スコアに変換（1 - distance）
                distance = distances[i] if i < len(distances) else 0.0
                score = max(0.0, min(1.0, 1.0 - distance))

                metadata = metadatas[i] if i < len(metadatas) else {}
                document_content = documents[i] if i < len(documents) else ""

                chunk_results.append(
                    ChunkResult(
                        content=document_content,
                        document_id=metadata.get("document_id", ""),
                        document_name=metadata.get("filename", ""),
                        score=score,
                        chunk_index=metadata.get("chunk_index", 0),
                    )
                )

        # スコア降順でソート
        chunk_results.sort(key=lambda x: x.score, reverse=True)

        return chunk_results[:k]

    def build_rag_context(self, chunks: List[ChunkResult]) -> str:
        """検索結果からLLMプロンプト用コンテキスト文字列を構築する。

        各チャンクの内容とソースドキュメント情報を整形し、
        LLMに渡すコンテキスト文字列を生成する。

        Args:
            chunks: ChunkResultのリスト

        Returns:
            LLMプロンプト用に整形されたコンテキスト文字列
        """
        if not chunks:
            return ""

        context_parts: List[str] = []
        context_parts.append("以下は関連ドキュメントからの抜粋です：\n")

        for i, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"--- ソース {i}: {chunk.document_name} "
                f"(類似度: {chunk.score:.2f}) ---"
            )
            context_parts.append(chunk.content)
            context_parts.append("")

        context_parts.append(
            "上記のコンテキストを参考にして、ユーザーの質問に回答してください。"
        )

        return "\n".join(context_parts)

    def delete_document(self, document_id: str) -> None:
        """ドキュメントと関連チャンク・埋め込みを削除する。

        ChromaDBから関連する埋め込みを削除し、
        メタデータストアからドキュメント情報を削除する。

        Args:
            document_id: 削除対象のドキュメントID

        Raises:
            ValueError: 指定されたドキュメントIDが存在しない場合
        """
        # メタデータストアから削除
        metadata_list = self._load_metadata()
        original_count = len(metadata_list)
        metadata_list = [
            m for m in metadata_list if m.get("document_id") != document_id
        ]

        if len(metadata_list) == original_count:
            raise ValueError(
                f"ドキュメントが見つかりません: {document_id}"
            )

        self._save_metadata(metadata_list)

        # ChromaDBから関連チャンクを削除
        if self._embedding_available and self._embedding_service is not None:
            try:
                self._embedding_service.delete_by_document_id(document_id)
            except Exception as e:
                logger.error(
                    f"ChromaDBからのチャンク削除に失敗しました: {e}"
                )

        logger.info(f"ドキュメントを削除しました: {document_id}")

    def list_documents(self) -> List[DocumentMetadata]:
        """アップロード済みドキュメント一覧を返す。

        メタデータストアからすべてのドキュメント情報を読み込み、
        DocumentMetadataオブジェクトのリストとして返す。

        Returns:
            DocumentMetadataのリスト
        """
        metadata_list = self._load_metadata()
        return [DocumentMetadata(**m) for m in metadata_list]
