"""ストリーミングレスポンス処理モジュール。

LLMからのレスポンスをリアルタイムでストリーミング表示する機能を提供する。
トークンを受信するたびに即座に出力ストリームに書き込み、
完了時に完全なレスポンステキストを返す。

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
"""

from __future__ import annotations

import sys
from typing import TextIO


class Stream_Handler:
    """ストリーミングレスポンスの処理と表示を担当するクラス。

    LLMからのトークンストリームを受信し、即座に出力ストリームに表示する。
    出力ストリームは依存性注入により差し替え可能で、テスト容易性を確保する。

    Attributes:
        output_stream: 出力先のテキストストリーム（デフォルト: sys.stdout）
        current_response: 現在のストリーミングで蓄積されたレスポンステキスト
        is_streaming: ストリーミング中かどうかを示すフラグ
    """

    def __init__(self, output_stream: TextIO = sys.stdout) -> None:
        """Stream_Handlerを初期化する。

        Args:
            output_stream: 出力ストリーム。テスト時にモック可能。
                          デフォルトはsys.stdout。
        """
        self.output_stream: TextIO = output_stream
        self.current_response: str = ""
        self.is_streaming: bool = False

    def start_streaming(self) -> None:
        """ストリーミング開始を通知し、状態を初期化する。

        ストリーミングフラグをTrueに設定し、レスポンスバッファをクリアする。
        出力ストリームに「Assistant: 」プレフィックスを書き込み、
        ユーザーにレスポンス生成中であることを視覚的に示す。

        Validates: Requirement 3.4
        """
        self.is_streaming = True
        self.current_response = ""
        self.output_stream.write("\nAssistant: ")
        self.output_stream.flush()

    def on_token(self, token: str) -> None:
        """トークン受信時のコールバック。

        受信したトークンをレスポンスバッファに追加し、
        即座に出力ストリームに書き込んでフラッシュする。
        これにより、ユーザーはリアルタイムでレスポンスを確認できる。

        Args:
            token: LLMから受信した1つのトークン文字列。

        Validates: Requirements 3.1, 3.2, 3.3
        """
        self.current_response += token
        self.output_stream.write(token)
        self.output_stream.flush()

    def end_streaming(self) -> str:
        """ストリーミング完了を通知し、完全なレスポンステキストを返す。

        ストリーミングフラグをFalseに設定し、出力ストリームに改行を書き込む。
        蓄積された完全なレスポンステキストを返す。

        Returns:
            ストリーミング中に蓄積された完全なレスポンステキスト。

        Validates: Requirement 3.5
        """
        self.is_streaming = False
        self.output_stream.write("\n")
        self.output_stream.flush()
        return self.current_response
