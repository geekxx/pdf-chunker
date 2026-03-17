from abc import ABC, abstractmethod

from pdf_chunker.models import MarkdownDocument, Chunk
from pdf_chunker.config import ChunkingConfig


class Chunker(ABC):
    @abstractmethod
    def chunk(self, document: MarkdownDocument, config: ChunkingConfig) -> list[Chunk]:
        ...
