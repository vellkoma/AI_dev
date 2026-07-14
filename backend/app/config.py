"""バックエンド設定管理モジュール。

環境変数と設定ファイルからバックエンドの設定を読み込む。
CORS設定、モデル設定、RAG設定、サーバー設定を管理する。
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class BackendConfig:
    """バックエンド全体の設定を管理するクラス。

    環境変数から各種設定値を読み込み、アプリケーション全体で
    参照可能な設定オブジェクトを提供する。
    """

    # サーバー設定
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS設定
    cors_origins: List[str] = field(default_factory=lambda: ["http://localhost:3000"])

    # LLMモデル設定
    default_provider: str = "openai"
    default_model: str = "gpt-3.5-turbo"
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000

    # ローカルモデル設定
    local_model_path: Optional[str] = None
    local_backend: str = "llama_cpp"

    # RAG設定
    chroma_persist_dir: str = "./data/chroma"
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 500
    chunk_overlap: int = 50
    rag_top_k: int = 5

    # ストレージ設定
    sessions_dir: str = "./data/sessions"
    stats_file: str = "./data/stats.json"
    documents_dir: str = "./data/documents"

    @classmethod
    def from_env(cls) -> "BackendConfig":
        """環境変数から設定を読み込む。

        環境変数が設定されていない場合はデフォルト値を使用する。
        API_Keyは OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY の
        順に優先して読み込む。

        Returns:
            BackendConfig: 環境変数から構築された設定インスタンス
        """
        return cls(
            host=os.getenv("BACKEND_HOST", "0.0.0.0"),
            port=int(os.getenv("BACKEND_PORT", "8000")),
            cors_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
            default_provider=os.getenv("DEFAULT_PROVIDER", "openai"),
            default_model=os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo"),
            api_key=(
                os.getenv("OPENAI_API_KEY")
                or os.getenv("ANTHROPIC_API_KEY")
                or os.getenv("GEMINI_API_KEY")
            ),
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("MAX_TOKENS", "2000")),
            local_model_path=os.getenv("LOCAL_MODEL_PATH"),
            local_backend=os.getenv("LOCAL_BACKEND", "llama_cpp"),
            chroma_persist_dir=os.getenv("CHROMA_PERSIST_DIR", "./data/chroma"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            chunk_size=int(os.getenv("CHUNK_SIZE", "500")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "50")),
            rag_top_k=int(os.getenv("RAG_TOP_K", "5")),
            sessions_dir=os.getenv("SESSIONS_DIR", "./data/sessions"),
            stats_file=os.getenv("STATS_FILE", "./data/stats.json"),
            documents_dir=os.getenv("DOCUMENTS_DIR", "./data/documents"),
        )
