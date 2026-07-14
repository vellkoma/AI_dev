"""SessionServiceの単体テスト。

CRUD操作、検索、ソートの正当性を検証する。
"""

import tempfile
import time
from pathlib import Path

import pytest

from backend.app.services.session_service import SessionService
from llm_chat_app.models import Conversation, Message


@pytest.fixture
def tmp_storage(tmp_path):
    """テスト用の一時ストレージディレクトリを提供する。"""
    return tmp_path / "sessions"


@pytest.fixture
def service(tmp_storage):
    """テスト用のSessionServiceインスタンスを提供する。"""
    return SessionService(tmp_storage)


class TestCreateSession:
    """create_session() のテスト。"""

    def test_create_session_returns_conversation(self, service):
        """新しいセッションが作成され、Conversationが返る。"""
        result = service.create_session(model_name="gpt-4")

        assert isinstance(result, Conversation)
        assert result.session_id != ""
        assert result.model_name == "gpt-4"
        assert result.messages == []
        assert result.total_tokens == 0
        assert result.created_at > 0
        assert result.updated_at > 0

    def test_create_session_persists_to_file(self, service, tmp_storage):
        """セッション作成時にJSONファイルが永続化される。"""
        result = service.create_session()
        path = tmp_storage / f"{result.session_id}.json"
        assert path.exists()

    def test_create_session_default_model_name(self, service):
        """モデル名未指定時はデフォルトの空文字列。"""
        result = service.create_session()
        assert result.model_name == ""


class TestGetSession:
    """get_session() のテスト。"""

    def test_get_existing_session(self, service):
        """作成済みセッションを取得できる。"""
        created = service.create_session(model_name="gpt-4")
        retrieved = service.get_session(created.session_id)

        assert retrieved.session_id == created.session_id
        assert retrieved.model_name == created.model_name
        assert retrieved.created_at == created.created_at

    def test_get_nonexistent_session_raises(self, service):
        """存在しないセッションIDで FileNotFoundError が発生する。"""
        with pytest.raises(FileNotFoundError):
            service.get_session("nonexistent-id")


class TestUpdateSession:
    """update_session() のテスト。"""

    def test_update_messages(self, service):
        """メッセージを更新できる。"""
        created = service.create_session()
        messages = [
            Message(role="user", content="こんにちは", timestamp=time.time()),
            Message(role="assistant", content="こんにちは！", timestamp=time.time()),
        ]

        updated = service.update_session(created.session_id, messages)

        assert len(updated.messages) == 2
        assert updated.messages[0].content == "こんにちは"
        assert updated.messages[1].content == "こんにちは！"

    def test_update_updates_timestamp(self, service):
        """更新時にupdated_atが更新される。"""
        created = service.create_session()
        original_updated = created.updated_at

        time.sleep(0.01)
        service.update_session(created.session_id, [])

        retrieved = service.get_session(created.session_id)
        assert retrieved.updated_at > original_updated

    def test_update_total_tokens(self, service):
        """total_tokensを更新できる。"""
        created = service.create_session()
        service.update_session(created.session_id, [], total_tokens=150)

        retrieved = service.get_session(created.session_id)
        assert retrieved.total_tokens == 150

    def test_update_model_name(self, service):
        """model_nameを更新できる。"""
        created = service.create_session(model_name="gpt-3.5-turbo")
        service.update_session(created.session_id, [], model_name="gpt-4")

        retrieved = service.get_session(created.session_id)
        assert retrieved.model_name == "gpt-4"

    def test_update_nonexistent_session_raises(self, service):
        """存在しないセッションの更新で FileNotFoundError が発生する。"""
        with pytest.raises(FileNotFoundError):
            service.update_session("nonexistent", [])


class TestDeleteSession:
    """delete_session() のテスト。"""

    def test_delete_existing_session(self, service, tmp_storage):
        """セッションを削除するとファイルが消える。"""
        created = service.create_session()
        path = tmp_storage / f"{created.session_id}.json"
        assert path.exists()

        service.delete_session(created.session_id)
        assert not path.exists()

    def test_delete_nonexistent_session_raises(self, service):
        """存在しないセッションの削除で FileNotFoundError が発生する。"""
        with pytest.raises(FileNotFoundError):
            service.delete_session("nonexistent-id")

    def test_deleted_session_not_in_list(self, service):
        """削除後のセッションは一覧に含まれない。"""
        created = service.create_session()
        service.delete_session(created.session_id)

        sessions = service.list_sessions()
        ids = [s.session_id for s in sessions]
        assert created.session_id not in ids


