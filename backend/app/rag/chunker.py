"""テキスト分割モジュール。

テキストを適切なサイズのチャンクに分割する。
LangChainのRecursiveCharacterTextSplitterを使用し、
各チャンクにドキュメントIDとチャンクインデックスのメタデータを付与する。
"""

from dataclasses import dataclass
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass
class Chunk:
    """テキストチャンクを表すデータクラス。

    Attributes:
        content: チャンクのテキスト内容
        document_id: 所属ドキュメントのID
        chunk_index: ドキュメント内でのチャンクインデックス（0始まり）
    """

    content: str
    document_id: str
    chunk_index: int


class TextChunker:
    """テキストを適切なサイズのチャンクに分割するクラス。

    LangChainのRecursiveCharacterTextSplitterを使用して、
    セマンティックな区切りを考慮したテキスト分割を行う。
    各チャンクはchunk_size以下のサイズを保証する。

    Attributes:
        chunk_size: チャンクの最大文字数
        chunk_overlap: チャンク間の重複文字数
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """TextChunkerを初期化する。

        Args:
            chunk_size: チャンクの最大文字数（デフォルト: 500）
            chunk_overlap: チャンク間の重複文字数（デフォルト: 50）
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", ".", " ", ""],
        )

    def split(self, text: str, document_id: str) -> List[Chunk]:
        """テキストをチャンクに分割する。

        Args:
            text: 分割対象のテキスト
            document_id: ドキュメントID（各チャンクに付与される）

        Returns:
            チャンクのリスト。元テキストが空の場合は空リスト。
        """
        if not text or not text.strip():
            return []

        text_chunks = self._splitter.split_text(text)

        return [
            Chunk(
                content=chunk_text,
                document_id=document_id,
                chunk_index=i,
            )
            for i, chunk_text in enumerate(text_chunks)
        ]
