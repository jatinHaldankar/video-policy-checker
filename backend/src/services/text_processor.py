import re
import logging
from typing import List, Dict
from backend.src.config import settings

logger = logging.getLogger(__name__)


class TextProcessorService:
    """
    Utility service for processing and chunking text.
    """

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    def clean_text(self, text: str) -> str:
        """
        Standardizes whitespace and line breaks.
        """
        text = re.sub(r"\r\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def chunk_text(self, text: str, source_name: str) -> List[Dict]:
        """
        Splits text into overlapping chunks using LangChain's RecursiveCharacterTextSplitter.
        """
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        cleaned_text = self.clean_text(text)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

        string_chunks = splitter.split_text(cleaned_text)

        chunks = []
        for i, chunk_str in enumerate(string_chunks):
            chunks.append(
                {
                    "chunk_index": i,
                    "text": chunk_str.strip(),
                    "source_name": source_name,
                }
            )

        return chunks
