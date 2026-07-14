"""RAGコンポーネント（DocumentLoader、TextChunker）の統合テスト。

DocumentLoaderの各形式ロードと非サポート形式エラー、
TextChunkerのサイズ制約とチャンク生成を検証する。
"""

import pytest

from backend.app.rag.document_loader import DocumentLoader, UnsupportedFormatError
from backend.app.rag.chunker import TextChunker, Chunk


class TestDocumentLoaderFormats:
    """DocumentLoaderの各形式ロードテスト。"""

    def setup_method(self):
        """各テストメソッドの前にローダーを初期化する。"""
        self.loader = DocumentLoader()

    def test_load_plain_text(self):
        """プレーンテキストを正しく読み込める。"""
        content = "Hello, World! これはテストです。".encode("utf-8")
        result = self.loader.load(content, "test.txt", "text/plain")
        assert result == "Hello, World! これはテストです。"

    def test_load_markdown(self):
        """Markdownファイルを正しく読み込める。"""
        content = "# タイトル\n\n段落テキスト\n\n- リスト項目".encode("utf-8")
        result = self.loader.load(content, "doc.md", "text/markdown")
        assert "# タイトル" in result
        assert "- リスト項目" in result

    def test_load_pdf(self):
        """PDFファイルからテキストを抽出できる。"""
        # 最小限のPDFを構築
        pdf_content = (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
            b"4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 100 700 Td (Test PDF) Tj ET\nendstream\nendobj\n"
            b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
            b"xref\n0 6\n"
            b"0000000000 65535 f \n"
            b"0000000009 00000 n \n"
            b"0000000058 00000 n \n"
            b"0000000115 00000 n \n"
            b"0000000266 00000 n \n"
            b"0000000360 00000 n \n"
            b"trailer\n<< /Size 6 /Root 1 0 R >>\n"
            b"startxref\n440\n%%EOF"
        )
        result = self.loader.load(pdf_content, "test.pdf", "application/pdf")
        assert "Test PDF" in result

    def test_load_text_by_extension_fallback(self):
        """拡張子による形式判定のフォールバックが動作する。"""
        content = "拡張子で判定".encode("utf-8")
        result = self.loader.load(content, "file.txt", "application/octet-stream")
        assert result == "拡張子で判定"

    def test_load_markdown_by_extension_fallback(self):
        """拡張子.mdでMarkdown形式と判定できる。"""
        content = "## Markdown content".encode("utf-8")
        result = self.loader.load(content, "readme.md", "application/octet-stream")
        assert result == "## Markdown content"


class TestDocumentLoaderUnsupportedFormat:
    """DocumentLoaderの非サポート形式エラーテスト。"""

    def setup_method(self):
        self.loader = DocumentLoader()

    def test_unsupported_content_type_raises_error(self):
        """サポート外のcontent_typeでUnsupportedFormatErrorが発生する。"""
        with pytest.raises(UnsupportedFormatError) as exc_info:
            self.loader.load(b"data", "image.png", "image/png")

        error = exc_info.value
        assert error.content_type == "image/png"
        assert "application/pdf" in error.supported_formats

    def test_unsupported_extension_raises_error(self):
        """サポート外の拡張子でUnsupportedFormatErrorが発生する。"""
        with pytest.raises(UnsupportedFormatError):
            self.loader.load(b"data", "file.docx", "application/octet-stream")

    def test_no_extension_unknown_type_raises_error(self):
        """拡張子なし・不明なcontent_typeでエラーが発生する。"""
        with pytest.raises(UnsupportedFormatError):
            self.loader.load(b"data", "noext", "application/octet-stream")

    def test_error_includes_supported_formats(self):
        """エラーにサポート形式のリストが含まれる。"""
        with pytest.raises(UnsupportedFormatError) as exc_info:
            self.loader.load(b"data", "file.exe", "application/x-executable")

        error = exc_info.value
        assert len(error.supported_formats) == 3
        assert "text/plain" in error.supported_formats
        assert "text/markdown" in error.supported_formats
        assert "application/pdf" in error.supported_formats


class TestTextChunkerSizeConstraints:
    """TextChunkerのサイズ制約テスト。"""

    def test_chunks_do_not_exceed_max_size(self):
        """生成されるチャンクがchunk_size以下であることを確認する。"""
        chunk_size = 100
        chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=10)
        # chunk_sizeより十分大きいテキストを生成
        text = "あ" * 500
        chunks = chunker.split(text, "doc-1")

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.content) <= chunk_size

    def test_short_text_produces_single_chunk(self):
        """短いテキストは1つのチャンクになる。"""
        chunker = TextChunker(chunk_size=500, chunk_overlap=50)
        text = "短いテキスト"
        chunks = chunker.split(text, "doc-2")

        assert len(chunks) == 1
        assert chunks[0].content == text

    def test_empty_text_produces_no_chunks(self):
        """空テキストはチャンクを生成しない。"""
        chunker = TextChunker(chunk_size=500, chunk_overlap=50)
        chunks = chunker.split("", "doc-3")
        assert chunks == []

    def test_whitespace_only_text_produces_no_chunks(self):
        """空白のみテキストはチャンクを生成しない。"""
        chunker = TextChunker(chunk_size=500, chunk_overlap=50)
        chunks = chunker.split("   \n\n  ", "doc-4")
        assert chunks == []

    def test_chunk_metadata(self):
        """チャンクにdocument_idとchunk_indexが正しく付与される。"""
        chunker = TextChunker(chunk_size=50, chunk_overlap=5)
        text = "これはテスト文章です。" * 20
        chunks = chunker.split(text, "doc-meta")

        assert len(chunks) > 1
        for i, chunk in enumerate(chunks):
            assert chunk.document_id == "doc-meta"
            assert chunk.chunk_index == i

    def test_custom_chunk_size(self):
        """カスタムchunk_sizeが適用される。"""
        chunker = TextChunker(chunk_size=30, chunk_overlap=5)
        text = "a" * 100
        chunks = chunker.split(text, "doc-custom")

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.content) <= 30

    def test_chunk_is_dataclass_instance(self):
        """生成結果がChunkインスタンスである。"""
        chunker = TextChunker(chunk_size=500, chunk_overlap=50)
        chunks = chunker.split("テスト", "doc-type")

        assert len(chunks) == 1
        assert isinstance(chunks[0], Chunk)
        assert chunks[0].content == "テスト"
        assert chunks[0].document_id == "doc-type"
        assert chunks[0].chunk_index == 0
