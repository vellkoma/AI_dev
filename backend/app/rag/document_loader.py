"""ドキュメントローダーモジュール。

PDF、プレーンテキスト、Markdownの3形式に対応した
マルチフォーマットドキュメント読み込み機能を提供する。
"""

import os
import tempfile
from typing import Dict


class UnsupportedFormatError(Exception):
    """サポート外のドキュメント形式が指定された場合の例外。

    Attributes:
        content_type: 指定されたcontent_type
        supported_formats: サポートされている形式の一覧
    """

    def __init__(self, content_type: str, supported_formats: list):
        self.content_type = content_type
        self.supported_formats = supported_formats
        super().__init__(
            f"非対応のファイル形式です: {content_type}。"
            f"サポート形式: {', '.join(supported_formats)}"
        )


class DocumentLoader:
    """マルチフォーマットドキュメントローダー。

    PDF、プレーンテキスト、Markdownの3形式に対応。
    バイトデータとcontent_typeを受け取り、テキスト文字列を返す。
    """

    SUPPORTED_FORMATS: Dict[str, str] = {
        "application/pdf": "pdf",
        "text/plain": "txt",
        "text/markdown": "md",
    }

    def load(self, content: bytes, filename: str, content_type: str) -> str:
        """ドキュメントをテキストとして読み込む。

        Args:
            content: ファイルのバイナリデータ
            filename: ファイル名（拡張子判定の補助に使用）
            content_type: MIMEタイプ

        Returns:
            抽出されたテキスト文字列

        Raises:
            UnsupportedFormatError: サポート外の形式の場合
        """
        # content_typeで判定、なければ拡張子で判定
        format_type = self._detect_format(content_type, filename)

        if format_type == "pdf":
            return self._load_pdf(content)
        elif format_type == "txt":
            return self._load_text(content)
        elif format_type == "md":
            return self._load_markdown(content)
        else:
            raise UnsupportedFormatError(
                content_type=content_type,
                supported_formats=list(self.SUPPORTED_FORMATS.keys()),
            )

    def _detect_format(self, content_type: str, filename: str) -> str:
        """content_typeとファイル名から形式を判定する。

        Args:
            content_type: MIMEタイプ
            filename: ファイル名

        Returns:
            判定された形式文字列（"pdf", "txt", "md"）

        Raises:
            UnsupportedFormatError: サポート外の形式の場合
        """
        # ファイル拡張子で判定（優先）
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        ext_map = {"pdf": "pdf", "txt": "txt", "md": "md", "markdown": "md"}
        if ext in ext_map:
            return ext_map[ext]

        # content_typeで判定（フォールバック）
        if content_type in self.SUPPORTED_FORMATS:
            return self.SUPPORTED_FORMATS[content_type]

        raise UnsupportedFormatError(
            content_type=content_type,
            supported_formats=list(self.SUPPORTED_FORMATS.keys()),
        )

    def _load_pdf(self, content: bytes) -> str:
        """PDFからテキストを抽出する。

        pdfplumber（pdfminer.six基盤）を使用してPDFを読み込み、
        全ページのテキストを結合して返す。
        日本語CIDフォントに対する抽出精度が高い。

        Args:
            content: PDFファイルのバイナリデータ

        Returns:
            抽出されたテキスト文字列

        Raises:
            ValueError: PDFが暗号化されていて読み取れない場合
        """
        import io

        try:
            import pdfplumber

            with pdfplumber.open(io.BytesIO(content)) as pdf:
                text_parts = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                return "\n".join(text_parts)
        except Exception as e:
            error_str = str(e).lower()
            if "password" in error_str or "decrypt" in error_str:
                raise ValueError(
                    "PDFがパスワードで保護されています。"
                    "保護を解除してから再度アップロードしてください。"
                )
            raise

    def _load_text(self, content: bytes) -> str:
        """プレーンテキストをデコードする。

        Args:
            content: テキストファイルのバイナリデータ

        Returns:
            UTF-8デコードされた文字列
        """
        return content.decode("utf-8")

    def _load_markdown(self, content: bytes) -> str:
        """Markdownファイルをテキストとして読み込む。

        マークダウン記法はそのまま保持し、バイナリデータを
        UTF-8文字列としてデコードして返す。

        Args:
            content: Markdownファイルのバイナリデータ

        Returns:
            UTF-8デコードされた文字列
        """
        return content.decode("utf-8")
