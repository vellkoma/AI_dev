"""ドキュメントローダーのユニットテスト。

DocumentLoaderクラスのテキスト・Markdown・PDF読み込み、
形式判定、UnsupportedFormatErrorの送出を検証する。
"""

import io

import pytest

from backend.app.rag.document_loader import DocumentLoader, UnsupportedFormatError


def _create_simple_pdf(text: str = "Hello PDF") -> bytes:
    """テスト用の簡単なPDFバイナリを生成する。

    最小限のPDFをバイト列で直接構築する。
    """

    # 最小限のPDFをバイト列で直接構築する
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length "
        + str(44 + len(text.encode("latin-1", errors="replace"))).encode()
        + b" >>\nstream\nBT /F1 12 Tf 100 700 Td ("
        + text.encode("latin-1", errors="replace")
        + b") Tj ET\nendstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000266 00000 n \n"
        b"0000000400 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\n"
        b"startxref\n480\n%%EOF"
    )
    return pdf_content


class TestDocumentLoader:
    """DocumentLoaderクラスのテスト。"""

    def setup_method(self):
        """各テストメソッドの前にローダーを初期化する。"""
        self.loader = DocumentLoader()

    # --- プレーンテキストの読み込みテスト ---

    def test_load_text_by_content_type(self):
        """content_type=text/plainでテキストを読み込める。"""
        content = "これはテストです。".encode("utf-8")
        result = self.loader.load(content, "test.txt", "text/plain")
        assert result == "これはテストです。"

    def test_load_text_by_extension(self):
        """拡張子.txtでテキストを読み込める（content_typeが不明な場合）。"""
        content = "拡張子判定テスト".encode("utf-8")
        result = self.loader.load(content, "test.txt", "application/octet-stream")
        assert result == "拡張子判定テスト"

    def test_load_text_empty(self):
        """空のテキストファイルを読み込める。"""
        content = b""
        result = self.loader.load(content, "empty.txt", "text/plain")
        assert result == ""

    def test_load_text_multiline(self):
        """複数行テキストを正しく読み込める。"""
        text = "行1\n行2\n行3"
        content = text.encode("utf-8")
        result = self.loader.load(content, "multi.txt", "text/plain")
        assert result == text

    # --- Markdownの読み込みテスト ---

    def test_load_markdown_by_content_type(self):
        """content_type=text/markdownでMarkdownを読み込める。"""
        content = "# 見出し\n\n本文です。".encode("utf-8")
        result = self.loader.load(content, "doc.md", "text/markdown")
        assert result == "# 見出し\n\n本文です。"

    def test_load_markdown_by_extension(self):
        """拡張子.mdでMarkdownを読み込める。"""
        content = "## セクション\n- リスト1".encode("utf-8")
        result = self.loader.load(content, "doc.md", "application/octet-stream")
        assert result == "## セクション\n- リスト1"

    def test_load_markdown_by_markdown_extension(self):
        """拡張子.markdownでMarkdownを読み込める。"""
        content = "**太字**テスト".encode("utf-8")
        result = self.loader.load(content, "doc.markdown", "application/octet-stream")
        assert result == "**太字**テスト"

    # --- サポート外形式のエラーテスト ---

    def test_unsupported_format_raises_error(self):
        """サポート外の形式でUnsupportedFormatErrorが送出される。"""
        content = b"<html><body>Hello</body></html>"
        with pytest.raises(UnsupportedFormatError) as exc_info:
            self.loader.load(content, "page.html", "text/html")

        error = exc_info.value
        assert error.content_type == "text/html"
        assert "application/pdf" in error.supported_formats
        assert "text/plain" in error.supported_formats
        assert "text/markdown" in error.supported_formats

    def test_unsupported_format_unknown_extension(self):
        """未知の拡張子でUnsupportedFormatErrorが送出される。"""
        content = b"\x00\x01\x02"
        with pytest.raises(UnsupportedFormatError) as exc_info:
            self.loader.load(content, "file.xyz", "application/octet-stream")

        error = exc_info.value
        assert len(error.supported_formats) == 3

    def test_unsupported_format_no_extension(self):
        """拡張子なしファイルでUnsupportedFormatErrorが送出される。"""
        content = b"some data"
        with pytest.raises(UnsupportedFormatError):
            self.loader.load(content, "noextension", "application/octet-stream")

    # --- 形式判定テスト ---

    def test_detect_format_content_type_priority(self):
        """content_typeが拡張子より優先される。"""
        # content_typeがtext/plainだがファイル名がtest.md
        content = "plain text content".encode("utf-8")
        result = self.loader.load(content, "test.md", "text/plain")
        # content_type優先なのでテキストとして読み込まれる
        assert result == "plain text content"

    # --- SUPPORTED_FORMATSの確認 ---

    def test_supported_formats_contains_expected_types(self):
        """SUPPORTED_FORMATSに3形式が含まれている。"""
        assert "application/pdf" in DocumentLoader.SUPPORTED_FORMATS
        assert "text/plain" in DocumentLoader.SUPPORTED_FORMATS
        assert "text/markdown" in DocumentLoader.SUPPORTED_FORMATS
        assert len(DocumentLoader.SUPPORTED_FORMATS) == 3

    # --- PDF読み込みテスト ---

    def test_load_pdf_by_content_type(self):
        """content_type=application/pdfでPDFを読み込める。"""
        pdf_bytes = _create_simple_pdf("Hello PDF")
        result = self.loader.load(pdf_bytes, "test.pdf", "application/pdf")
        assert "Hello PDF" in result

    def test_load_pdf_by_extension(self):
        """拡張子.pdfでPDFを読み込める（content_typeが不明な場合）。"""
        pdf_bytes = _create_simple_pdf("Extension test")
        result = self.loader.load(pdf_bytes, "test.pdf", "application/octet-stream")
        assert "Extension test" in result


class TestUnsupportedFormatError:
    """UnsupportedFormatErrorのテスト。"""

    def test_error_attributes(self):
        """エラーにcontent_typeとsupported_formatsが含まれる。"""
        error = UnsupportedFormatError(
            content_type="image/png",
            supported_formats=["application/pdf", "text/plain", "text/markdown"],
        )
        assert error.content_type == "image/png"
        assert error.supported_formats == [
            "application/pdf",
            "text/plain",
            "text/markdown",
        ]

    def test_error_message(self):
        """エラーメッセージにcontent_typeとサポート形式が含まれる。"""
        error = UnsupportedFormatError(
            content_type="image/png",
            supported_formats=["application/pdf", "text/plain"],
        )
        msg = str(error)
        assert "image/png" in msg
        assert "application/pdf" in msg
        assert "text/plain" in msg
