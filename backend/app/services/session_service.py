"""会話セッション管理サービス。

JSON形式でファイルシステムにセッションを永続化し、
CRUD操作とキーワード検索を提供する。
"""

import json
import time
import uuid
from pathlib import Path
from typing import List, Optional, Union

from backend.app.schemas.history import SessionSummary
from llm_chat_app.models import Conversation, Message


class SessionService:
    """会話セッションの永続化と検索を管理するサービス。

    各セッションは個別のJSONファイルとして保存される。
    ファイル名は `{session_id}.json` 形式。
    """

    def __init__(self, storage_dir: Union[str, Path]):
        """SessionServiceを初期化する。

        Args:
            storage_dir: セッションファイルを保存するディレクトリパス
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        """セッションIDからファイルパスを生成する。"""
        return self.storage_dir / f"{session_id}.json"

    def _save_session(self, conversation: Conversation) -> None:
        """セッションをJSONファイルに保存する。"""
        path = self._session_path(conversation.session_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(conversation.to_dict(), f, ensure_ascii=False, indent=2)

    def _load_session(self, session_id: str) -> Conversation:
        """JSONファイルからセッションを読み込む。

        Args:
            session_id: セッション識別子

        Returns:
            復元されたConversationインスタンス

        Raises:
            FileNotFoundError: セッションファイルが存在しない場合
        """
        path = self._session_path(session_id)
        if not path.exists():
            raise FileNotFoundError(f"セッションが見つかりません: {session_id}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Conversation.from_dict(data)

    def create_session(self, model_name: str = "") -> Conversation:
        """新しい会話セッションを作成する。

        Args:
            model_name: 使用するモデル名

        Returns:
            作成されたConversationインスタンス
        """
        now = time.time()
        conversation = Conversation(
            session_id=str(uuid.uuid4()),
            messages=[],
            created_at=now,
            updated_at=now,
            model_name=model_name,
            total_tokens=0,
        )
        self._save_session(conversation)
        return conversation

    def get_session(self, session_id: str) -> Conversation:
        """セッションIDで会話を取得する。

        Args:
            session_id: セッション識別子

        Returns:
            Conversationインスタンス

        Raises:
            FileNotFoundError: セッションが存在しない場合
        """
        return self._load_session(session_id)

    def list_sessions(self) -> List[SessionSummary]:
        """全セッションの概要リストを更新日時降順で返す。

        Returns:
            SessionSummaryのリスト（updated_at降順）
        """
        summaries: List[SessionSummary] = []
        for path in self.storage_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                conversation = Conversation.from_dict(data)
                summary = self._to_summary(conversation)
                summaries.append(summary)
            except (json.JSONDecodeError, KeyError, TypeError):
                # 破損したファイルはスキップする
                continue

        # 更新日時降順でソート
        summaries.sort(key=lambda s: s.updated_at, reverse=True)
        return summaries

    def update_session(
        self,
        session_id: str,
        messages: List[Message],
        total_tokens: Optional[int] = None,
        model_name: Optional[str] = None,
    ) -> Conversation:
        """セッションのメッセージを更新する。

        Args:
            session_id: セッション識別子
            messages: 更新後のメッセージリスト
            total_tokens: 累積トークン数（指定時のみ更新）
            model_name: モデル名（指定時のみ更新）

        Returns:
            更新されたConversationインスタンス

        Raises:
            FileNotFoundError: セッションが存在しない場合
        """
        conversation = self._load_session(session_id)
        conversation.messages = messages
        conversation.updated_at = time.time()

        if total_tokens is not None:
            conversation.total_tokens = total_tokens
        if model_name is not None:
            conversation.model_name = model_name

        self._save_session(conversation)
        return conversation

    def delete_session(self, session_id: str) -> None:
        """セッションを削除する。

        Args:
            session_id: セッション識別子

        Raises:
            FileNotFoundError: セッションが存在しない場合
        """
        path = self._session_path(session_id)
        if not path.exists():
            raise FileNotFoundError(f"セッションが見つかりません: {session_id}")
        path.unlink()

    def search_sessions(self, keyword: str) -> List[SessionSummary]:
        """キーワードでメッセージ内容を全文検索する。

        すべてのセッションのメッセージ内容を走査し、
        キーワードを含むセッションを返す。
        結果は更新日時降順でソートされる。

        Args:
            keyword: 検索キーワード

        Returns:
            マッチしたセッションのSessionSummaryリスト（updated_at降順）
        """
        if not keyword:
            return self.list_sessions()

        keyword_lower = keyword.lower()
        results: List[SessionSummary] = []

        for path in self.storage_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                conversation = Conversation.from_dict(data)

                # メッセージ内容にキーワードが含まれるかチェック
                found = any(
                    keyword_lower in msg.content.lower()
                    for msg in conversation.messages
                )
                if found:
                    results.append(self._to_summary(conversation))
            except (json.JSONDecodeError, KeyError, TypeError):
                continue

        # 更新日時降順でソート
        results.sort(key=lambda s: s.updated_at, reverse=True)
        return results

    def _to_summary(self, conversation: Conversation) -> SessionSummary:
        """ConversationからSessionSummaryを生成する。

        Args:
            conversation: 変換元のConversationインスタンス

        Returns:
            SessionSummaryインスタンス
        """
        # プレビューは最初のユーザーメッセージの先頭50文字
        preview = ""
        for msg in conversation.messages:
            if msg.role == "user":
                preview = msg.content[:50]
                break

        return SessionSummary(
            session_id=conversation.session_id,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=len(conversation.messages),
            model_name=conversation.model_name,
            preview=preview,
        )
