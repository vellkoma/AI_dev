"""メインエントリーポイントモジュール。

LLMチャットアプリケーションの起動処理を担当する。
コマンドライン引数の解析、設定読み込み、各コンポーネントの初期化、
チャットインターフェースの起動を行う。

Requirements: 1.1, 2.1, 6.1, 7.1, 7.4
"""

from __future__ import annotations

import argparse
import sys
import traceback
from typing import Optional

from llm_chat_app.clients.base import APIProvider, LocalModelBackend
from llm_chat_app.exceptions import ChatAppError


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を解析する。

    Returns:
        解析済みの引数オブジェクト
    """
    parser = argparse.ArgumentParser(
        description="LLM Chat App - APIまたはローカルモデルでチャット対話を行うアプリケーション"
    )
    parser.add_argument(
        "--mode",
        choices=["api", "local"],
        default="api",
        help="実行モード: api（商用API）または local（ローカルモデル）。デフォルト: api",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="設定ファイルのパス。デフォルト: config.yaml",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="プロバイダー/バックエンド名を上書き指定（例: openai, claude, gemini, llama_cpp, ollama）",
    )
    return parser.parse_args()


def main() -> None:
    """アプリケーションのメインエントリーポイント。

    以下の手順で起動処理を実行する:
    1. コマンドライン引数の解析
    2. 設定ファイルの読み込み
    3. モードに応じたLLMクライアントの初期化
    4. ChatOrchestrator、History_Manager、Stream_Handlerの組み立て
    5. Chat_Interfaceの起動
    """
    try:
        args = parse_args()

        # 設定ファイルの読み込み
        from llm_chat_app.infrastructure.config import Config_Manager

        config_manager = Config_Manager()
        config = config_manager.load_config(args.config)

        # モードに応じたLLMクライアントの初期化
        if args.mode == "api":
            client = _create_api_client(args, config)
        else:
            client = _create_local_client(args, config)

        # コンポーネントの組み立て
        from llm_chat_app.core.history import History_Manager
        from llm_chat_app.core.stream import Stream_Handler

        history_manager = History_Manager(max_tokens=config.history_max_tokens)
        stream_handler = Stream_Handler()

        from llm_chat_app.core.orchestrator import ChatOrchestrator

        orchestrator = ChatOrchestrator(client, history_manager, stream_handler)

        # チャットインターフェースの起動
        from llm_chat_app.ui.cli import Chat_Interface

        chat_interface = Chat_Interface(orchestrator)
        chat_interface.start()

    except ChatAppError as e:
        # アプリケーション固有エラー: ユーザーフレンドリーなメッセージを表示
        print(f"\n{e.full_message}", file=sys.stderr)
        sys.exit(1)

    except KeyboardInterrupt:
        # Ctrl+C: 終了メッセージを表示
        print("\nチャットを終了します。お疲れ様でした。")
        sys.exit(0)

    except Exception as e:
        # 未処理の例外: トレースバック情報付きのエラー表示
        print(f"\n予期しないエラーが発生しました: {e}", file=sys.stderr)
        print(f"詳細:\n{traceback.format_exc()}", file=sys.stderr)
        sys.exit(1)


def _resolve_api_key(provider: APIProvider, config_api_key: Optional[str]) -> Optional[str]:
    """プロバイダーに応じたAPIキーを解決する。

    以下の優先順位でAPIキーを取得する:
    1. config.yamlのapi_keyが有効な値（環境変数展開済み）ならそれを使用
    2. プロバイダーに応じた環境変数から自動取得

    Args:
        provider: 使用するAPIプロバイダー
        config_api_key: config.yamlから読み込んだAPIキー（展開済み）

    Returns:
        解決されたAPIキー文字列、または取得できない場合はNone
    """
    import os

    # プロバイダーごとの環境変数名
    env_var_map = {
        APIProvider.OPENAI: "OPENAI_API_KEY",
        APIProvider.CLAUDE: "ANTHROPIC_API_KEY",
        APIProvider.GEMINI: "GOOGLE_API_KEY",
    }

    # config.yamlのキーが有効ならそのまま使用（ただしプロバイダー固有の環境変数を優先）
    provider_env_var = env_var_map.get(provider)
    if provider_env_var:
        env_key = os.environ.get(provider_env_var)
        if env_key:
            return env_key

    # フォールバック: config.yamlの値を使用
    if config_api_key:
        return config_api_key

    return None


def _create_api_client(args: argparse.Namespace, config):
    """APIモードのLLMクライアントを生成する。

    Args:
        args: コマンドライン引数
        config: アプリケーション設定（AppConfig）

    Returns:
        初期化されたAPI_Chat_Clientインスタンス

    Raises:
        ConfigurationError: APIキーが未設定の場合
    """
    from llm_chat_app.clients.api_client import API_Chat_Client
    from llm_chat_app.exceptions import ConfigurationError

    # プロバイダーの決定: コマンドライン引数 > 設定ファイル
    provider_name = args.provider or config.api_provider
    if not provider_name:
        raise ConfigurationError(
            message="APIプロバイダーが指定されていません。",
            details="--provider オプションまたは config.yaml の api.provider を設定してください。",
        )

    # APIProvider Enumに変換
    try:
        provider = APIProvider(provider_name)
    except ValueError:
        valid_providers = ", ".join(p.value for p in APIProvider)
        raise ConfigurationError(
            message=f"不正なAPIプロバイダー: '{provider_name}'",
            details=f"有効な値: {valid_providers}",
        )

    # APIキーの決定: プロバイダーに応じた環境変数を自動取得
    api_key = _resolve_api_key(provider, config.api_key)
    if not api_key:
        env_var_names = {
            APIProvider.OPENAI: "OPENAI_API_KEY",
            APIProvider.CLAUDE: "ANTHROPIC_API_KEY",
            APIProvider.GEMINI: "GOOGLE_API_KEY",
        }
        expected_env = env_var_names.get(provider, "不明")
        raise ConfigurationError(
            message="APIキーが設定されていません。",
            details=(
                f"プロバイダー '{provider.value}' 用のAPIキーを設定してください。\n"
                f"環境変数 {expected_env} を設定するか、config.yaml の api.api_key を更新してください。"
            ),
        )

    # プロバイダーに応じたデフォルトモデル名
    model = config.api_model
    if args.provider and args.provider != config.api_provider:
        # コマンドラインでプロバイダーを切り替えた場合、モデルもデフォルトに変更
        default_models = {
            APIProvider.OPENAI: "gpt-3.5-turbo",
            APIProvider.CLAUDE: "claude-3-haiku-20240307",
            APIProvider.GEMINI: "gemini-pro",
        }
        model = default_models.get(provider, config.api_model)

    return API_Chat_Client(
        provider=provider,
        api_key=api_key,
        model=model,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )


def _create_local_client(args: argparse.Namespace, config):
    """ローカルモードのLLMクライアントを生成する。

    Args:
        args: コマンドライン引数
        config: アプリケーション設定（AppConfig）

    Returns:
        初期化されたLocal_Chat_Clientインスタンス

    Raises:
        ConfigurationError: バックエンドまたはモデルパスが未設定の場合
    """
    from llm_chat_app.clients.local_client import Local_Chat_Client
    from llm_chat_app.exceptions import ConfigurationError

    # バックエンドの決定: コマンドライン引数 > 設定ファイル
    backend_name = args.provider or config.local_backend
    if not backend_name:
        raise ConfigurationError(
            message="ローカルモデルバックエンドが指定されていません。",
            details="--provider オプションまたは config.yaml の local.backend を設定してください。",
        )

    # LocalModelBackend Enumに変換
    try:
        backend = LocalModelBackend(backend_name)
    except ValueError:
        valid_backends = ", ".join(b.value for b in LocalModelBackend)
        raise ConfigurationError(
            message=f"不正なローカルモデルバックエンド: '{backend_name}'",
            details=f"有効な値: {valid_backends}",
        )

    # モデルパスの確認
    if not config.local_model_path:
        raise ConfigurationError(
            message="ローカルモデルのパスが設定されていません。",
            details="config.yaml の local.model_path を設定してください。",
        )

    return Local_Chat_Client(
        backend=backend,
        model_path=config.local_model_path,
        n_ctx=config.local_n_ctx,
        n_gpu_layers=config.local_n_gpu_layers,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )


if __name__ == "__main__":
    main()
