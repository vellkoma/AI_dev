"""カスタム例外クラスのユニットテスト。"""

import pytest

from llm_chat_app.exceptions import (
    AuthenticationError,
    ChatAppError,
    ConfigurationError,
    FileFormatError,
    ModelLoadError,
    NetworkError,
    RateLimitError,
)


class TestChatAppError:
    """基底例外クラスのテスト。"""

    def test_default_message(self) -> None:
        """デフォルトメッセージが正しく設定される。"""
        error = ChatAppError()
        assert error.user_message == "アプリケーションでエラーが発生しました。"

    def test_custom_message(self) -> None:
        """カスタムメッセージが正しく設定される。"""
        custom = "カスタムエラーメッセージ"
        error = ChatAppError(message=custom)
        assert error.user_message == custom

    def test_details_attribute(self) -> None:
        """details属性が正しく設定される。"""
        error = ChatAppError(details="追加情報")
        assert error.details == "追加情報"

    def test_details_default_none(self) -> None:
        """details属性のデフォルト値はNone。"""
        error = ChatAppError()
        assert error.details is None

    def test_is_exception(self) -> None:
        """Exceptionを継承している。"""
        error = ChatAppError()
        assert isinstance(error, Exception)

    def test_str_representation(self) -> None:
        """str()でuser_messageが返される。"""
        error = ChatAppError()
        assert str(error) == "アプリケーションでエラーが発生しました。"

    def test_raise_and_catch(self) -> None:
        """raiseしてcatchできる。"""
        with pytest.raises(ChatAppError):
            raise ChatAppError()

    def test_guidance_attribute(self) -> None:
        """guidance属性が設定されている。"""
        error = ChatAppError()
        assert error.guidance is not None
        assert len(error.guidance) > 0

    def test_full_message_without_details(self) -> None:
        """full_messageがメッセージと対処法を含む。"""
        error = ChatAppError()
        full = error.full_message
        assert "アプリケーションでエラーが発生しました。" in full
        assert "対処法:" in full

    def test_full_message_with_details(self) -> None:
        """full_messageに詳細情報が含まれる。"""
        error = ChatAppError(details="接続タイムアウト")
        full = error.full_message
        assert "詳細: 接続タイムアウト" in full
        assert "対処法:" in full


class TestNetworkError:
    """ネットワークエラーのテスト。"""

    def test_inherits_chat_app_error(self) -> None:
        """ChatAppErrorを継承している。"""
        error = NetworkError()
        assert isinstance(error, ChatAppError)

    def test_default_message(self) -> None:
        """デフォルトメッセージが日本語で設定される。"""
        error = NetworkError()
        assert "ネットワークエラー" in error.user_message

    def test_guidance_contains_remediation(self) -> None:
        """対処法にインターネット接続確認が含まれる。"""
        error = NetworkError()
        assert "インターネット接続" in error.guidance
        assert "プロキシ" in error.guidance
        assert "ファイアウォール" in error.guidance

    def test_custom_message_overrides(self) -> None:
        """カスタムメッセージがデフォルトを上書きする。"""
        custom = "接続タイムアウト"
        error = NetworkError(message=custom)
        assert error.user_message == custom

    def test_with_details(self) -> None:
        """details付きで生成できる。"""
        error = NetworkError(details="Connection timeout after 30s")
        assert error.details == "Connection timeout after 30s"

    def test_full_message_includes_guidance(self) -> None:
        """full_messageにエラー種類と対処法が表示される（Req 8.1）。"""
        error = NetworkError(details="Connection refused")
        full = error.full_message
        assert "ネットワークエラー" in full
        assert "詳細: Connection refused" in full
        assert "インターネット接続" in full


class TestAuthenticationError:
    """認証エラーのテスト。"""

    def test_inherits_chat_app_error(self) -> None:
        """ChatAppErrorを継承している。"""
        error = AuthenticationError()
        assert isinstance(error, ChatAppError)

    def test_default_message(self) -> None:
        """デフォルトメッセージが日本語で設定される。"""
        error = AuthenticationError()
        assert "API認証" in error.user_message

    def test_guidance_contains_setup_instructions(self) -> None:
        """対処法にAPI_Key設定方法が含まれる（Req 8.2）。"""
        error = AuthenticationError()
        assert "config.yaml" in error.guidance
        assert "API_Key" in error.guidance
        assert "再発行" in error.guidance

    def test_custom_message_overrides(self) -> None:
        """カスタムメッセージがデフォルトを上書きする。"""
        custom = "APIキーが無効です"
        error = AuthenticationError(message=custom)
        assert error.user_message == custom


