"""Config_Managerのユニットテスト。

設定ファイルの読み込み、デフォルト生成、環境変数展開、
バリデーションの各機能をテストする。
"""

from __future__ import annotations

import pytest
import yaml

from llm_chat_app.exceptions import ConfigurationError
from llm_chat_app.infrastructure.config import Config_Manager
from llm_chat_app.models import AppConfig


@pytest.fixture(autouse=True)
def reset_singleton():
    """各テストの前後にシングルトンインスタンスをリセットする。"""
    Config_Manager.reset_instance()
    yield
    Config_Manager.reset_instance()


@pytest.fixture
def valid_config_dict():
    """有効な設定辞書を返す。"""
    return {
        "api": {
            "provider": "openai",
            "api_key": "test-api-key-123",
            "model": "gpt-4",
        },
        "local": {
            "backend": "llama_cpp",
            "model_path": "./models/test-model.gguf",
            "n_ctx": 4096,
            "n_gpu_layers": 10,
        },
        "common": {
            "temperature": 0.5,
            "max_tokens": 1000,
            "history_max_tokens": 3000,
        },
        "logging": {
            "enabled": True,
            "level": "DEBUG",
            "file": "logs/test.log",
        },
    }


@pytest.fixture
def config_file(valid_config_dict, tmp_path):
    """一時設定ファイルを作成して返す。"""
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(valid_config_dict, f, allow_unicode=True, default_flow_style=False)
    return str(config_path)


class TestSingleton:
    """シングルトンパターンのテスト。"""

    def test_singleton_returns_same_instance(self):
        """同じインスタンスが返されることを確認。"""
        mgr1 = Config_Manager()
        mgr2 = Config_Manager()
        assert mgr1 is mgr2

    def test_reset_instance_creates_new_instance(self):
        """reset_instance後に新しいインスタンスが生成されることを確認。"""
        mgr1 = Config_Manager()
        Config_Manager.reset_instance()
        mgr2 = Config_Manager()
        assert mgr1 is not mgr2


class TestLoadConfig:
    """load_config()のテスト。"""

    def test_load_valid_config(self, config_file):
        """有効な設定ファイルが正しく読み込まれることを確認。"""
        mgr = Config_Manager()
        config = mgr.load_config(config_file)

        assert isinstance(config, AppConfig)
        assert config.api_provider == "openai"
        assert config.api_key == "test-api-key-123"
        assert config.api_model == "gpt-4"
        assert config.local_backend == "llama_cpp"
        assert config.local_model_path == "./models/test-model.gguf"
        assert config.local_n_ctx == 4096
        assert config.local_n_gpu_layers == 10
        assert config.temperature == 0.5
        assert config.max_tokens == 1000
        assert config.history_max_tokens == 3000
        assert config.log_enabled is True
        assert config.log_level == "DEBUG"
        assert config.log_file == "logs/test.log"

    def test_load_config_stores_result(self, config_file):
        """読み込み後にconfig属性に格納されることを確認。"""
        mgr = Config_Manager()
        config = mgr.load_config(config_file)
        assert mgr.config is config

    def test_load_config_with_minimal_config(self, tmp_path):
        """最小限の設定（api + common）でも読み込めることを確認。"""
        minimal_config = {
            "api": {"provider": "claude", "model": "claude-3-haiku-20240307"},
            "common": {"temperature": 1.0, "max_tokens": 500},
        }
        config_path = tmp_path / "minimal.yaml"
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(minimal_config, f)

        mgr = Config_Manager()
        config = mgr.load_config(str(config_path))
        assert config.api_provider == "claude"
        assert config.api_model == "claude-3-haiku-20240307"
        assert config.temperature == 1.0
        assert config.max_tokens == 500


class TestCreateDefaultConfig:
    """_create_default_config()のテスト。"""

    def test_creates_default_config_when_file_missing(self, tmp_path):
        """設定ファイルが存在しない場合にデフォルトを自動生成することを確認。"""
        config_path = tmp_path / "nonexistent_config.yaml"
        mgr = Config_Manager()
        config = mgr.load_config(str(config_path))

        # ファイルが生成されている
        assert config_path.exists()

        # デフォルト値が設定されている
        assert config.api_provider == "openai"
        assert config.api_model == "gpt-3.5-turbo"
        assert config.temperature == 0.7
        assert config.max_tokens == 2000

    def test_default_config_is_valid_yaml(self, tmp_path):
        """生成されたデフォルト設定ファイルが有効なYAMLであることを確認。"""
        config_path = tmp_path / "default.yaml"
        mgr = Config_Manager()
        mgr.load_config(str(config_path))

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert "api" in data
        assert "local" in data
        assert "common" in data
        assert "logging" in data


