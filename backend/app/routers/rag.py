"""RAGドキュメント管理APIルーター。

ドキュメントのアップロード、一覧取得、削除エンドポイントを提供する。
ファイルアップロードはmultipart/form-dataで受け付ける。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from backend.app.dependencies import get_rag_service
from backend.app.rag.document_loader import UnsupportedFormatError
from backend.app.schemas.rag import (
    DocumentListResponse,
    DocumentUploadResponse,
)
from backend.app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile,
    rag_service: RAGService = Depends(get_rag_service),
) -> DocumentUploadResponse:
    """ドキュメントをアップロードしてRAGストアに取り込む。

    multipart/form-dataでファイルを受け取り、テキスト抽出→チャンキング→
    埋め込み生成→ベクトルストアへの格納を実行する。

    Args:
        file: アップロードされたファイル（UploadFile）
        rag_service: RAGサービスインスタンス

    Returns:
        DocumentUploadResponse: アップロード結果

    Raises:
        HTTPException 415: サポート外のファイル形式の場合
        HTTPException 503: 埋め込みモデルが利用不可の場合
    """
    try:
        # ファイル内容を読み込み
        file_content = await file.read()
        content_type = file.content_type or "application/octet-stream"
        filename = file.filename or "unknown"

        # RAGサービスでドキュメントを取り込み
        metadata = rag_service.ingest_document(
            file_content=file_content,
            filename=filename,
            content_type=content_type,
        )

        return DocumentUploadResponse(
            success=True,
            document=metadata,
            message=f"ドキュメント '{filename}' を正常にアップロードしました。",
        )

    except UnsupportedFormatError as e:
        raise HTTPException(
            status_code=415,
            detail={
                "error": "非対応のファイル形式です",
                "content_type": e.content_type,
                "supported_formats": e.supported_formats,
            },
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "埋め込みサービスが利用できません",
                "message": str(e),
            },
        )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    rag_service: RAGService = Depends(get_rag_service),
) -> DocumentListResponse:
    """アップロード済みドキュメントの一覧を取得する。

    Args:
        rag_service: RAGサービスインスタンス

    Returns:
        DocumentListResponse: ドキュメント一覧
    """
    documents = rag_service.list_documents()
    return DocumentListResponse(documents=documents)


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    rag_service: RAGService = Depends(get_rag_service),
) -> None:
    """指定されたドキュメントを削除する。

    ドキュメントとその関連チャンク・埋め込みをすべて削除する。

    Args:
        document_id: 削除対象のドキュメントID
        rag_service: RAGサービスインスタンス

    Raises:
        HTTPException 404: ドキュメントが見つからない場合
    """
    try:
        rag_service.delete_document(document_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "ドキュメントが見つかりません",
                "document_id": document_id,
            },
        )
