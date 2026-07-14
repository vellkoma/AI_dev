"""依存性注入モジュール。

FastAPI の Depends を使用してサービスのシングルトン管理を提供する。
各サービスはアプリケーションライフサイクル内で1つのインスタンスのみ生成される。
"""

from functools import lru_cache
from typing import Optional

from backend.app.config import BackendConfig


@lru_cache()
def get_config() -> BackendConfig:
    """設定のシングルトンインスタンスを返す。

    lru_cacheにより、初回呼び出し時に環境変数から設定を読み込み、
    以降は同一インスタンスを返す。

    Returns:
        BackendConfig: アプリケーション設定
    """
    return BackendConfig.from_env()


# サービスインスタンスのシングルトン管理
_llm_service_instance: Optional["LLMService"] = None  # noqa: F821


def get_llm_service():
    """LLMServiceのシングルトンインスタンスを返す。

    初回呼び出し時にLLMServiceを生成し、以降は同一インスタンスを返す。
    BackendConfigから設定を読み込み、LLMクライアントを初期化する。

    Returns:
        LLMService: LLMサービスインスタンス
    """
    global _llm_service_instance
    if _llm_service_instance is None:
        from backend.app.services.llm_service import LLMService

        config = get_config()
        _llm_service_instance = LLMService(config)
    return _llm_service_instance


def get_rag_service():
    """RAGServiceのシングルトンインスタンスを返す。

    初回呼び出し時にRAGServiceを生成し、以降は同一インスタンスを返す。
    ドキュメント取り込み、類似度検索、コンテキスト構築を担当するサービスを提供する。

    Returns:
        RAGService: RAGサービスインスタンス
    """
    from backend.app.services.rag_service import RAGService

    if not hasattr(get_rag_service, "_instance"):
        config = get_config()
        get_rag_service._instance = RAGService(config)
    return get_rag_service._instance


def get_session_service():
    """SessionServiceのシングルトンインスタンスを返す。

    会話セッションの永続化と検索を担当するサービスを提供する。
    初回呼び出し時にインスタンスを生成し、以降は同一インスタンスを返す。

    Returns:
        SessionService: セッション管理サービス
    """
    from backend.app.services.session_service import SessionService

    if not hasattr(get_session_service, "_instance"):
        config = get_config()
        get_session_service._instance = SessionService(config.sessions_dir)
    return get_session_service._instance


def get_stats_service():
    """StatsServiceのシングルトンインスタンスを返す。

    初回呼び出し時にBackendConfigからstats_fileパスを取得し、
    StatsServiceインスタンスを生成する。以降は同一インスタンスを返す。

    Returns:
        StatsService: パフォーマンス統計サービス
    """
    from pathlib import Path

    from backend.app.services.stats_service import StatsService

    if not hasattr(get_stats_service, "_instance"):
        config = get_config()
        get_stats_service._instance = StatsService(storage_path=Path(config.stats_file))
    return get_stats_service._instance
