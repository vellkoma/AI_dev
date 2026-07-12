"""メインエントリーポイントのユニットテスト。

main.pyのコマンドライン引数解析、クライアント生成ロジック、
エラーハンドリングをテストする。
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from llm_chat_app.clients.base import APIProvider, LocalModelBackend
from llm_chat_app.exceptions import ConfigurationError
from llm_chat_app.main import _create_api_client, _create_local_client, parse_args
from llm_chat_app.models import AppConfig


class TestParseArgs:
    """コマンドライン引数解析のテスト。"""

    def test_デフォルト値(self):
        """引数なしの場合はデフォルト値が使用される。"""
        with patch.object(sys, "argv", ["main"]):
            args = parse_args()
            assert args.mode == "api"
            assert args.config == "config.yaml"
            assert args.provider is None

    def test_apiモード指定(self):
        """--mode api を指定した場合。"""
        with patch.object(sys, "argv", ["main", "--mode", "api"]):
            args = parse_args()
            assert args.mode == "api"

    def test_localモード指定(self):
        """--mode local を指定した場合。"""
        with patch.object(sys, "argv", ["main", "--mode", "local"]):
            args = parse_args()
            assert args.mode == "local"

    def test_設定ファイルパス指定(self):
        """--config でカスタムパスを指定した場合。"""
        with patch.object(sys, "argv", ["main", "--config", "custom.yaml"]):
            args = parse_args()
            assert args.config == "custom.yaml"

    def test_プロバイダー指定(self):
        """--provider でプロバイダーを指定した場合。"""
        with patch.object(sys, "argv", ["main", "--provider", "claude"]):
            args = parse_args()
            assert args.provider == "claude"

    def test_全オプション指定(self):
        """すべてのオプションを同時に指定した場合。"""
        with patch.object(
            sys, "argv", ["main", "--mode", "local", "--config", "my.yaml", "--provider", "ollama"]
        ):
            args = parse_args()
            assert args.mode == "local"
            assert args.config == "my.yaml"
            assert args.provider == "ollama"

    def test_不正なモードでエラー(self):
        """--mode に不正な値を指定するとエラーになる。"""
        with patch.object(sys, "argv", ["main", "--mode", "invalid"]):
            with pytest.raises(SystemExit):
                parse_args()


class TestCreateApiClient:
    """APIクライアント生成のテスト。"""

    def _make_config(self, **kwargs) -> AppConfig:
        """テスト用AppConfigを生成する。"""
        defaults = {
            "api_provider": "openai",
            "api_key": "test-key-123",
            "api_model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 2000,
        }
        defaults.update(kwargs)
        return AppConfig(**defaults)

    def _make_args(self, provider=None):
        """テスト用argsオブジェクトを生成する。"""
        args = MagicMock()
        args.provider = provider
        return args

    @patch("llm_chat_app.clients.api_client.API_Chat_Client._initialize_client")
    def test_正常なAPIクライアント生成(self, mock_init):
        """正常な設定でAPIクライアントが生成される。"""
        mock_init.return_value = None
        config = self._make_config()
        args = self._make_args()

        client = _create_api_client(args, config)

        assert client.provider == APIProvider.OPENAI
        assert client.api_key == "test-key-123"
        assert client.model == "gpt-3.5-turbo"

    @patch("llm_chat_app.clients.api_client.API_Chat_Client._initialize_client")
    def test_コマンドライン引数でプロバイダー上書き(self, mock_init):
        """--providerでconfig.yamlのプロバイダーを上書きする。"""
        mock_init.return_value = None
        config = self._make_config(api_provider="openai")
        args = self._make_args(provider="claude")

        client = _create_api_client(args, config)

        assert client.provider == APIProvider.CLAUDE

    def test_プロバイダー未設定でエラー(self):
        """プロバイダーがどこにも設定されていない場合エラーになる。"""
        config = self._make_config(api_provider=None)
        args = self._make_args()

        with pytest.raises(ConfigurationError) as exc_info:
            _create_api_client(args, config)
        assert "APIプロバイダーが指定されていません" in str(exc_info.value)

    def test_不正なプロバイダー名でエラー(self):
        """不正なプロバイダー名が指定された場合エラーになる。"""
        config = self._make_config()
        args = self._make_args(provider="invalid_provider")

        with pytest.raises(ConfigurationError) as exc_info:
            _create_api_client(args, config)
        assert "不正なAPIプロバイダー" in str(exc_info.value)

    def test_APIキー未設定でエラー(self):
        """APIキーが設定されていない場合エラーになる。"""
        config = self._make_config(api_key=None)
        args = self._make_args()

        with pytest.raises(ConfigurationError) as exc_info:
            _create_api_client(args, config)
        assert "APIキーが設定されていません" in str(exc_info.value)


class TestCreateLocalClient:
    """ローカルクライアント生成のテスト。"""

    def _make_config(self, **kwargs) -> AppConfig:
        """テスト用AppConfigを生成する。"""
        defaults = {
            "local_backend": "llama_cpp",
            "local_model_path": "./models/test-model.gguf",
            "local_n_ctx": 2048,
            "local_n_gpu_layers": 0,
            "temperature": 0.7,
            "max_tokens": 2000,
        }
        defaults.update(kwargs)
        return AppConfig(**defaults)

    def _make_args(self, provider=None):
        """テスト用argsオブジェクトを生成する。"""
        args = MagicMock()
        args.provider = provider
        return args

    @patch("llm_chat_app.clients.local_client.Local_Chat_Client._initialize_model")
    def test_正常なローカルクライアント生成(self, mock_init):
        """正常な設定でローカルクライアントが生成される。"""
        mock_init.return_value = None
        config = self._make_config()
        args = self._make_args()

        client = _create_local_client(args, config)

        assert client.backend == LocalModelBackend.LLAMA_CPP
        assert client.model_path == "./models/test-model.gguf"
        assert client.n_ctx == 2048

    @patch("llm_chat_app.clients.local_client.Local_Chat_Client._initialize_model")
    def test_コマンドライン引数でバックエンド上書き(self, mock_init):
        """--providerでconfig.yamlのバックエンドを上書きする。"""
        mock_init.return_value = None
        config = self._make_config(local_backend="llama_cpp")
        args = self._make_args(provider="ollama")

        client = _create_local_client(args, config)

        assert client.backend == LocalModelBackend.OLLAMA

    def test_バックエンド未設定でエラー(self):
        """バックエンドがどこにも設定されていない場合エラーになる。"""
        config = self._make_config(local_backend=None)
        args = self._make_args()

        with pytest.raises(ConfigurationError) as exc_info:
            _create_local_client(args, config)
        assert "ローカルモデルバックエンドが指定されていません" in str(exc_info.value)

    def test_不正なバックエンド名でエラー(self):
        """不正なバックエンド名が指定された場合エラーになる。"""
        config = self._make_config()
        args = self._make_args(provider="invalid_backend")

        with pytest.raises(ConfigurationError) as exc_info:
            _create_local_client(args, config)
        assert "不正なローカルモデルバックエンド" in str(exc_info.value)

    def test_モデルパス未設定でエラー(self):
        """モデルパスが設定されていない場合エラーになる。"""
        config = self._make_config(local_model_path=None)
        args = self._make_args()

        with pytest.raises(ConfigurationError) as exc_info:
            _create_local_client(args, config)
        assert "ローカルモデルのパスが設定されていません" in str(exc_info.value)
