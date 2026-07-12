"""Stream_Handlerの単体テスト。

ストリーミングレスポンスの開始・トークン受信・終了処理、
出力ストリームへの即時書き込み、状態管理の動作を検証する。

Validates: Requirements 3.3, 4.4, 4.5, 5.1, 5.5
"""

from __future__ import annotations

import io

from llm_chat_app.core.stream import Stream_Handler


class TestStreamHandlerInit:
    """Stream_Handlerの初期化テスト"""

    def test_デフォルト出力ストリームで初期化できる(self) -> None:
        """デフォルトのoutput_streamで初期化できることを検証"""
        handler = Stream_Handler()
        assert handler.output_stream is not None

    def test_カスタム出力ストリームを注入できる(self) -> None:
        """カスタムのoutput_streamを依存性注入できることを検証"""
        output = io.StringIO()
        handler = Stream_Handler(output_stream=output)
        assert handler.output_stream is output

    def test_初期状態でis_streamingがFalseである(self) -> None:
        """初期化直後はis_streamingがFalseであることを検証"""
        output = io.StringIO()
        handler = Stream_Handler(output_stream=output)
        assert handler.is_streaming is False

    def test_初期状態でcurrent_responseが空文字列である(self) -> None:
        """初期化直後はcurrent_responseが空文字列であることを検証"""
        output = io.StringIO()
        handler = Stream_Handler(output_stream=output)
        assert handler.current_response == ""


class TestStartStreaming:
    """start_streaming()のテスト"""

    def test_プレフィックスが出力ストリームに書き込まれる(self) -> None:
        """start_streaming()で「\\nAssistant: 」が出力されることを検証"""
        output = io.StringIO()
        handler = Stream_Handler(output_stream=output)
        handler.start_streaming()
        assert output.getvalue() == "\nAssistant: "

    def test_is_streamingがTrueになる(self) -> None:
        """start_streaming()後にis_streamingがTrueになることを検証"""
        output = io.StringIO()
        handler = Stream_Handler(output_stream=output)
        handler.start_streaming()
        assert handler.is_streaming is True

    def test_current_responseが空文字列にリセットされる(self) -> None:
        """start_streaming()でcurrent_responseが空文字列にリセットされることを検証"""
        output = io.StringIO()
        handler = Stream_Handler(output_stream=output)
        # 事前にcurrent_responseに値を設定
        handler.current_response = "前回のレスポンス"
        handler.start_streaming()
        assert handler.current_response == ""


class TestOnToken:
    """on_token()のテスト"""

    def test_トークンが出力ストリームに即座に書き込まれる(self) -> None:
        """on_token()でトークンが出力ストリームに即座に書き込まれることを検証"""
        output = io.StringIO()
        handler = Stream_Handler(output_stream=output)
        handler.start_streaming()
        handler.on_token("こんにちは")
        assert "こんにちは" in output.getvalue()

    def test_トークンがcurrent_responseに蓄積される(self) -> None:
        """on_token()でトークンがcurrent_responseに蓄積されることを検証"""
        output = io.StringIO()
        handler = Stream_Handler(output_stream=output)
        handler.start_streaming()
        handler.on_token("Hello")
        handler.on_token(" World")
        assert handler.current_response == "Hello World"

    def test_複数トークンが順序通りに出力される(self) -> None:
        """複数のon_token()呼び出しが順序通りに出力されることを検証"""
        output = io.StringIO()
        handler = Stream_Handler(output_stream=output)
        handler.start_streaming()
        handler.on_token("A")
        handler.on_token("B")
        handler.on_token("C")
        # プレフィックス「\nAssistant: 」の後にABCが続く
        assert output.getvalue() == "\nAssistant: ABC"

    def test_空トークンの処理(self) -> None:
        """空文字列トークンが正しく処理されることを検証"""
        output = io.StringIO()
        handler = Stream_Handler(output_stream=output)
        handler.start_streaming()
        handler.on_token("")
        handler.on_token("テスト")
        handler.on_token("")
        # current_responseは空トークンを含む連結結果
        assert handler.current_response == "テスト"
        # 出力にはプレフィックスとトークン
        assert output.getvalue() == "\nAssistant: テスト"


class TestEndStreaming:
    """end_streaming()のテスト"""

    def test_完全なレスポンステキストを返す(self) -> None:
        """end_streaming()が蓄積された完全なレスポンステキストを返すことを検証"""
        output = io.StringIO()
        handler = Stream_Handler(output_stream=output)
        handler.start_streaming()
        handler.on_token("応答")
        handler.on_token("テキスト")
        result = handler.end_streaming()
        assert result == "応答テキスト"

    def test_出力ストリームに改行が追加される(self) -> None:
        """end_streaming()で出力ストリームに改行が追加されることを検証"""
        output = io.StringIO()
        handler = Stream_Handler(output_stream=output)
        handler.start_streaming()
        handler.on_token("テスト")
        handler.end_streaming()
        # 末尾に改行が追加される
        assert output.getvalue().endswith("\n")

    def test_is_streamingがFalseになる(self) -> None:
        """end_streaming()後にis_streamingがFalseになることを検証"""
        output = io.StringIO()
        handler = Stream_Handler(output_stream=output)
        handler.start_streaming()
        handler.on_token("データ")
        handler.end_streaming()
        assert handler.is_streaming is False

    def test_トークンなしの場合は空文字列を返す(self) -> None:
        """トークンが送信されなかった場合にend_streaming()が空文字列を返すことを検証"""
        output = io.StringIO()
        handler = Stream_Handler(output_stream=output)
        handler.start_streaming()
        result = handler.end_streaming()
        assert result == ""


class TestMultipleStreamingSessions:
    """複数ストリーミングセッションのテスト"""

    def test_連続した2つのセッションが独立して動作する(self) -> None:
        """2つの連続セッションが互いに干渉しないことを検証"""
        output = io.StringIO()
        handler = Stream_Handler(output_stream=output)

        # 最初のセッション
        handler.start_streaming()
        handler.on_token("最初の")
        handler.on_token("応答")
        result1 = handler.end_streaming()

        # 2番目のセッション
        handler.start_streaming()
        handler.on_token("次の")
        handler.on_token("応答")
        result2 = handler.end_streaming()

        # 各セッションの結果が独立している
        assert result1 == "最初の応答"
        assert result2 == "次の応答"

    def test_セッション間でis_streamingが正しく遷移する(self) -> None:
        """複数セッション間でis_streamingフラグが正しく遷移することを検証"""
        output = io.StringIO()
        handler = Stream_Handler(output_stream=output)

        # 初期状態
        assert handler.is_streaming is False

        # セッション1開始
        handler.start_streaming()
        assert handler.is_streaming is True

        # セッション1終了
        handler.end_streaming()
        assert handler.is_streaming is False

        # セッション2開始
        handler.start_streaming()
        assert handler.is_streaming is True

        # セッション2終了
        handler.end_streaming()
        assert handler.is_streaming is False

    def test_セッション間で出力ストリームに正しく書き込まれる(self) -> None:
        """複数セッションの出力が出力ストリームに連続して書き込まれることを検証"""
        output = io.StringIO()
        handler = Stream_Handler(output_stream=output)

        handler.start_streaming()
        handler.on_token("A")
        handler.end_streaming()

        handler.start_streaming()
        handler.on_token("B")
        handler.end_streaming()

        # 出力ストリームに両方のセッションの内容が含まれる
        full_output = output.getvalue()
        assert "\nAssistant: A\n" in full_output
        assert "\nAssistant: B\n" in full_output
