"""History_Managerの単体テスト。

会話履歴の追加・取得・クリア・永続化・トークン制限管理の
動作を検証する。
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from llm_chat_app.core.history import History_Manager
from llm_chat_app.exceptions import FileFormatError
from llm_chat_app.models import Message


class TestHistoryManagerInit:
    """History_Managerの初期化テスト"""

    def test_初期化時にセッションIDが生成される(self) -> None:
        """初期化時にUUID形式のセッションIDが生成されることを検証"""
        manager = History_Manager()
        assert manager.conversation.session_id is not None
        assert len(manager.conversation.session_id) == 36  # UUID4の文字列長

    def test_初期化時にメッセージリストが空である(self) -> None:
        """初期化時に会話履歴が空であることを検証"""
        manager = History_Manager()
        assert manager.conversation.messages == []

    def test_デフォルトmax_tokensが4000である(self) -> None:
        """デフォルトのmax_tokensが4000であることを検証"""
        manager = History_Manager()
        assert manager.max_tokens == 4000

    def test_カスタムmax_tokensを指定できる(self) -> None:
        """カスタムのmax_tokens値を指定して初期化できることを検証"""
        manager = History_Manager(max_tokens=2000)
        assert manager.max_tokens == 2000

    def test_各インスタンスで異なるセッションIDが生成される(self) -> None:
        """複数インスタンスで異なるセッションIDが生成されることを検証"""
        manager1 = History_Manager()
        manager2 = History_Manager()
        assert manager1.conversation.session_id != manager2.conversation.session_id


class TestAddMessage:
    """add_message()のテスト"""

    def test_メッセージを追加できる(self) -> None:
        """メッセージが正しく追加されることを検証"""
        manager = History_Manager()
        msg = Message(role="user", content="こんにちは", timestamp=time.time())
        manager.add_message(msg)
        assert len(manager.conversation.messages) == 1
        assert manager.conversation.messages[0].content == "こんにちは"

    def test_複数メッセージを追加順序で保持する(self) -> None:
        """複数メッセージが追加順に保持されることを検証"""
        manager = History_Manager()
        msg1 = Message(role="user", content="最初", timestamp=1.0)
        msg2 = Message(role="assistant", content="応答", timestamp=2.0)
        manager.add_message(msg1)
        manager.add_message(msg2)
        assert len(manager.conversation.messages) == 2
        assert manager.conversation.messages[0].content == "最初"
        assert manager.conversation.messages[1].content == "応答"

    def test_追加後にupdated_atが更新される(self) -> None:
        """メッセージ追加後にupdated_atが更新されることを検証"""
        manager = History_Manager()
        original_updated = manager.conversation.updated_at
        time.sleep(0.01)
        msg = Message(role="user", content="テスト", timestamp=time.time())
        manager.add_message(msg)
        assert manager.conversation.updated_at >= original_updated


class TestGetMessages:
    """get_messages()のテスト"""

    def test_空の場合は空リストを返す(self) -> None:
        """履歴が空の場合に空リストを返すことを検証"""
        manager = History_Manager()
        assert manager.get_messages() == []

    def test_コピーを返す(self) -> None:
        """返されるリストが元のリストのコピーであることを検証"""
        manager = History_Manager()
        msg = Message(role="user", content="テスト", timestamp=time.time())
        manager.add_message(msg)
        messages = manager.get_messages()
        messages.clear()
        # 元のリストには影響しない
        assert len(manager.conversation.messages) == 1

    def test_追加したメッセージが取得できる(self) -> None:
        """追加したメッセージがget_messages()で取得できることを検証"""
        manager = History_Manager()
        msg = Message(role="user", content="こんにちは", timestamp=1.0)
        manager.add_message(msg)
        result = manager.get_messages()
        assert len(result) == 1
        assert result[0].role == "user"
        assert result[0].content == "こんにちは"


class TestClearHistory:
    """clear_history()のテスト"""

    def test_履歴がクリアされる(self) -> None:
        """clear_history()後に履歴が空になることを検証"""
        manager = History_Manager()
        msg = Message(role="user", content="テスト", timestamp=time.time())
        manager.add_message(msg)
        manager.clear_history()
        assert manager.get_messages() == []

    def test_total_tokensがリセットされる(self) -> None:
        """clear_history()後にtotal_tokensが0になることを検証"""
        manager = History_Manager()
        msg = Message(role="user", content="テスト" * 100, timestamp=time.time())
        manager.add_message(msg)
        manager.clear_history()
        assert manager.conversation.total_tokens == 0


class TestSaveToFile:
    """save_to_file()のテスト"""

    def test_JSONファイルに保存できる(self, tmp_path: Path) -> None:
        """会話履歴がJSON形式で保存されることを検証"""
        manager = History_Manager()
        msg = Message(role="user", content="保存テスト", timestamp=1.0)
        manager.add_message(msg)

        filepath = str(tmp_path / "test_history.json")
        manager.save_to_file(filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["session_id"] == manager.conversation.session_id
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == "保存テスト"

    def test_保存データにモデル名が含まれる(self, tmp_path: Path) -> None:
        """保存データにmodel_nameが含まれることを検証"""
        manager = History_Manager()
        manager.conversation.model_name = "gpt-4"
        msg = Message(role="user", content="テスト", timestamp=1.0)
        manager.add_message(msg)

        filepath = str(tmp_path / "test.json")
        manager.save_to_file(filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["model_name"] == "gpt-4"

    def test_存在しないディレクトリに保存する場合ディレクトリが作成される(
        self, tmp_path: Path
    ) -> None:
        """保存先ディレクトリが存在しない場合に自動作成されることを検証"""
        manager = History_Manager()
        filepath = str(tmp_path / "subdir" / "deep" / "test.json")
        manager.save_to_file(filepath)
        assert Path(filepath).exists()


class TestLoadFromFile:
    """load_from_file()のテスト"""

    def test_保存したファイルを読み込める(self, tmp_path: Path) -> None:
        """save_to_fileで保存したデータをload_from_fileで復元できることを検証"""
        manager = History_Manager()
        msg1 = Message(role="user", content="質問", timestamp=1.0)
        msg2 = Message(role="assistant", content="回答", timestamp=2.0)
        manager.add_message(msg1)
        manager.add_message(msg2)
        manager.conversation.model_name = "gpt-4"

        filepath = str(tmp_path / "test.json")
        manager.save_to_file(filepath)

        # 新しいインスタンスで読み込み
        new_manager = History_Manager()
        new_manager.load_from_file(filepath)

        assert new_manager.conversation.session_id == manager.conversation.session_id
        assert len(new_manager.conversation.messages) == 2
        assert new_manager.conversation.messages[0].content == "質問"
        assert new_manager.conversation.messages[1].content == "回答"
        assert new_manager.conversation.model_name == "gpt-4"

    def test_存在しないファイルでFileNotFoundErrorが発生する(self) -> None:
        """存在しないファイルを指定した場合にFileNotFoundErrorが発生することを検証"""
        manager = History_Manager()
        with pytest.raises(FileNotFoundError):
            manager.load_from_file("nonexistent_file.json")

    def test_不正なJSONでFileFormatErrorが発生する(self, tmp_path: Path) -> None:
        """不正なJSON形式のファイルでFileFormatErrorが発生することを検証"""
        filepath = tmp_path / "invalid.json"
        filepath.write_text("{ invalid json }", encoding="utf-8")

        manager = History_Manager()
        with pytest.raises(FileFormatError):
            manager.load_from_file(str(filepath))

    def test_不正なデータ構造でFileFormatErrorが発生する(self, tmp_path: Path) -> None:
        """必須フィールドが欠けたデータでFileFormatErrorが発生することを検証"""
        filepath = tmp_path / "bad_structure.json"
        filepath.write_text(json.dumps({"invalid": "data"}), encoding="utf-8")

        manager = History_Manager()
        with pytest.raises(FileFormatError):
            manager.load_from_file(str(filepath))


class TestTrimHistory:
    """_trim_history_if_needed()のテスト"""

    def test_トークン制限内ではトリミングされない(self) -> None:
        """トークン制限内のメッセージはトリミングされないことを検証"""
        manager = History_Manager(max_tokens=1000)
        msg = Message(role="user", content="短いメッセージ", timestamp=1.0)
        manager.add_message(msg)
        assert len(manager.conversation.messages) == 1

    def test_トークン制限超過時に古いメッセージが削除される(self) -> None:
        """トークン制限を超過した場合に古いメッセージが削除されることを検証"""
        # max_tokens=10で非常に低い制限を設定
        manager = History_Manager(max_tokens=10)
        # 長いメッセージを追加してトークン制限を超過させる
        msg1 = Message(role="user", content="a" * 100, timestamp=1.0)
        msg2 = Message(role="assistant", content="b" * 100, timestamp=2.0)
        msg3 = Message(role="user", content="c" * 20, timestamp=3.0)
        manager.add_message(msg1)
        manager.add_message(msg2)
        manager.add_message(msg3)

        # メッセージが削減されている
        assert len(manager.conversation.messages) < 3

    def test_システムメッセージはトリミングで保持される(self) -> None:
        """トリミング時にシステムメッセージ（role="system"）が保持されることを検証"""
        manager = History_Manager(max_tokens=10)
        system_msg = Message(
            role="system", content="あなたはアシスタントです。" * 5, timestamp=1.0
        )
        user_msg = Message(role="user", content="x" * 200, timestamp=2.0)
        assistant_msg = Message(role="assistant", content="y" * 200, timestamp=3.0)

        manager.add_message(system_msg)
        manager.add_message(user_msg)
        manager.add_message(assistant_msg)

        # システムメッセージが保持されているか確認
        remaining_roles = [msg.role for msg in manager.conversation.messages]
        assert "system" in remaining_roles
