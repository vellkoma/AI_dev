"""モデル管理関連のPydanticスキーマ定義。

LLMモデル情報、モデル一覧レスポンス、モデル切り替えリクエスト・レスポンスの
データモデルを定義する。
"""

from typing import List

from pydantic import BaseModel


class ModelInfo(BaseModel):
    """モデル情報モデル。

    利用可能なLLMモデルの名前、プロバイダー、接続状態、パラメータを表現する。
    """

    name: str
    provider: str  # "openai" | "claude" | "gemini" | "local"
    status: str  # "available" | "unavailable"
    parameters: dict = {}


class ModelListResponse(BaseModel):
    """モデル一覧レスポンス。

    利用可能なモデル一覧と現在選択中のモデル名を返す。
    """

    models: List[ModelInfo]
    current_model: str


class ModelSwitchRequest(BaseModel):
    """モデル切り替えリクエスト。

    切り替え先のモデル名とプロバイダーを指定する。
    """

    model: str
    provider: str


class ModelSwitchResponse(BaseModel):
    """モデル切り替えレスポンス。

    切り替え結果の成否、対象モデル名、メッセージを返す。
    """

    success: bool
    model: str
    message: str
