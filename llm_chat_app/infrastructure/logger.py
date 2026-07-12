"""
ロガー設定モジュール

RotatingFileHandler付きのロガーを提供します。
- ログフォーマット: %(asctime)s - %(name)s - %(levelname)s - %(message)s
- 10MB上限のローテーション（5世代バックアップ）
- コンソール出力（WARNING以上）とファイル出力を併用
"""

import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logger(
    name: str = "llm_chat_app",
    log_file: str = "logs/chat.log",
    log_level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """ロガーのセットアップ。

    RotatingFileHandler付きのロガーを設定する。
    同じ名前で複数回呼び出された場合はハンドラーの重複追加を防ぐ。

    Args:
        name: ロガー名
        log_file: ログファイルのパス
        log_level: ログレベル（"DEBUG" | "INFO" | "WARNING" | "ERROR"）
        max_bytes: ログファイルの最大サイズ（バイト）。デフォルト10MB
        backup_count: ローテーション時のバックアップファイル数

    Returns:
        設定済みのLoggerインスタンス
    """
    logger = logging.getLogger(name)

    # 既にハンドラーが設定済みの場合は既存のロガーを返す（冪等性）
    if logger.handlers:
        return logger

    # ログレベルを設定
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)

    # ログフォーマット
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # ログディレクトリを作成（存在しない場合）
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # ファイルハンドラー（RotatingFileHandler）
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # コンソールハンドラー（WARNING以上を表示）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
