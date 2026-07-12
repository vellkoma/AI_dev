"""設定管理モジュール。

YAML形式の設定ファイルの読み込み、バリデーション、
デフォルト設定生成を担当するConfig_Managerを提供する。

シングルトンパターンで実装され、アプリケーション全体で
一貫した設定管理を実現する。

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional

import yaml

from llm_chat_app.exceptions import ConfigurationError
from llm_chat_app.models import AppConfig


class Config_Manager:
    """設定ファイルの管理（シングルトン）。

    YAML形式の設定ファイルを読み込み、AppConfigオブジェクトを生成する。
    設定ファイルが存在しない場合はデフォルト設定ファイルを自動生成する。
    環境変数プレースホルダー（${ENV_VAR}形式）の展開にも対応する。

    Attributes:
        config: 現在のアプリケーション設定（AppConfig）
        config_path: 設定ファイルのパス
    """

    _instance: Optional[Config_Manager] = None

    def __new__(cls) -> Config_Manager:
        """シングルトンインスタンスを返す。"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Config_Managerを初期化する（初回のみ実行）。"""
        if not hasattr(self, "config"):
            self.config: Optional[AppConfig] = None
            self.config_path: str = "config.yaml"

    @classmethod
    def reset_instance(cls) -> None:
        """シングルトンインスタンスをリセットする（テスト用）。"""
        cls._instance = None

    def load_config(self, config_path: Optional[str] = None) -> AppConfig:
        """設定ファイルを読み込み、AppConfigオブジェクトを返す。

        設定ファイルが存在しない場合はデフォルト設定ファイルを自動生成し、
        その内容を読み込む。

        Args:
            config_path: 設定ファイルのパス。Noneの場合はデフォルトパスを使用。

        Returns:
            読み込んだ設定を含むAppConfigオブジェクト。

        Raises:
            ConfigurationError: 設定ファイルの読み込みまたはパースに失敗した場合。
        """
        if config_path is not None:
            self.config_path = config_path

        if not os.path.exists(self.config_path):
            self._create_default_config()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_dict = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(
                message="設定ファイルのYAML形式が不正です。",
                details=f"ファイル: {self.config_path}\nYAMLパースエラー: {e}",
            )
        except OSError as e:
            raise ConfigurationError(
                message="設定ファイルの読み込みに失敗しました。",
                details=f"ファイル: {self.config_path}\nエラー: {e}",
            )

        if config_dict is None:
            raise ConfigurationError(
                message="設定ファイルが空です。",
                details=f"ファイル: {self.config_path}",
            )

        self._validate_config(config_dict)
        self.config = self._parse_config(config_dict)
        return self.config

    def _create_default_config(self) -> None:
        """デフォルト設定ファイルを生成する。

        config.yaml.exampleと同等の構造を持つデフォルト設定ファイルを
        自動生成する。APIキーは環境変数プレースホルダーを使用する。
        """
        default_config: Dict[str, Any] = {
            "api": {
                "provider": "openai",
                "api_key": "${OPENAI_API_KEY}",
                "model": "gpt-3.5-turbo",
            },
            "local": {
                "backend": "llama_cpp",
                "model_path": "./models/llama-2-7b-chat.Q4_K_M.gguf",
                "n_ctx": 2048,
                "n_gpu_layers": 0,
            },
            "common": {
                "temperature": 0.7,
                "max_tokens": 2000,
                "history_max_tokens": 4000,
            },
            "logging": {
                "enabled": True,
                "level": "INFO",
                "file": "logs/chat.log",
            },
        }

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    default_config,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                )
        except OSError as e:
            raise ConfigurationError(
                message="デフォルト設定ファイルの生成に失敗しました。",
                details=f"ファイル: {self.config_path}\nエラー: {e}",
            )

    def _expand_env_vars(self, value: str) -> str:
        """${ENV_VAR}形式のプレースホルダーを環境変数で展開する。

        文字列中の${ENV_VAR}パターンを対応する環境変数の値に置換する。
        環境変数が設定されていない場合は空文字列に置換する。

        Args:
            value: 展開対象の文字列。

        Returns:
            環境変数が展開された文字列。
        """
        pattern = r"\$\{([^}]+)\}"

        def replace_env_var(match: re.Match) -> str:
            env_var_name = match.group(1)
            return os.environ.get(env_var_name, "")

        return re.sub(pattern, replace_env_var, value)

    def _validate_config(self, config_dict: Dict[str, Any]) -> None:
        """設定値のバリデーションを行う。

        設定ファイルの構造と値が正しいことを検証する。
        不正な場合はConfigurationErrorを送出する。

        Args:
            config_dict: YAML読み込み後の辞書データ。

        Raises:
            ConfigurationError: バリデーションに失敗した場合。
        """
        if not isinstance(config_dict, dict):
            raise ConfigurationError(
                message="設定ファイルの形式が不正です。",
                details="設定ファイルはYAMLマッピング形式である必要があります。",
            )

        # 必須セクションの検証
        required_sections = ["api", "common"]
        for section in required_sections:
            if section not in config_dict:
                raise ConfigurationError(
                    message=f"設定ファイルに必須セクション '{section}' がありません。",
                    details=(
                        f"config.yaml.exampleを参考に '{section}' セクションを追加してください。"
                    ),
                )

        # apiセクションのバリデーション
        api_section = config_dict.get("api", {})
        if not isinstance(api_section, dict):
            raise ConfigurationError(
                message="'api' セクションの形式が不正です。",
                details="'api' セクションはマッピング形式で記述してください。",
            )

        if "provider" not in api_section:
            raise ConfigurationError(
                message="'api.provider' が設定されていません。",
                details="openai, claude, gemini のいずれかを指定してください。",
            )

        valid_providers = {"openai", "claude", "gemini"}
        provider = api_section.get("provider")
        if provider not in valid_providers:
            raise ConfigurationError(
                message=f"不正なAPIプロバイダー: '{provider}'",
                details=f"有効な値: {', '.join(sorted(valid_providers))}",
            )

        # commonセクションのバリデーション
        common_section = config_dict.get("common", {})
        if not isinstance(common_section, dict):
            raise ConfigurationError(
                message="'common' セクションの形式が不正です。",
                details="'common' セクションはマッピング形式で記述してください。",
            )

        # temperatureの範囲チェック
        temperature = common_section.get("temperature", 0.7)
        if not isinstance(temperature, (int, float)):
            raise ConfigurationError(
                message="'common.temperature' は数値で指定してください。",
                details=f"現在の値: {temperature}（型: {type(temperature).__name__}）",
            )
        if not (0.0 <= float(temperature) <= 2.0):
            raise ConfigurationError(
                message="'common.temperature' は 0.0〜2.0 の範囲で指定してください。",
                details=f"現在の値: {temperature}",
            )

        # max_tokensの範囲チェック
        max_tokens = common_section.get("max_tokens", 2000)
        if not isinstance(max_tokens, int):
            raise ConfigurationError(
                message="'common.max_tokens' は整数で指定してください。",
                details=f"現在の値: {max_tokens}（型: {type(max_tokens).__name__}）",
            )
        if max_tokens <= 0:
            raise ConfigurationError(
                message="'common.max_tokens' は正の整数で指定してください。",
                details=f"現在の値: {max_tokens}",
            )

        # localセクションのバリデーション（存在する場合）
        local_section = config_dict.get("local")
        if local_section is not None:
            if not isinstance(local_section, dict):
                raise ConfigurationError(
                    message="'local' セクションの形式が不正です。",
                    details="'local' セクションはマッピング形式で記述してください。",
                )
            valid_backends = {"llama_cpp", "ollama"}
            backend = local_section.get("backend")
            if backend is not None and backend not in valid_backends:
                raise ConfigurationError(
                    message=f"不正なローカルモデルバックエンド: '{backend}'",
                    details=f"有効な値: {', '.join(sorted(valid_backends))}",
                )

        # loggingセクションのバリデーション（存在する場合）
        logging_section = config_dict.get("logging")
        if logging_section is not None:
            if not isinstance(logging_section, dict):
                raise ConfigurationError(
                    message="'logging' セクションの形式が不正です。",
                    details="'logging' セクションはマッピング形式で記述してください。",
                )
            valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR"}
            log_level = logging_section.get("level", "INFO")
            if log_level not in valid_log_levels:
                raise ConfigurationError(
                    message=f"不正なログレベル: '{log_level}'",
                    details=f"有効な値: {', '.join(sorted(valid_log_levels))}",
                )

    def _parse_config(self, config_dict: Dict[str, Any]) -> AppConfig:
        """辞書からAppConfigオブジェクトを生成する。

        YAML読み込み後の辞書データからAppConfigデータクラスの
        インスタンスを構築する。環境変数プレースホルダーも展開する。

        Args:
            config_dict: バリデーション済みの設定辞書データ。

        Returns:
            設定値を含むAppConfigオブジェクト。
        """
        api_section = config_dict.get("api", {})
        local_section = config_dict.get("local", {})
        common_section = config_dict.get("common", {})
        logging_section = config_dict.get("logging", {})

        # APIキーの環境変数展開
        api_key_raw = api_section.get("api_key")
        api_key: Optional[str] = None
        if api_key_raw is not None:
            api_key = self._expand_env_vars(str(api_key_raw))
            # 展開後に空文字列の場合はNoneにする
            if not api_key:
                api_key = None

        # モデルパスの環境変数展開
        model_path_raw = local_section.get("model_path")
        model_path: Optional[str] = None
        if model_path_raw is not None:
            model_path = self._expand_env_vars(str(model_path_raw))
            if not model_path:
                model_path = None

        return AppConfig(
            # API設定
            api_provider=api_section.get("provider"),
            api_key=api_key,
            api_model=api_section.get("model", "gpt-3.5-turbo"),
            # ローカルモデル設定
            local_backend=local_section.get("backend"),
            local_model_path=model_path,
            local_n_ctx=local_section.get("n_ctx", 2048),
            local_n_gpu_layers=local_section.get("n_gpu_layers", 0),
            # 共通設定
            temperature=float(common_section.get("temperature", 0.7)),
            max_tokens=int(common_section.get("max_tokens", 2000)),
            history_max_tokens=int(common_section.get("history_max_tokens", 4000)),
            # ログ設定
            log_enabled=bool(logging_section.get("enabled", True)),
            log_level=logging_section.get("level", "INFO"),
            log_file=logging_section.get("file", "chat.log"),
        )