class TestExpandEnvVars:
    """_expand_env_vars()のテスト。"""

    def test_expand_single_env_var(self, monkeypatch):
        """単一の環境変数が展開されることを確認。"""
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key-value")
        mgr = Config_Manager()
        result = mgr._expand_env_vars("${TEST_API_KEY}")
        assert result == "sk-test-key-value"

    def test_expand_multiple_env_vars(self, monkeypatch):
        """複数の環境変数が展開されることを確認。"""
        monkeypatch.setenv("HOST", "localhost")
        monkeypatch.setenv("PORT", "8080")
        mgr = Config_Manager()
        result = mgr._expand_env_vars("${HOST}:${PORT}")
        assert result == "localhost:8080"

    def test_expand_missing_env_var_returns_empty(self, monkeypatch):
        """未設定の環境変数は空文字列に展開されることを確認。"""
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)
        mgr = Config_Manager()
        result = mgr._expand_env_vars("${NONEXISTENT_VAR}")
        assert result == ""

    def test_no_env_vars_returns_unchanged(self):
        """環境変数パターンがない場合はそのまま返されることを確認。"""
        mgr = Config_Manager()
        result = mgr._expand_env_vars("plain-text-value")
        assert result == "plain-text-value"

    def test_env_var_in_config_file(self, monkeypatch, tmp_path):
        """設定ファイル内の環境変数が展開されることを確認。"""
        monkeypatch.setenv("MY_API_KEY", "sk-real-key-from-env")
        config_data = {
            "api": {
                "provider": "openai",
                "api_key": "${MY_API_KEY}",
                "model": "gpt-4",
            },
            "common": {"temperature": 0.7, "max_tokens": 2000},
        }
        config_path = tmp_path / "env_config.yaml"
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        mgr = Config_Manager()
        config = mgr.load_config(str(config_path))
        assert config.api_key == "sk-real-key-from-env"

    def test_unset_env_var_results_in_none_api_key(self, monkeypatch, tmp_path):
        """未設定の環境変数はapi_keyがNoneになることを確認。"""
        monkeypatch.delenv("UNSET_KEY", raising=False)
        config_data = {
            "api": {
                "provider": "openai",
                "api_key": "${UNSET_KEY}",
                "model": "gpt-4",
            },
            "common": {"temperature": 0.7, "max_tokens": 2000},
        }
        config_path = tmp_path / "unset_env.yaml"
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        mgr = Config_Manager()
        config = mgr.load_config(str(config_path))
        assert config.api_key is None


class TestValidateConfig:
    """_validate_config()のテスト。"""

    def test_missing_api_section_raises_error(self):
        """apiセクションが無い場合にConfigurationErrorが送出されることを確認。"""
        mgr = Config_Manager()
        with pytest.raises(ConfigurationError):
            mgr._validate_config({"common": {"temperature": 0.7, "max_tokens": 2000}})

    def test_missing_common_section_raises_error(self):
        """commonセクションが無い場合にConfigurationErrorが送出されることを確認。"""
        mgr = Config_Manager()
        with pytest.raises(ConfigurationError):
            mgr._validate_config({"api": {"provider": "openai", "model": "gpt-4"}})

    def test_invalid_provider_raises_error(self):
        """不正なプロバイダーでConfigurationErrorが送出されることを確認。"""
        mgr = Config_Manager()
        with pytest.raises(ConfigurationError, match="不正なAPIプロバイダー"):
            mgr._validate_config(
                {
                    "api": {"provider": "invalid_provider", "model": "gpt-4"},
                    "common": {"temperature": 0.7, "max_tokens": 2000},
                }
            )

    def test_temperature_out_of_range_raises_error(self):
        """temperatureが範囲外の場合にConfigurationErrorが送出されることを確認。"""
        mgr = Config_Manager()
        with pytest.raises(ConfigurationError, match="temperature"):
            mgr._validate_config(
                {
                    "api": {"provider": "openai", "model": "gpt-4"},
                    "common": {"temperature": 3.0, "max_tokens": 2000},
                }
            )

    def test_negative_max_tokens_raises_error(self):
        """max_tokensが0以下の場合にConfigurationErrorが送出されることを確認。"""
        mgr = Config_Manager()
        with pytest.raises(ConfigurationError, match="max_tokens"):
            mgr._validate_config(
                {
                    "api": {"provider": "openai", "model": "gpt-4"},
                    "common": {"temperature": 0.7, "max_tokens": -100},
                }
            )

    def test_invalid_log_level_raises_error(self):
        """不正なログレベルでConfigurationErrorが送出されることを確認。"""
        mgr = Config_Manager()
        with pytest.raises(ConfigurationError, match="不正なログレベル"):
            mgr._validate_config(
                {
                    "api": {"provider": "openai", "model": "gpt-4"},
                    "common": {"temperature": 0.7, "max_tokens": 2000},
                    "logging": {"level": "INVALID"},
                }
            )

    def test_invalid_backend_raises_error(self):
        """不正なバックエンドでConfigurationErrorが送出されることを確認。"""
        mgr = Config_Manager()
        with pytest.raises(
            ConfigurationError, match="不正なローカルモデルバックエンド"
        ):
            mgr._validate_config(
                {
                    "api": {"provider": "openai", "model": "gpt-4"},
                    "common": {"temperature": 0.7, "max_tokens": 2000},
                    "local": {"backend": "invalid_backend"},
                }
            )

    def test_invalid_yaml_content_raises_error(self, tmp_path):
        """不正なYAMLファイルでConfigurationErrorが送出されることを確認。"""
        config_path = tmp_path / "invalid.yaml"
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("invalid: yaml: content: [broken")

        mgr = Config_Manager()
        with pytest.raises(ConfigurationError):
            mgr.load_config(str(config_path))

    def test_empty_yaml_file_raises_error(self, tmp_path):
        """空のYAMLファイルでConfigurationErrorが送出されることを確認。"""
        config_path = tmp_path / "empty.yaml"
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("")

        mgr = Config_Manager()
        with pytest.raises(ConfigurationError, match="空"):
            mgr.load_config(str(config_path))

    def test_non_dict_config_raises_error(self, tmp_path):
        """辞書でない設定でConfigurationErrorが送出されることを確認。"""
        config_path = tmp_path / "list.yaml"
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(["item1", "item2"], f)

        mgr = Config_Manager()
        with pytest.raises(ConfigurationError):
            mgr.load_config(str(config_path))

    def test_missing_provider_raises_error(self):
        """providerが未設定の場合にConfigurationErrorが送出されることを確認。"""
        mgr = Config_Manager()
        with pytest.raises(ConfigurationError, match="provider"):
            mgr._validate_config(
                {
                    "api": {"model": "gpt-4"},
                    "common": {"temperature": 0.7, "max_tokens": 2000},
                }
            )
