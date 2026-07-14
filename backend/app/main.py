"""FastAPIアプリケーションのエントリポイント。

バックエンドAPIサーバーの初期化、CORS設定、ルーター登録、
ライフスパンイベント（起動/終了時の処理）を定義する。
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import BackendConfig
from backend.app.dependencies import get_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフスパン管理。

    起動時: 設定読み込み、ストレージディレクトリ作成
    終了時: リソースのクリーンアップ
    """
    config = get_config()
    # 起動時の初期化処理: 必要なストレージディレクトリを作成
    os.makedirs(config.sessions_dir, exist_ok=True)
    os.makedirs(config.documents_dir, exist_ok=True)
    os.makedirs(config.chroma_persist_dir, exist_ok=True)

    yield

    # 終了時のクリーンアップ（将来の拡張用）
    pass


app = FastAPI(
    title="LLM Chat App - Web API",
    description=(
        "LLMチャットアプリケーションのWeb APIバックエンド。"
        "SSEストリーミング、RAG、統計ダッシュボード機能を提供する。"
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# CORS設定
config = BackendConfig.from_env()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター登録
from backend.app.routers import chat, history, models, rag, stats  # noqa: E402

app.include_router(chat.router)
app.include_router(models.router)
app.include_router(history.router)
app.include_router(stats.router)
app.include_router(rag.router)


@app.get("/")
async def root():
    """ヘルスチェック用ルートエンドポイント。"""
    return {
        "status": "running",
        "app": "LLM Chat App - Web API",
        "version": "2.0.0",
    }


@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント。"""
    return {"status": "healthy"}