class TestListSessions:
    """list_sessions() のテスト。"""

    def test_empty_list(self, service):
        """セッションがない場合は空リスト。"""
        assert service.list_sessions() == []

    def test_returns_all_sessions(self, service):
        """すべてのセッションが一覧に含まれる。"""
        service.create_session()
        service.create_session()
        service.create_session()

        sessions = service.list_sessions()
        assert len(sessions) == 3

    def test_sorted_by_updated_at_descending(self, service):
        """一覧は更新日時降順でソートされる。"""
        s1 = service.create_session()
        time.sleep(0.01)
        s2 = service.create_session()
        time.sleep(0.01)
        s3 = service.create_session()

        sessions = service.list_sessions()
        # 最新のものが先頭
        assert sessions[0].session_id == s3.session_id
        assert sessions[1].session_id == s2.session_id
        assert sessions[2].session_id == s1.session_id

    def test_summary_fields(self, service):
        """SessionSummaryに必要なフィールドが含まれる。"""
        created = service.create_session(model_name="gpt-4")
        messages = [
            Message(role="user", content="テストメッセージ", timestamp=time.time()),
        ]
        service.update_session(created.session_id, messages)

        sessions = service.list_sessions()
        summary = sessions[0]

        assert summary.session_id == created.session_id
        assert summary.created_at > 0
        assert summary.updated_at > 0
        assert summary.message_count == 1
        assert summary.model_name == "gpt-4"
        assert summary.preview == "テストメッセージ"


class TestSearchSessions:
    """search_sessions() のテスト。"""

    def test_search_finds_matching_session(self, service):
        """キーワードを含むセッションが検索結果に含まれる。"""
        s1 = service.create_session()
        service.update_session(
            s1.session_id,
            [
                Message(
                    role="user", content="Pythonについて教えて", timestamp=time.time()
                )
            ],
        )

        s2 = service.create_session()
        service.update_session(
            s2.session_id,
            [Message(role="user", content="JavaScriptの基礎", timestamp=time.time())],
        )

        results = service.search_sessions("Python")
        assert len(results) == 1
        assert results[0].session_id == s1.session_id

    def test_search_case_insensitive(self, service):
        """検索は大文字小文字を区別しない。"""
        s1 = service.create_session()
        service.update_session(
            s1.session_id,
            [Message(role="user", content="Hello World", timestamp=time.time())],
        )

        results = service.search_sessions("hello")
        assert len(results) == 1

    def test_search_empty_keyword_returns_all(self, service):
        """空キーワードで全セッションを返す。"""
        service.create_session()
        service.create_session()

        results = service.search_sessions("")
        assert len(results) == 2

    def test_search_no_match(self, service):
        """マッチしない場合は空リスト。"""
        s1 = service.create_session()
        service.update_session(
            s1.session_id,
            [Message(role="user", content="こんにちは", timestamp=time.time())],
        )

        results = service.search_sessions("存在しないキーワード")
        assert len(results) == 0

    def test_search_results_sorted_by_updated_at(self, service):
        """検索結果も更新日時降順でソートされる。"""
        s1 = service.create_session()
        service.update_session(
            s1.session_id,
            [Message(role="user", content="共通キーワード", timestamp=time.time())],
        )

        time.sleep(0.01)

        s2 = service.create_session()
        service.update_session(
            s2.session_id,
            [Message(role="user", content="共通キーワード", timestamp=time.time())],
        )

        results = service.search_sessions("共通キーワード")
        assert len(results) == 2
        assert results[0].session_id == s2.session_id
        assert results[1].session_id == s1.session_id

    def test_search_in_assistant_messages(self, service):
        """アシスタントのメッセージ内容も検索対象。"""
        s1 = service.create_session()
        service.update_session(
            s1.session_id,
            [
                Message(role="user", content="質問", timestamp=time.time()),
                Message(
                    role="assistant",
                    content="回答にPythonを使います",
                    timestamp=time.time(),
                ),
            ],
        )

        results = service.search_sessions("Python")
        assert len(results) == 1
