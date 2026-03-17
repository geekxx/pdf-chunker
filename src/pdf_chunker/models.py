from pydantic import BaseModel, Field
from pathlib import Path


class TextBlock(BaseModel):
    """A block of text extracted from a PDF page."""
    text: str
    bbox: tuple[float, float, float, float]  # (x0, y0, x1, y1)
    block_type: str = "paragraph"  # paragraph, heading, list_item
    page_number: int
    font_size: float = 0.0
    font_flags: int = 0  # bitmask: bit 1=italic, bit 4=bold


class Table(BaseModel):
    """A table extracted from a PDF page."""
    rows: list[list[str]]
    page_number: int
    bbox: tuple[float, float, float, float]
    has_header_row: bool = True


class Page(BaseModel):
    """A single page from a PDF document."""
    page_number: int
    text_blocks: list[TextBlock] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)


class Document(BaseModel):
    """A parsed PDF document."""
    path: Path
    page_count: int
    metadata: dict = Field(default_factory=dict)
    pages: list[Page] = Field(default_factory=list)


class MarkdownDocument(BaseModel):
    """Markdown representation of a document with source traceability."""
    content: str
    source_path: Path
    page_map: list[tuple[int, int, int]] = Field(default_factory=list)
    # Each tuple: (start_offset, end_offset, page_number)


class ChunkMetadata(BaseModel):
    """Metadata for a single chunk, enabling traceability."""
    chunk_id: str
    source_file: str
    page_numbers: list[int] = Field(default_factory=list)
    chunk_index: int
    total_chunks: int
    token_count: int
    heading_hierarchy: list[str] = Field(default_factory=list)


class Chunk(BaseModel):
    """A single chunk of content with metadata."""
    content: str
    metadata: ChunkMetadata
    token_count: int
    heading_hierarchy: list[str] = Field(default_factory=list)


class ChunkedDocument(BaseModel):
    """The final output: a document split into chunks."""
    source: str
    total_chunks: int
    chunks: list[Chunk] = Field(default_factory=list)
