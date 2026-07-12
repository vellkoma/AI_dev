"""コマンドラインチャットインターフェースモジュール。

ユーザーとのチャット対話を処理するCLIインターフェースを提供する。
メッセージ入力、コマンド処理、パフォーマンス統計表示、
ウェルカムメッセージ表示などの機能を含む。

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 9.1, 9.2, 9.3
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from llm_chat_app.exceptions import ChatAppError

if TYPE_CHECKING:
    from llm_chat_app.core.orchestrator import ChatOrchestrator


class Chat_Interface:
    """コマンドラインチャットインターフェース。

    ChatOrchestratorと連携し、ユーザーとLLMの対話を
    コマンドラインで実現する。コマンド入力、メッセージ送信、
    パフォーマンス統計表示などの機能を提供する。

    Attributes:
        orchestrator: チャット処理のオーケストレーター
    """

    def __init__(self, orchestrator: ChatOrchestrator) -> None:
        """Chat_Interfaceを初期化する。

        Args:
            orchestrator: チャット処理のオーケストレーター
        """
        self.orchestrator: ChatOrchestrator = orchestrator

    def start(self) -> None:
        """チャットインターフェースのメインループを開始する。

        ウェルカムメッセージを表示した後、入力待ち→処理→表示の
        ループを実行する。Ctrl+Cで終了確認を行う。

        Validates: Requirements 6.1, 6.2
        """
        self._print_welcome()

        while True:
            try:
                user_input = input("\nYou: ").strip()

                if not user_input:
                    continue

                self._process_input(user_input)

            except KeyboardInterrupt:
                # Ctrl+C: 安全な終了確認
                print("\n終了しますか？(y/n): ", end="")
                try:
                    answer = input().strip().lower()
                    if answer == "y":
                        print("チャットを終了します。お疲れ様でした。")
                        sys.exit(0)
                except (KeyboardInterrupt, EOFError):
                    # 確認中にもう一度Ctrl+Cが押された場合は即終了
                    print("\nチャットを終了します。お疲れ様でした。")
                    sys.exit(0)

    def _process_input(self, user_input: str) -> None:
        """ユーザー入力を処理する。

        "/" で始まる入力はコマンドとして処理し、
        それ以外は通常のメッセージとしてLLMに送信する。

        Args:
            user_input: ユーザーが入力した文字列

        Validates: Requirements 6.3, 6.4
        """
        try:
            if user_input.startswith("/"):
                self._handle_command(user_input)
            else:
                # 通常メッセージ: オーケストレーターに送信
                # Stream_Handlerが "Assistant: " プレフィックスを表示する
                self.orchestrator.send_message(user_input)
        except ChatAppError as e:
            # アプリケーション固有のエラー: ユーザーフレンドリーな表示
            print(f"\nエラー: {e.user_message}")
            print(f"対処法: {e.guidance}")

    def _handle_command(self, command: str) -> None:
        """コマンドを処理する。

        サポートするコマンド:
        - /clear: 会話履歴をクリア
        - /save [filepath]: 会話履歴をファイルに保存
        - /load <filepath>: ファイルから会話履歴を読み込み
        - /stats: パフォーマンス統計を表示
        - /help: コマンド一覧を表示
        - /exit: アプリケーションを終了

        Args:
            command: "/" で始まるコマンド文字列

        Validates: Requirement 6.3
        """
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "/clear":
            self.orchestrator.clear_history()
            print("会話履歴をクリアしました。")

        elif cmd == "/save":
            # ファイルパスが指定されない場合はデフォルトパスを使用
            if args:
                filepath = args
            else:
                session_id = self.orchestrator.history_manager.conversation.session_id
                filepath = f"conversations/{session_id}.json"
            self.orchestrator.save_history(filepath)
            print(f"会話履歴を保存しました: {filepath}")

        elif cmd == "/load":
            if not args:
                print("使い方: /load <ファイルパス>")
                return
            self.orchestrator.load_history(args)
            print(f"会話履歴を読み込みました: {args}")

        elif cmd == "/stats":
            self._show_stats()

        elif cmd == "/help":
            self._print_help()

        elif cmd == "/exit":
            print("チャットを終了します。お疲れ様でした。")
            sys.exit(0)

        else:
            print("不明なコマンドです。/help でコマンド一覧を表示します。")

    def _print_welcome(self) -> None:
        """ウェルカムメッセージを表示する。

        アプリケーション名、使用中のモデル情報、
        ヘルプコマンドの案内を表示する。

        Validates: Requirement 6.2
        """
        model_info = self.orchestrator.get_model_info()
        model_name = model_info.get("model", "不明")
        provider = model_info.get("provider", "不明")

        print("=" * 60)
        print("  LLM Chat App - ポートフォリオプロジェクト")
        print("=" * 60)
        print(f"モデル: {model_name}")
        print(f"プロバイダー: {provider}")
        print("/help でコマンド一覧を表示します。")

    def _print_help(self) -> None:
        """コマンド一覧を表示する。

        利用可能なすべてのコマンドと説明を
        フォーマットして表示する。

        Validates: Requirement 6.2
        """
        print("\n利用可能なコマンド:")
        print("  /clear          - 会話履歴をクリア")
        print("  /save [file]    - 会話履歴を保存（デフォルト: conversations/セッションID.json）")
        print("  /load <file>    - 会話履歴を読み込み")
        print("  /stats          - パフォーマンス統計を表示")
        print("  /help           - このヘルプを表示")
        print("  /exit           - アプリケーションを終了")

    def _show_stats(self) -> None:
        """パフォーマンス統計を表示する。

        累積リクエスト数、応答時間、トークン数、推定コストを
        フォーマットして表示する。

        Validates: Requirements 9.1, 9.2, 9.3
        """
        stats = self.orchestrator.get_stats()

        print("\n--- パフォーマンス統計 ---")
        print(f"  リクエスト数: {stats['total_requests']}")
        print(f"  合計応答時間: {stats['total_time']:.2f}秒")
        print(f"  平均応答時間: {stats['average_response_time']:.2f}秒")
        print(f"  合計トークン数: {stats['total_tokens']}")
        print(f"  推定コスト: ${stats['estimated_cost']:.6f}")
        print("-------------------------")
