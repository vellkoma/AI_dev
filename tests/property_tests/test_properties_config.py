"""Config_Managerのプロパティベーステスト。

Property 9: 設定ファイルのラウンドトリップ
任意の有効な設定データ（AppConfig）に対して、YAML形式で保存してから
読み込むと、元の設定データと同等の値が復元される。

**Validates: Requirements 7.1, 7.2**

テストフレームワーク: Hypothesis
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from llm_chat_app.infrastructure.config import Config_Manager
from llm_chat_app.models import AppConfig


# ===== 戦略（Strategy）定義 =====

# 有効なAPIプロバイダー
valid_providers = st.sampled_from(["openai", "claude", "gemini"])

# 有効なローカルバックエンド
valid_backends = st.sampled_from(["llama_cpp", "ollama"])

# 有効なログレベル
valid_log_levels = st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR"])

# temperature: 0.0〜2.0の範囲
valid_temperature = st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False)

# max_tokens: 正の整数
valid_max_tokens = st.integers(min_value=1, max_value=100000)

# history_max_tokens: 正の整数
valid_history_max_tokens = st.integers(min_value=1, max_value=200000)

# APIキー: $や{を含まない文字列（環境変数展開を避けるため）
# 最低1文字の英数字文字列を生成
valid_api_key = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N"),
        whitelist_characters="-_"
    ),
    min_size=1,
    max_size=64,
)

# モデル名: 空でない英数字・ハイフン・ドット文字列
valid_model_name = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N"),
        whitelist_characters="-_."
    ),
    min_size=1,
    max_size=50,
)

# ローカルモデルパス: $や{を含まない文字列
valid_model_path = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N"),
        whitelist_characters="-_./\\"
    ),
    min_size=1,
    max_size=100,
)

# n_ctx: 正の整数
valid_n_ctx = st.integers(min_value=128, max_value=32768)

# n_gpu_layers: 0以上の整数
valid_n_gpu_layers = st.integers(min_value=0, max_value=100)

# log_enabled: ブール値
valid_log_enabled = st.booleans()

# ログファイルパス: $や{を含まない文字列
valid_log_file = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N"),
        whitelist_characters="-_./\\"
    ),
    min_size=1,
    max_size=50,
)


@st.composite
def valid_config_dict_strategy(draw):
    """Config_Managerが受け付ける有効なYAML設定辞書を生成する戦略。

    apiセクションとcommonセクションは必須。
    localセクションとloggingセクションはオプション。
    """
    # 必須: apiセクション
    provider = draw(valid_providers)
    api_key = draw(valid_api_key)
    model = draw(valid_model_name)

    api_section = {
        "provider": provider,
        "api_key": api_key,
        "model": model,
    }

    # 必須: commonセクション
    temperature = draw(valid_temperature)
    max_tokens = draw(valid_max_tokens)
    history_max_tokens = draw(valid_history_max_tokens)

    common_section = {
        "temperature": temperature,
        "max_tokens": max_tokens,
        "history_max_tokens": history_max_tokens,
    }

    config_dict = {
        "api": api_section,
        "common": common_section,
    }

    # オプション: localセクション
    include_local = draw(st.booleans())
    if include_local:
        backend = draw(valid_backends)
        model_path = draw(valid_model_path)
        n_ctx = draw(valid_n_ctx)
        n_gpu_layers = draw(valid_n_gpu_layers)

        config_dict["local"] = {
            "backend": backend,
            "model_path": model_path,
            "n_ctx": n_ctx,
            "n_gpu_layers": n_gpu_layers,
        }

    # オプション: loggingセクション
    include_logging = draw(st.booleans())
    if include_logging:
        log_enabled = draw(valid_log_enabled)
        log_level = draw(valid_log_levels)
        log_file = draw(valid_log_file)

        config_dict["logging"] = {
            "enabled": log_enabled,
            "level": log_level,
            "file": log_file,
        }

    return config_dict


# ===== プロパティテスト =====


class TestConfigRoundTrip:
    """設定ファイルのラウンドトリッププロパティテスト。

    **Validates: Requirements 7.1, 7.2**
    """

    @given(config_data=valid_config_dict_strategy())
    @settings(max_examples=100, deadline=None)
    def test_yaml_roundtrip_preserves_all_fields(self, config_data: dict) -> None:
        """Property 9: 有効な設定をYAMLで保存→読み込みすると全フィールドが復元される。

        **Validates: Requirements 7.1, 7.2**

        任意の有効な設定辞書に対して:
        1. 一時ファイルにYAML形式で保存
        2. Config_Manager.load_config()で読み込み
        3. 元のデータと読み込んだAppConfigの各フィールドが一致することを検証
        """
        # シングルトンをリセット
        Config_Manager.reset_instance()

        try:
            # 一時ファイルにYAML形式で保存
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".yaml",
                delete=False,
                encoding="utf-8",
            ) as f:
                yaml.dump(
                    config_data,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                )
                temp_path = f.name

            # Config_Managerで読み込み
            mgr = Config_Manager()
            loaded_config = mgr.load_config(temp_path)

            # 型の確認
            assert isinstance(loaded_config, AppConfig)

            # apiセクションの検証
            api_section = config_data["api"]
            assert loaded_config.api_provider == api_section["provider"]
            assert loaded_config.api_key == api_section["api_key"]
            assert loaded_config.api_model == api_section["model"]

            # commonセクションの検証
            common_section = config_data["common"]
            assert loaded_config.temperature == float(common_section["temperature"])
            assert loaded_config.max_tokens == int(common_section["max_tokens"])
            assert loaded_config.history_max_tokens == int(
                common_section["history_max_tokens"]
            )

            # localセクションの検証（存在する場合）
            if "local" in config_data:
                local_section = config_data["local"]
                assert loaded_config.local_backend == local_section["backend"]
                assert loaded_config.local_model_path == local_section["model_path"]
                assert loaded_config.local_n_ctx == local_section["n_ctx"]
                assert loaded_config.local_n_gpu_layers == local_section["n_gpu_layers"]
            else:
                # localセクションが無い場合はデフォルト値
                assert loaded_config.local_backend is None
                assert loaded_config.local_model_path is None
                assert loaded_config.local_n_ctx == 2048
                assert loaded_config.local_n_gpu_layers == 0

            # loggingセクションの検証（存在する場合）
            if "logging" in config_data:
                logging_section = config_data["logging"]
                assert loaded_config.log_enabled == bool(logging_section["enabled"])
                assert loaded_config.log_level == logging_section["level"]
                assert loaded_config.log_file == logging_section["file"]
            else:
                # loggingセクションが無い場合はデフォルト値
                assert loaded_config.log_enabled is True
                assert loaded_config.log_level == "INFO"
                assert loaded_config.log_file == "chat.log"

        finally:
            # クリーンアップ
            Config_Manager.reset_instance()
            Path(temp_path).unlink(missing_ok=True)
