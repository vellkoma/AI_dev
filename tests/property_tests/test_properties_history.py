"""History_Managerのプロパティベーステスト。

Property 3: 会話履歴の追加と取得
Property 4: 会話履歴のクリア
Property 5: トークン制限による履歴トリミング
Property 6: 会話履歴の永続化ラウンドトリップ

**Validates: Requirements 4.1, 4.2, 4.4, 4.5, 5.1, 5.2, 5.3**

テストフレームワーク: Hypothesis
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from llm_chat_app.core.history import History_Manager
from llm_chat_app.models import Message

# ===== 戦略（Strategy）定義 =====

# 有効なメッセージロール
valid_roles = st.sampled_from(["user", "assistant", "system"])

# ユーザー/アシスタントのみのロール（トリミングテスト用）
non_system_roles = st.sampled_from(["user", "assistant"])

# メッセージ内容: 空でない文字列（トークン推定に関わるため最低1文字）
valid_content = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S", "Z"),
    ),
    min_size=1,
    max_size=200,
)

# タイムスタンプ: 妥当なUNIX時間範囲
valid_timestamp = st.floats(
    min_value=1000000000.0,  # 2001年頃
    max_value=2000000000.0,  # 2033年頃
    allow_nan=False,
    allow_infinity=False,
)


@st.composite
def message_strategy(draw, role_strategy=valid_roles):
    """Messageオブジェクトを生成する戦略。"""
    role = draw(role_strategy)
    content = draw(valid_content)
    timestamp = draw(valid_timestamp)
    return Message(role=role, content=content, timestamp=timestamp)


@st.composite
def message_list_strategy(draw, min_size=1, max_size=10, role_strategy=valid_roles):
    """Messageオブジェクトのリストを生成する戦略。"""
    messages = draw(
        st.lists(
            message_strategy(role_strategy=role_strategy),
            min_size=min_size,
            max_size=max_size,
        )
    )
    return messages


@st.composite
def system_and_non_system_messages_strategy(draw):
    """システムメッセージと非システムメッセージを混在させた戦略。

    トリミングテスト用: 十分なコンテンツ量を確保する。
    """
    # システムメッセージ（1〜2個、短い内容）
    system_messages = draw(
        st.lists(
            message_strategy(role_strategy=st.just("system")),
            min_size=1,
            max_size=2,
        )
    )

    # 非システムメッセージ（長い内容でトークン制限を超えさせる）
    long_content = st.text(
        alphabet=st.characters(whitelist_categories=("L", "N")),
        min_size=100,
        max_size=500,
    )

    non_system_messages = draw(
        st.lists(
            st.builds(
                Message,
                role=non_system_roles,
                content=long_content,
                timestamp=valid_timestamp,
            ),
            min_size=3,
            max_size=8,
        )
    )

    # システムメッセージを先頭に配置し、非システムメッセージを後に追加
    all_messages = system_messages + non_system_messages
    return all_messages


# ===== プロパティテスト =====


class TestHistoryAddAndGet:
    """会話履歴の追加と取得プロパティテスト。

    **Validates: Requirements 4.1, 4.2**
    """

    @given(messages=message_list_strategy(min_size=1, max_size=10))
    @settings(max_examples=100, deadline=None)
    def test_add_and_get_preserves_order_and_content(
        self, messages: List[Message]
    ) -> None:
        """Property 3: 任意のメッセージリストを追加後、get_messages()で同じ順序・内容で取得できる。

        **Validates: Requirements 4.1, 4.2**

        検証内容:
        1. 追加したメッセージ数と取得したメッセージ数が一致する
        2. 各メッセージのrole、content、timestampが追加順に一致する
        """
        # トークン制限を十分大きく設定してトリミングを回避
        manager = History_Manager(max_tokens=1000000)

        # メッセージを順番に追加
        for msg in messages:
            manager.add_message(msg)

        # 取得して検証
        retrieved = manager.get_messages()

        # メッセージ数が一致する
        assert len(retrieved) == len(messages)

        # 各メッセージの内容と順序が一致する
        for original, got in zip(messages, retrieved):
            assert got.role == original.role
            assert got.content == original.content
            assert got.timestamp == original.timestamp


class TestHistoryClear:
    """会話履歴のクリアプロパティテスト。

    **Validates: Requirements 4.4**
    """

    @given(messages=message_list_strategy(min_size=1, max_size=10))
    @settings(max_examples=100, deadline=None)
    def test_clear_history_returns_empty_list(self, messages: List[Message]) -> None:
        """Property 4: 任意のメッセージを追加後にclear_history()するとget_messages()が空リストを返す。

        **Validates: Requirements 4.4**

        検証内容:
        1. メッセージ追加後、clear_history()を呼ぶ
        2. get_messages()が空リストを返す
        """
        # トークン制限を十分大きく設定してトリミングを回避
        manager = History_Manager(max_tokens=1000000)

        # メッセージを追加
        for msg in messages:
            manager.add_message(msg)

        # クリア前にメッセージが存在することを確認
        assert len(manager.get_messages()) > 0

        # クリア実行
        manager.clear_history()

        # クリア後は空リストが返る
        assert manager.get_messages() == []


class TestHistoryTokenTrimming:
    """トークン制限による履歴トリミングプロパティテスト。

    **Validates: Requirements 4.5**
    """

    @given(data=system_and_non_system_messages_strategy())
    @settings(max_examples=100, deadline=None)
    def test_token_limit_respected_after_trimming(self, data: List[Message]) -> None:
        """Property 5: max_tokensを超過するメッセージ群を追加した場合、推定トークン数がmax_tokens以下に収まる。

        **Validates: Requirements 4.5**

        検証内容:
        1. 小さいmax_tokensを設定する
        2. 大量のメッセージを追加する
        3. トリミング後の推定トークン数がmax_tokens以下である
        4. システムメッセージが常に保持される
        """
        # 小さいトークン制限でManagerを作成
        max_tokens = 50
        manager = History_Manager(max_tokens=max_tokens)

        # システムメッセージだけでmax_tokensを超過する場合はスキップ
        # （システムメッセージは保持される設計のため、トリミング不可能）
        system_tokens = sum(
            len(msg.content) // 4 for msg in data if msg.role == "system"
        )
        assume(system_tokens <= max_tokens)

        # メッセージを追加（トリミングが発動するはず）
        for msg in data:
            manager.add_message(msg)

        # 推定トークン数を計算
        remaining_messages = manager.get_messages()
        estimated_tokens = sum(len(msg.content) // 4 for msg in remaining_messages)

        # 推定トークン数がmax_tokens以下であることを検証
        assert estimated_tokens <= max_tokens

        # システムメッセージが保持されていることを検証
        system_messages_in_input = [m for m in data if m.role == "system"]
        system_messages_in_result = [
            m for m in remaining_messages if m.role == "system"
        ]

        # 入力のシステムメッセージがすべて保持されている
        for sys_msg in system_messages_in_input:
            assert any(
                m.role == sys_msg.role
                and m.content == sys_msg.content
                and m.timestamp == sys_msg.timestamp
                for m in system_messages_in_result
            ), f"システムメッセージが削除された: {sys_msg.content[:50]}"


class TestHistoryPersistenceRoundTrip:
    """会話履歴の永続化ラウンドトリッププロパティテスト。

    **Validates: Requirements 5.1, 5.2, 5.3**
    """

    @given(messages=message_list_strategy(min_size=0, max_size=10))
    @settings(max_examples=100, deadline=None)
    def test_save_and_load_preserves_messages(self, messages: List[Message]) -> None:
        """Property 6: save_to_file()で保存した内容をload_from_file()で読み込むと、
        元のメッセージ内容と順序が完全に一致する。

        **Validates: Requirements 5.1, 5.2, 5.3**

        検証内容:
        1. メッセージを追加して保存する
        2. 別のHistory_Managerインスタンスで読み込む
        3. メッセージの内容と順序が完全に一致する
        """
        # トークン制限を十分大きく設定してトリミングを回避
        manager = History_Manager(max_tokens=1000000)

        # メッセージを追加
        for msg in messages:
            manager.add_message(msg)

        try:
            # 一時ファイルに保存
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".json",
                delete=False,
                encoding="utf-8",
            ) as f:
                temp_path = f.name

            manager.save_to_file(temp_path)

            # 別のインスタンスで読み込み
            loaded_manager = History_Manager(max_tokens=1000000)
            loaded_manager.load_from_file(temp_path)

            # 取得して検証
            original_messages = manager.get_messages()
            loaded_messages = loaded_manager.get_messages()

            # メッセージ数が一致する
            assert len(loaded_messages) == len(original_messages)

            # 各メッセージの内容と順序が一致する
            for original, loaded in zip(original_messages, loaded_messages):
                assert loaded.role == original.role
                assert loaded.content == original.content
                assert loaded.timestamp == original.timestamp

        finally:
            # クリーンアップ
            Path(temp_path).unlink(missing_ok=True)
