"""ロガーモジュールのテスト"""

import logging
import os

import pytest

from llm_chat_app.infrastructure.logger import setup_logger


@pytest.fixture(autouse=True)
def cleanup_loggers():
    """各テスト後にテスト用ロガーをクリーンアップする。"""
    yield
    # テストで作成したロガーのハンドラーを削除
    for name in list(logging.Logger.manager.loggerDict.keys()):
        if name.startswith("test_"):
            logger = logging.getLogger(name)
            logger.handlers.clear()


class TestSetupLogger:
    """setup_logger関数のテスト"""

    def test_returns_logger_instance(self, tmp_path):
        """Loggerインスタンスが返されることを確認"""
        log_file = str(tmp_path / "test.log")
        logger = setup_logger(name="test_instance", log_file=log_file)
        assert isinstance(logger, logging.Logger)

    def test_logger_name(self, tmp_path):
        """指定した名前でロガーが作成されることを確認"""
        log_file = str(tmp_path / "test.log")
        logger = setup_logger(name="test_name", log_file=log_file)
        assert logger.name == "test_name"

    def test_default_log_level_info(self, tmp_path):
        """デフォルトログレベルがINFOであることを確認"""
        log_file = str(tmp_path / "test.log")
        logger = setup_logger(name="test_default_level", log_file=log_file)
        assert logger.level == logging.INFO

    def test_custom_log_level_debug(self, tmp_path):
        """DEBUGレベルが正しく設定されることを確認"""
        log_file = str(tmp_path / "test.log")
        logger = setup_logger(
            name="test_debug_level", log_file=log_file, log_level="DEBUG"
        )
        assert logger.level == logging.DEBUG

    def test_custom_log_level_error(self, tmp_path):
        """ERRORレベルが正しく設定されることを確認"""
        log_file = str(tmp_path / "test.log")
        logger = setup_logger(
            name="test_error_level", log_file=log_file, log_level="ERROR"
        )
        assert logger.level == logging.ERROR

    def test_custom_log_level_warning(self, tmp_path):
        """WARNINGレベルが正しく設定されることを確認"""
        log_file = str(tmp_path / "test.log")
        logger = setup_logger(
            name="test_warning_level", log_file=log_file, log_level="WARNING"
        )
        assert logger.level == logging.WARNING

    def test_has_file_handler(self, tmp_path):
        """RotatingFileHandlerが追加されていることを確認"""
        log_file = str(tmp_path / "test.log")
        logger = setup_logger(name="test_file_handler", log_file=log_file)
        file_handlers = [
            h
            for h in logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(file_handlers) == 1

    def test_has_console_handler(self, tmp_path):
        """StreamHandlerが追加されていることを確認"""
        log_file = str(tmp_path / "test.log")
        logger = setup_logger(name="test_console_handler", log_file=log_file)
        stream_handlers = [
            h
            for h in logger.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(stream_handlers) == 1

    def test_console_handler_level_warning(self, tmp_path):
        """コンソールハンドラーのレベルがWARNINGであることを確認"""
        log_file = str(tmp_path / "test.log")
        logger = setup_logger(name="test_console_level", log_file=log_file)
        stream_handlers = [
            h
            for h in logger.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert stream_handlers[0].level == logging.WARNING

    def test_log_format(self, tmp_path):
        """ログフォーマットが正しいことを確認"""
        log_file = str(tmp_path / "test.log")
        logger = setup_logger(name="test_format", log_file=log_file)
        file_handler = [
            h
            for h in logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ][0]
        expected_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        assert file_handler.formatter._fmt == expected_format

    def test_rotating_file_handler_max_bytes(self, tmp_path):
        """RotatingFileHandlerのmax_bytesが10MBであることを確認"""
        log_file = str(tmp_path / "test.log")
        logger = setup_logger(name="test_max_bytes", log_file=log_file)
        file_handler = [
            h
            for h in logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ][0]
        assert file_handler.maxBytes == 10 * 1024 * 1024

    def test_rotating_file_handler_backup_count(self, tmp_path):
        """RotatingFileHandlerのbackup_countが5であることを確認"""
        log_file = str(tmp_path / "test.log")
        logger = setup_logger(name="test_backup_count", log_file=log_file)
        file_handler = [
            h
            for h in logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ][0]
        assert file_handler.backupCount == 5

    def test_idempotent_no_duplicate_handlers(self, tmp_path):
        """同じ名前で複数回呼び出してもハンドラーが重複しないことを確認"""
        log_file = str(tmp_path / "test.log")
        logger1 = setup_logger(name="test_idempotent", log_file=log_file)
        logger2 = setup_logger(name="test_idempotent", log_file=log_file)
        assert logger1 is logger2
        assert len(logger1.handlers) == 2  # ファイル + コンソール

    def test_creates_log_directory(self, tmp_path):
        """ログディレクトリが自動作成されることを確認"""
        log_file = str(tmp_path / "subdir" / "nested" / "test.log")
        setup_logger(name="test_mkdir", log_file=log_file)
        assert os.path.isdir(str(tmp_path / "subdir" / "nested"))

    def test_writes_log_to_file(self, tmp_path):
        """ログメッセージがファイルに書き込まれることを確認"""
        log_file = str(tmp_path / "test.log")
        logger = setup_logger(name="test_write", log_file=log_file)
        logger.info("テストメッセージ")

        # ハンドラーをフラッシュ
        for handler in logger.handlers:
            handler.flush()

        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()

        assert "テストメッセージ" in content
        assert "test_write" in content
        assert "INFO" in content

    def test_respects_log_level_filtering(self, tmp_path):
        """ログレベル以下のメッセージがフィルタされることを確認"""
        log_file = str(tmp_path / "test.log")
        logger = setup_logger(
            name="test_filter", log_file=log_file, log_level="WARNING"
        )
        logger.info("このメッセージは記録されない")
        logger.warning("このメッセージは記録される")

        for handler in logger.handlers:
            handler.flush()

        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()

        assert "このメッセージは記録されない" not in content
        assert "このメッセージは記録される" in content

    def test_custom_max_bytes_and_backup_count(self, tmp_path):
        """カスタムのmax_bytesとbackup_countが設定されることを確認"""
        log_file = str(tmp_path / "test.log")
        logger = setup_logger(
            name="test_custom_rotation",
            log_file=log_file,
            max_bytes=5 * 1024 * 1024,
            backup_count=3,
        )
        file_handler = [
            h
            for h in logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ][0]
        assert file_handler.maxBytes == 5 * 1024 * 1024
        assert file_handler.backupCount == 3
