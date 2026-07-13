"""モデル管理APIルーター。

利用可能なLLMモデルの一覧取得と切り替えを提供する。
各モデルの接続状態（available/unavailable）を含め、
無効モデル指定時にはエラーと代替モデル情報を返す。

Requirements: 3.1, 3.2, 3.3, 3.4
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.app.dependencies import get_llm_service
from backend.app.schemas.models import (
    ModelInfo,
    ModelListResponse,
    ModelSwitchRequest,
    ModelSwitchResponse,
)
from backend.app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("", response_model=ModelListResponse)
def get_models(
    llm_service: LLMService = Depends(get_llm_service),
) -> ModelListResponse:
    """利用可能なモデル一覧を取得する。

    各モデルの名前、プロバイダー、接続状態（available/unavailable）、
    パラメータ情報を含むリストと現在選択中のモデル名を返す。

    Returns:
        ModelListResponse: モデル一覧と現在のモデル名
    """
    models: List[ModelInfo] = llm_service.get_available_models()
    current_model: str = llm_service.current_model

    return ModelListResponse(
        models=models,
        current_model=current_model,
    )


@router.post("/switch", response_model=ModelSwitchResponse)
def switch_model(
    request: ModelSwitchRequest,
    llm_service: LLMService = Depends(get_llm_service),
) -> ModelSwitchResponse:
    """使用モデルを切り替える。

    指定されたモデル名とプロバイダーでLLMクライアントを再構成する。
    無効なプロバイダーまたはモデルが指定された場合はHTTP 400エラーを返し、
    利用可能な代替モデルの情報を含める。

    Args:
        request: モデル切り替えリクエスト（モデル名、プロバイダー）

    Returns:
        ModelSwitchResponse: 切り替え結果

    Raises:
        HTTPException: 無効なモデル/プロバイダー指定時（400）
    """
    try:
        model_info: ModelInfo = llm_service.switch_model(
            model_name=request.model,
            provider=request.provider,
        )
        logger.info(
            f"モデル切り替え成功: provider={request.provider}, model={request.model}"
        )
        return ModelSwitchResponse(
            success=True,
            model=model_info.name,
            message=f"モデルを {model_info.provider}/{model_info.name} に切り替えました。",
        )
    except (ValueError, RuntimeError) as e:
        # 利用可能な代替モデル情報を取得
        available_models = llm_service.get_available_models()
        alternatives = [
            f"{m.provider}/{m.name}"
            for m in available_models
            if m.status == "available"
        ]
        error_message = str(e)
        if alternatives:
            error_message += f" 利用可能な代替モデル: {', '.join(alternatives)}"

        logger.warning(
            f"モデル切り替え失敗: provider={request.provider}, "
            f"model={request.model}, error={error_message}"
        )
        raise HTTPException(
            status_code=400,
            detail=error_message,
        )
