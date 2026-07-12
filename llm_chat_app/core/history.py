"""会話履歴管理モジュール。

会話履歴の追加・取得・クリア・永続化・トークン制限管理を担当する。
History_ManagerクラスはConversationデータクラスを内部で保持し、
セッション単位で会話履歴を管理する。

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import List, Optional

from llm_chat_app.exceptions import FileFormatError
from llm_chat_app.models import Conversation, Message


class History_Manager:
    """会話履歴の管理と永続化を担当するクラス。

    メッセージの追加・取得・クリア、JSON形式でのファイル保存・読み込み、
    トークン制限超過時の古いメッセージ削減機能を提供する。

    Attributes:
        conversation: 現在の会話セッション
        max_tokens: 履歴の最大トークン数（制限超過時は古い履歴を削減）
    """

    def __init__(self, max_tokens: int = 4000) -> None:
        """History_Managerを初期化する。

        Args:
            max_tokens: 履歴の最大トークン数（制限超過時は古い履歴を削減）
        """
        self.max_tokens: int = max_tokens
        self.conversation: Conversation = Conversation(
            session_id=self._generate_session_id(),
            messages=[],
            created_at=time.time(),
            updated_at=time.time(),
            model_name="",
            total_tokens=0,
        )

    def add_message(self, message: Message) -> None:
        """メッセージを会話履歴に追加する。

        メッセージ追加後、トークン制限を超過している場合は
        古いメッセージを自動的に削減する。

        Args:
            message: 追加するメッセージ
        """
        self.conversation.messages.append(message)
        self.conversation.updated_at = time.time()
        self._trim_history_if_needed()

    def get_messages(self) -> List[Message]:
        """現在の会話履歴のコピーを返す。

        Returns:
            会話メッセージのリスト（コピー）
        """
        return self.conversation.messages.copy()

    def clear_history(self) -> None:
        """会話履歴をクリアする。

        メッセージリストと累積トークン数をリセットする。
        """
        self.conversation.messages.clear()
        self.conversation.total_tokens = 0
        self.conversation.updated_at = time.time()

    def save_to_file(self, filepath: str) -> None:
        """会話履歴をJSON形式でファイルに保存する。

        保存データにはsession_id、メッセージ一覧、タイムスタンプ、
        モデル名、累積トークン数が含まれる。

        Args:
            filepath: 保存先ファイルパス

        Raises:
            OSError: ファイルの書き込みに失敗した場合
        """
        data = self.conversation.to_dict()
        path = Path(filepath)

        # 親ディレクトリが存在しない場合は作成する
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_from_file(self, filepath: str) -> None:
        """JSONファイルから会話履歴を読み込む。

        読み込んだデータで現在のConversationオブジェクトを置き換える。

        Args:
            filepath: 読み込み元ファイルパス

        Raises:
            FileNotFoundError: ファイルが存在しない場合
            FileFormatError: JSONの形式が不正またはデータ構造が不正な場合
        """
        path = Path(filepath)

        if not path.exists():
            raise FileNotFoundError(
                f"履歴ファイルが見つかりません: {filepath}"
            )

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise FileFormatError(
                message=f"履歴ファイルのJSON形式が不正です: {filepath}",
                details=str(e),
            )

        # データ構造の検証
        try:
            self.conversation = Conversation.from_dict(data)
        except (KeyError, TypeError) as e:
            raise FileFormatError(
                message=f"履歴ファイルのデータ構造が不正です: {filepath}",
                details=str(e),
            )

    def _trim_history_if_needed(self) -> None:
        """トークン制限超過時に古いメッセージを削減する。

        簡易的なトークン推定（文字数 / 4）を使用して、
        推定トークン数が制限を超える場合は古いメッセージから削除する。
        ただし、システムメッセージ（role="system"）は保持する。
        """
        estimated_tokens = self._estimate_tokens()

        while estimated_tokens > self.max_tokens and len(self.conversation.messages) > 1:
            # 削除対象のインデックスを探す（システムメッセージ以外で最も古いもの）
            removed = False
            for i, msg in enumerate(self.conversation.messages):
                if msg.role != "system":
                    self.conversation.messages.pop(i)
                    removed = True
                    break

            if not removed:
                # すべてシステムメッセージの場合はループを抜ける
                break

            estimated_tokens = self._estimate_tokens()

        # 累積トークン数を更新
        self.conversation.total_tokens = estimated_tokens

    def _estimate_tokens(self) -> int:
        """会話履歴の推定トークン数を計算する。

        簡易的なヒューリスティック（文字数 / 4）を使用する。

        Returns:
            推定トークン数
        """
        return sum(len(msg.content) // 4 for msg in self.conversation.messages)

    @staticmethod
    def _generate_session_id() -> str:
        """新しいセッションIDを生成する。

        Returns:
            UUID4文字列
        """
        return str(uuid.uuid4())
