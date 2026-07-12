"""カスタム例外クラスモジュール。

チャットアプリケーション全体で使用するカスタム例外を定義する。
各例外クラスはユーザーフレンドリーな日本語エラーメッセージテンプレートと
推奨される対処法を含む。

Requirements: 8.1, 8.2, 8.3
"""

from __future__ import annotations

from typing import Optional


class ChatAppError(Exception):
    """チャットアプリケーションの基底例外クラス。

    すべてのカスタム例外はこのクラスを継承する。
    日本語のユーザーフレンドリーメッセージと対処法を提供する。

    Attributes:
        default_message: デフォルトの日本語エラーメッセージテンプレート
        guidance: エラー発生時の推奨対処法
        details: エラーの追加コンテキスト情報
    """

    default_message: str = "アプリケーションでエラーが発生しました。"
    guidance: str = "アプリケーションを再起動してください。問題が続く場合はログを確認してください。"

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[str] = None,
    ) -> None:
        """例外を初期化する。

        Args:
            message: カスタムエラーメッセージ。Noneの場合はdefault_messageを使用。
            details: エラーの追加コンテキスト情報。
        """
        self._custom_message = message
        self.details = details
        super().__init__(self.user_message)

    @property
    def user_message(self) -> str:
        """ユーザーフレンドリーな日本語エラーメッセージを返す。

        カスタムメッセージが設定されている場合はそれを返し、
        そうでなければデフォルトメッセージを返す。

        Returns:
            ユーザー向けの日本語エラーメッセージ。
        """
        return self._custom_message if self._custom_message else self.default_message

    @property
    def full_message(self) -> str:
        """エラーメッセージと対処法を含む完全なメッセージを返す。

        Returns:
            エラーメッセージ、詳細情報（あれば）、対処法を結合した文字列。
        """
        parts = [self.user_message]
        if self.details:
            parts.append(f"詳細: {self.details}")
        parts.append(f"対処法: {self.guidance}")
        return "\n".join(parts)


class NetworkError(ChatAppError):
    """ネットワーク関連のエラー。

    API呼び出し時の接続タイムアウト、DNS解決失敗、
    ネットワーク接続なしなどの場合に送出される。

    Validates: Requirement 8.1
    """

    default_message: str = "ネットワークエラーが発生しました。"
    guidance: str = (
        "以下を確認してください:\n"
        "  1. インターネット接続を確認してください\n"
        "  2. プロキシ設定を確認してください\n"
        "  3. ファイアウォール設定を確認してください"
    )


class AuthenticationError(ChatAppError):
    """認証関連のエラー。

    API_Keyが無効、未設定、権限不足などの場合に送出される。

    Validates: Requirement 8.2
    """

    default_message: str = "API認証に失敗しました。"
    guidance: str = (
        "以下を確認してください:\n"
        "  1. config.yamlのapi_keyが正しく設定されているか確認してください\n"
        "  2. 環境変数（例: OPENAI_API_KEY）が設定されているか確認してください\n"
        "  3. API_Keyの有効期限を確認してください\n"
        "  4. APIプロバイダーのダッシュボードでAPI_Keyを再発行してください"
    )


class RateLimitError(ChatAppError):
    """レート制限エラー。

    API呼び出し頻度が制限を超えた場合に送出される。
    """

    default_message: str = "API呼び出しのレート制限に達しました。"
    guidance: str = (
        "以下を確認してください:\n"
        "  1. しばらく待ってから再試行してください\n"
        "  2. APIプランのアップグレードを検討してください"
    )


class ModelLoadError(ChatAppError):
    """モデルロードエラー。

    ローカルモデルの初期化時にファイル不在、メモリ不足、
    GPU利用不可などの場合に送出される。

    Validates: Requirement 8.3
    """

    default_message: str = "モデルのロードに失敗しました。"
    guidance: str = (
        "以下を確認してください:\n"
        "  1. モデルファイルのパスが正しいか確認してください\n"
        "  2. モデルファイルがダウンロード済みか確認してください\n"
        "  3. システムメモリ（RAM）に十分な空きがあるか確認してください\n"
        "  4. より小さいモデル（7Bパラメータ推奨）の使用を検討してください\n"
        "  5. n_ctx設定値を小さくしてください（推奨: 512-2048）"
    )


class FileFormatError(ChatAppError):
    """ファイル形式エラー。

    会話履歴や設定ファイルの読み込み時に形式が不正な場合に送出される。
    """

    default_message: str = "ファイルの形式が不正です。"
    guidance: str = (
        "以下を確認してください:\n"
        "  1. ファイルが破損していないか確認してください\n"
        "  2. 正しいJSON/YAML形式であるか確認してください\n"
        "  3. 別のファイルを読み込むか、新しい会話を開始してください"
    )


class ConfigurationError(ChatAppError):
    """設定エラー。

    設定ファイルの読み込みや検証に失敗した場合に送出される。
    """

    default_message: str = "設定ファイルの読み込みに失敗しました。"
    guidance: str = (
        "以下を確認してください:\n"
        "  1. config.yamlが存在するか確認してください\n"
        "  2. YAML形式が正しいか確認してください\n"
        "  3. 必須項目（provider, model等）が設定されているか確認してください\n"
        "  4. config.yaml.exampleを参考に設定ファイルを再作成してください"
    )