class TestRateLimitError:
    """レート制限エラーのテスト。"""

    def test_inherits_chat_app_error(self) -> None:
        """ChatAppErrorを継承している。"""
        error = RateLimitError()
        assert isinstance(error, ChatAppError)

    def test_default_message(self) -> None:
        """デフォルトメッセージが日本語で設定される。"""
        error = RateLimitError()
        assert "レート制限" in error.user_message

    def test_guidance_contains_remediation(self) -> None:
        """対処法に再試行案内が含まれる。"""
        error = RateLimitError()
        assert "再試行" in error.guidance
        assert "アップグレード" in error.guidance


class TestModelLoadError:
    """モデルロードエラーのテスト。"""

    def test_inherits_chat_app_error(self) -> None:
        """ChatAppErrorを継承している。"""
        error = ModelLoadError()
        assert isinstance(error, ChatAppError)

    def test_default_message(self) -> None:
        """デフォルトメッセージが日本語で設定される。"""
        error = ModelLoadError()
        assert "モデルのロード" in error.user_message

    def test_guidance_contains_resource_info(self) -> None:
        """対処法にリソース情報が含まれる（Req 8.3）。"""
        error = ModelLoadError()
        assert "モデルファイル" in error.guidance
        assert "メモリ" in error.guidance
        assert "n_ctx" in error.guidance

    def test_full_message_shows_failure_reason_and_resources(self) -> None:
        """full_messageに失敗理由と必要リソース情報を表示（Req 8.3）。"""
        error = ModelLoadError(details="FileNotFoundError: model.gguf")
        full = error.full_message
        assert "モデルのロード" in full
        assert "FileNotFoundError" in full
        assert "メモリ" in full


class TestFileFormatError:
    """ファイル形式エラーのテスト。"""

    def test_inherits_chat_app_error(self) -> None:
        """ChatAppErrorを継承している。"""
        error = FileFormatError()
        assert isinstance(error, ChatAppError)

    def test_default_message(self) -> None:
        """デフォルトメッセージが日本語で設定される。"""
        error = FileFormatError()
        assert "ファイルの形式" in error.user_message

    def test_guidance_contains_remediation(self) -> None:
        """対処法にファイル確認手順が含まれる。"""
        error = FileFormatError()
        assert "破損" in error.guidance
        assert "JSON" in error.guidance


class TestConfigurationError:
    """設定エラーのテスト。"""

    def test_inherits_chat_app_error(self) -> None:
        """ChatAppErrorを継承している。"""
        error = ConfigurationError()
        assert isinstance(error, ChatAppError)

    def test_default_message(self) -> None:
        """デフォルトメッセージが日本語で設定される。"""
        error = ConfigurationError()
        assert "設定ファイル" in error.user_message

    def test_guidance_contains_remediation(self) -> None:
        """対処法に設定方法の案内が含まれる。"""
        error = ConfigurationError()
        assert "config.yaml" in error.guidance
        assert "YAML" in error.guidance


class TestExceptionHierarchy:
    """例外クラスの継承階層テスト。"""

    def test_all_errors_catchable_as_chat_app_error(self) -> None:
        """すべてのカスタム例外はChatAppErrorとしてcatchできる。"""
        exceptions = [
            NetworkError(),
            AuthenticationError(),
            RateLimitError(),
            ModelLoadError(),
            FileFormatError(),
            ConfigurationError(),
        ]
        for exc in exceptions:
            assert isinstance(exc, ChatAppError)
            assert isinstance(exc, Exception)

    def test_specific_exception_not_caught_by_sibling(self) -> None:
        """兄弟例外はお互いにcatchしない。"""
        with pytest.raises(NetworkError):
            try:
                raise NetworkError()
            except AuthenticationError:
                pass

    def test_all_exceptions_have_guidance(self) -> None:
        """すべての例外クラスが対処法を持つ。"""
        exceptions = [
            ChatAppError(),
            NetworkError(),
            AuthenticationError(),
            RateLimitError(),
            ModelLoadError(),
            FileFormatError(),
            ConfigurationError(),
        ]
        for exc in exceptions:
            assert hasattr(exc, "guidance")
            assert len(exc.guidance) > 0

    def test_all_exceptions_have_full_message(self) -> None:
        """すべての例外クラスがfull_messageを生成できる。"""
        exceptions = [
            ChatAppError(),
            NetworkError(),
            AuthenticationError(),
            RateLimitError(),
            ModelLoadError(),
            FileFormatError(),
            ConfigurationError(),
        ]
        for exc in exceptions:
            full = exc.full_message
            assert "対処法:" in full
