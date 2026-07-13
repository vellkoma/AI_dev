"""RAG関連のPydanticスキーマ定義。

ドキュメントメタデータ、ドキュメント一覧レスポンス、チャンク検索結果、
ドキュメントアップロードレスポンスのデータモデルを定義する。
"""

from typing import List

from pydantic import BaseModel


class DocumentMetadata(BaseModel):
    """ドキュメントメタデータモデル。

    アップロード済みドキュメントのID、ファイル名、MIME種別、
    チャンク数、アップロード日時、ファイルサイズを保持する。
    """

    document_id: str
    filename: str
    content_type: str
    chunk_count: int
    uploaded_at: float
    file_size: int


class DocumentListResponse(BaseModel):
    """ドキュメント一覧レスポンス。

    アップロード済みドキュメントのメタデータリストを返す。
    """

    documents: List[DocumentMetadata]


class ChunkResult(BaseModel):
    """チャンク検索結果モデル。

    類似度検索で取得されたチャンクの内容、所属ドキュメント情報、
    類似度スコア、チャンクインデックスを表現する。
    スコアは0.0〜1.0の範囲で、値が大きいほど類似度が高い。
    """

    content: str
    document_id: str
    document_name: str
    score: float
    chunk_index: int


class DocumentUploadResponse(BaseModel):
    """ドキュメントアップロードレスポンス。

    アップロード結果の成否、ドキュメントメタデータ、メッセージを返す。
    """

    success: bool
    document: DocumentMetadata
    message: str
