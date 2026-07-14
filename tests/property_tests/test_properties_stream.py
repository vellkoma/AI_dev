"""Stream_Handlerのプロパティベーステスト。

Property 1: トークンのストリーミング表示
任意のトークンリストをon_token()で送信した場合、出力ストリームに書き込まれた
内容がすべてのトークンを連結した文字列と一致することを検証する。

Property 2: ストリーミング完了通知
start_streaming()の後、任意のトークンをon_token()で送信し、
end_streaming()で返されるテキストがすべてのトークンを連結した文字列と一致することを検証する。

**Validates: Requirements 3.1, 3.2, 3.5**

テストフレームワーク: Hypothesis
"""

from __future__ import annotations

import io

from hypothesis import given, settings
from hypothesis import strategies as st

from llm_chat_app.core.stream import Stream_Handler

# ===== 戦略（Strategy）定義 =====

# トークン文字列: 任意のUnicode文字列（空文字列を含む）
# LLMのトークンは通常短いテキスト片なので、適度な長さに制限
valid_token = st.text(min_size=0, max_size=50)

# トークンリスト: 0〜50個のトークンからなるリスト
valid_token_list = st.lists(valid_token, min_size=0, max_size=50)


# ===== プロパティテスト =====


class TestStreamingTokenDisplay:
    """トークンのストリーミング表示プロパティテスト。

    **Validates: Requirements 3.1, 3.2**
    """

    @given(tokens=valid_token_list)
    @settings(max_examples=100, deadline=None)
    def test_tokens_written_to_stream_match_concatenation(
        self, tokens: list[str]
    ) -> None:
        """Property 1: 任意のトークンリストをon_token()で送信した場合、
        出力ストリームに書き込まれた内容がすべてのトークンを連結した文字列と一致する。

        **Validates: Requirements 3.1, 3.2**

        検証手順:
        1. StringIOを出力ストリームとしてStream_Handlerを作成
        2. start_streaming()を呼び出し
        3. 各トークンに対してon_token()を呼び出し
        4. 出力ストリームのトークン部分が全トークンの連結と一致することを確認
        """
        # テスト用の出力ストリームを準備
        output = io.StringIO()
        handler = Stream_Handler(output_stream=output)

        # ストリーミング開始
        handler.start_streaming()

        # 各トークンを送信
        for token in tokens:
            handler.on_token(token)

        # 出力ストリームの内容を取得
        stream_content = output.getvalue()

        # start_streaming()が書き込む「\nAssistant: 」プレフィックスを除いた部分を検証
        prefix = "\nAssistant: "
        assert stream_content.startswith(prefix)

        # プレフィックス以降の内容が全トークンの連結と一致する
        token_content = stream_content[len(prefix) :]
        expected = "".join(tokens)
        assert token_content == expected


class TestStreamingCompletion:
    """ストリーミング完了通知プロパティテスト。

    **Validates: Requirements 3.5**
    """

    @given(tokens=valid_token_list)
    @settings(max_examples=100, deadline=None)
    def test_end_streaming_returns_concatenated_tokens(self, tokens: list[str]) -> None:
        """Property 2: start_streaming()の後、任意のトークンをon_token()で送信し、
        end_streaming()で返されるテキストがすべてのトークンを連結した文字列と一致する。

        **Validates: Requirements 3.5**

        検証手順:
        1. StringIOを出力ストリームとしてStream_Handlerを作成
        2. start_streaming()を呼び出し
        3. 各トークンに対してon_token()を呼び出し
        4. end_streaming()の戻り値が全トークンの連結と一致することを確認
        5. ストリーミング状態がFalseになることを確認
        """
        # テスト用の出力ストリームを準備
        output = io.StringIO()
        handler = Stream_Handler(output_stream=output)

        # ストリーミング開始
        handler.start_streaming()

        # 開始時の状態確認
        assert handler.is_streaming is True
        assert handler.current_response == ""

        # 各トークンを送信
        for token in tokens:
            handler.on_token(token)

        # ストリーミング終了
        result = handler.end_streaming()

        # end_streaming()の戻り値が全トークンの連結と一致する
        expected = "".join(tokens)
        assert result == expected

        # ストリーミング状態がFalseになっている
        assert handler.is_streaming is False

        # 出力ストリームの末尾に改行が書き込まれている
        stream_content = output.getvalue()
        assert stream_content.endswith("\n")
