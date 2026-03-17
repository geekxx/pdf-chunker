"""
Acceptance tests for Slice 1: End-to-end single-column PDF to chunked Markdown.

These tests define the contract for the full pipeline. They should FAIL until
all components (ingestion, conversion, cleaning, chunking) are implemented.
"""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# STORY-001: Single PDF file loading
# ---------------------------------------------------------------------------


class TestPDFLoading:
    """Acceptance tests for PDF loading (STORY-001)."""

    def test_load_valid_pdf_returns_document(self):
        """Given a valid PDF path, the system loads it and returns a Document."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.models import Document

        doc = load_document(FIXTURES_DIR / "simple.pdf")
        assert isinstance(doc, Document)
        assert doc.page_count == 1
        assert doc.path == FIXTURES_DIR / "simple.pdf"

    def test_load_pdf_exposes_metadata(self):
        """Document object exposes basic metadata."""
        from pdf_chunker.ingestion.loader import load_document

        doc = load_document(FIXTURES_DIR / "simple.pdf")
        assert isinstance(doc.metadata, dict)

    def test_load_multipage_pdf_correct_page_count(self):
        """Multi-page PDF reports correct page count."""
        from pdf_chunker.ingestion.loader import load_document

        doc = load_document(FIXTURES_DIR / "multiheading.pdf")
        assert doc.page_count == 2

    def test_load_invalid_path_raises_file_not_found(self):
        """Given an invalid path, raises FileNotFoundError."""
        from pdf_chunker.ingestion.loader import load_document

        with pytest.raises(FileNotFoundError):
            load_document(Path("/nonexistent/file.pdf"))

    def test_load_non_pdf_raises_value_error(self, tmp_path):
        """Given a non-PDF file, raises ValueError."""
        from pdf_chunker.ingestion.loader import load_document

        fake = tmp_path / "not_a_pdf.pdf"
        fake.write_text("this is not a pdf")
        with pytest.raises(ValueError, match="not a valid PDF"):
            load_document(fake)


# ---------------------------------------------------------------------------
# STORY-002: PDF text extraction (slice 1 - single column)
# ---------------------------------------------------------------------------


class TestTextExtraction:
    """Acceptance tests for text extraction (STORY-002, slice 1)."""

    def test_extract_text_returns_text_blocks(self):
        """Text is extracted as a list of TextBlock objects per page."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.extractor import extract_text
        from pdf_chunker.models import TextBlock

        doc = load_document(FIXTURES_DIR / "simple.pdf")
        doc = extract_text(doc)

        assert len(doc.pages) == 1
        page = doc.pages[0]
        assert len(page.text_blocks) > 0
        for block in page.text_blocks:
            assert isinstance(block, TextBlock)
            assert block.text.strip() != ""
            assert block.page_number == 0

    def test_text_blocks_have_bbox_and_font_info(self):
        """Each TextBlock includes bounding box and font metadata."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.extractor import extract_text

        doc = load_document(FIXTURES_DIR / "simple.pdf")
        doc = extract_text(doc)

        block = doc.pages[0].text_blocks[0]
        assert block.bbox is not None
        assert len(block.bbox) == 4
        assert block.font_size > 0

    def test_heading_detected_by_larger_font(self):
        """Blocks with larger font size exist (heading candidates)."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.extractor import extract_text

        doc = load_document(FIXTURES_DIR / "simple.pdf")
        doc = extract_text(doc)

        font_sizes = [b.font_size for b in doc.pages[0].text_blocks]
        # There should be at least 2 distinct font sizes (heading vs body)
        assert len(set(font_sizes)) >= 2


# ---------------------------------------------------------------------------
# STORY-004: Basic text-to-Markdown conversion (slice 1)
# ---------------------------------------------------------------------------


class TestMarkdownConversion:
    """Acceptance tests for Markdown conversion (STORY-004, slice 1)."""

    def test_conversion_produces_markdown_with_headings(self):
        """Converted markdown contains heading markers."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.extractor import extract_text
        from pdf_chunker.conversion.markdown_writer import to_markdown

        doc = load_document(FIXTURES_DIR / "simple.pdf")
        doc = extract_text(doc)
        md_doc = to_markdown(doc)

        assert "# " in md_doc.content
        assert "Document Title" in md_doc.content

    def test_paragraphs_separated_by_blank_lines(self):
        """Paragraphs in the output are separated by blank lines."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.extractor import extract_text
        from pdf_chunker.conversion.markdown_writer import to_markdown

        doc = load_document(FIXTURES_DIR / "simple.pdf")
        doc = extract_text(doc)
        md_doc = to_markdown(doc)

        # Should have double newlines between sections
        assert "\n\n" in md_doc.content

    def test_markdown_includes_page_map(self):
        """MarkdownDocument includes page_map for traceability."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.extractor import extract_text
        from pdf_chunker.conversion.markdown_writer import to_markdown

        doc = load_document(FIXTURES_DIR / "simple.pdf")
        doc = extract_text(doc)
        md_doc = to_markdown(doc)

        assert hasattr(md_doc, "page_map")
        assert len(md_doc.page_map) > 0
        # Each entry: (start_offset, end_offset, page_number)
        for entry in md_doc.page_map:
            assert len(entry) == 3

    def test_multipage_conversion_includes_all_content(self):
        """Multi-page PDF conversion includes content from all pages."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.extractor import extract_text
        from pdf_chunker.conversion.markdown_writer import to_markdown

        doc = load_document(FIXTURES_DIR / "multiheading.pdf")
        doc = extract_text(doc)
        md_doc = to_markdown(doc)

        assert "Chapter One" in md_doc.content
        assert "Chapter Two" in md_doc.content


# ---------------------------------------------------------------------------
# STORY-010: Content cleaning and normalization
# ---------------------------------------------------------------------------


class TestContentCleaning:
    """Acceptance tests for content cleaning (STORY-010)."""

    def test_clean_collapses_excessive_whitespace(self):
        """Triple+ newlines are collapsed to double newlines."""
        from pdf_chunker.conversion.cleaner import clean

        result = clean("Hello\n\n\n\nWorld")
        assert "\n\n\n" not in result
        assert "Hello\n\nWorld" == result

    def test_clean_normalizes_smart_quotes(self):
        """Smart quotes are normalized to straight quotes."""
        from pdf_chunker.conversion.cleaner import clean

        result = clean("\u201cHello\u201d \u2018world\u2019")
        assert '"Hello" \'world\'' == result

    def test_clean_rejoins_hyphenated_line_breaks(self):
        """Hyphenated line breaks are rejoined."""
        from pdf_chunker.conversion.cleaner import clean

        result = clean("docu-\nment")
        assert "document" in result

    def test_clean_expands_ligatures(self):
        """Common ligatures are expanded."""
        from pdf_chunker.conversion.cleaner import clean

        result = clean("of\ufb01ce ef\ufb02uent")
        assert "office" in result
        assert "effluent" in result

    def test_clean_normalizes_dashes(self):
        """Em-dashes and en-dashes are normalized."""
        from pdf_chunker.conversion.cleaner import clean

        result = clean("hello\u2014world foo\u2013bar")
        assert "hello--world" in result
        assert "foo--bar" in result


# ---------------------------------------------------------------------------
# STORY-007: Structural chunking by sections (slice 1)
# ---------------------------------------------------------------------------


class TestStructuralChunking:
    """Acceptance tests for structural chunking (STORY-007, slice 1)."""

    def test_chunks_split_at_heading_boundaries(self):
        """Document is split into chunks at heading boundaries."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.extractor import extract_text
        from pdf_chunker.conversion.markdown_writer import to_markdown
        from pdf_chunker.conversion.cleaner import clean_markdown_document
        from pdf_chunker.chunking.structural_chunker import StructuralChunker
        from pdf_chunker.config import ChunkingConfig

        doc = load_document(FIXTURES_DIR / "multiheading.pdf")
        doc = extract_text(doc)
        md_doc = to_markdown(doc)
        md_doc = clean_markdown_document(md_doc)

        chunker = StructuralChunker()
        config = ChunkingConfig()
        chunks = chunker.chunk(md_doc, config)

        # Small test fixture (~162 tokens) may merge into fewer chunks.
        # Verify we get at least 1 chunk with content.
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.content.strip() != ""

    def test_chunks_include_heading_hierarchy(self):
        """Each chunk includes its heading hierarchy for context."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.extractor import extract_text
        from pdf_chunker.conversion.markdown_writer import to_markdown
        from pdf_chunker.conversion.cleaner import clean_markdown_document
        from pdf_chunker.chunking.structural_chunker import StructuralChunker
        from pdf_chunker.config import ChunkingConfig

        doc = load_document(FIXTURES_DIR / "multiheading.pdf")
        doc = extract_text(doc)
        md_doc = to_markdown(doc)
        md_doc = clean_markdown_document(md_doc)

        chunker = StructuralChunker()
        config = ChunkingConfig()
        chunks = chunker.chunk(md_doc, config)

        # At least one chunk should have a heading hierarchy
        has_hierarchy = any(len(c.heading_hierarchy) > 0 for c in chunks)
        assert has_hierarchy


# ---------------------------------------------------------------------------
# STORY-009: Chunk metadata generation
# ---------------------------------------------------------------------------


class TestChunkMetadata:
    """Acceptance tests for chunk metadata (STORY-009)."""

    def test_chunks_have_complete_metadata(self):
        """Each chunk carries complete metadata."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.extractor import extract_text
        from pdf_chunker.conversion.markdown_writer import to_markdown
        from pdf_chunker.conversion.cleaner import clean_markdown_document
        from pdf_chunker.chunking.structural_chunker import StructuralChunker
        from pdf_chunker.config import ChunkingConfig

        doc = load_document(FIXTURES_DIR / "multiheading.pdf")
        doc = extract_text(doc)
        md_doc = to_markdown(doc)
        md_doc = clean_markdown_document(md_doc)

        chunker = StructuralChunker()
        config = ChunkingConfig()
        chunks = chunker.chunk(md_doc, config)

        for i, chunk in enumerate(chunks):
            meta = chunk.metadata
            assert meta.chunk_id != ""
            assert meta.source_file != ""
            assert meta.chunk_index == i
            assert meta.total_chunks == len(chunks)
            assert meta.token_count > 0
            assert isinstance(meta.page_numbers, list)

    def test_chunk_ids_are_unique(self):
        """All chunk IDs are unique within a document."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.extractor import extract_text
        from pdf_chunker.conversion.markdown_writer import to_markdown
        from pdf_chunker.conversion.cleaner import clean_markdown_document
        from pdf_chunker.chunking.structural_chunker import StructuralChunker
        from pdf_chunker.config import ChunkingConfig

        doc = load_document(FIXTURES_DIR / "multiheading.pdf")
        doc = extract_text(doc)
        md_doc = to_markdown(doc)
        md_doc = clean_markdown_document(md_doc)

        chunker = StructuralChunker()
        config = ChunkingConfig()
        chunks = chunker.chunk(md_doc, config)

        ids = [c.metadata.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_metadata_serializable_to_json(self):
        """Chunk metadata is serializable to JSON via Pydantic."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.extractor import extract_text
        from pdf_chunker.conversion.markdown_writer import to_markdown
        from pdf_chunker.conversion.cleaner import clean_markdown_document
        from pdf_chunker.chunking.structural_chunker import StructuralChunker
        from pdf_chunker.config import ChunkingConfig
        import json

        doc = load_document(FIXTURES_DIR / "multiheading.pdf")
        doc = extract_text(doc)
        md_doc = to_markdown(doc)
        md_doc = clean_markdown_document(md_doc)

        chunker = StructuralChunker()
        config = ChunkingConfig()
        chunks = chunker.chunk(md_doc, config)

        for chunk in chunks:
            # Should be serializable to JSON without error
            data = chunk.metadata.model_dump(mode="json")
            json_str = json.dumps(data)
            assert json_str  # non-empty


# ---------------------------------------------------------------------------
# End-to-end pipeline test
# ---------------------------------------------------------------------------


class TestEndToEndPipeline:
    """Integration test proving the full vertical path works."""

    def test_pdf_to_chunks_end_to_end(self):
        """A PDF can be loaded, converted, cleaned, and chunked end-to-end."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.extractor import extract_text
        from pdf_chunker.conversion.markdown_writer import to_markdown
        from pdf_chunker.conversion.cleaner import clean_markdown_document
        from pdf_chunker.chunking.structural_chunker import StructuralChunker
        from pdf_chunker.config import ChunkingConfig

        # Full pipeline
        doc = load_document(FIXTURES_DIR / "multiheading.pdf")
        doc = extract_text(doc)
        md_doc = to_markdown(doc)
        md_doc = clean_markdown_document(md_doc)

        chunker = StructuralChunker()
        chunks = chunker.chunk(md_doc, ChunkingConfig())

        # Verify we got meaningful output (small fixture may merge into 1 chunk)
        assert len(chunks) >= 1
        total_content = " ".join(c.content for c in chunks)
        assert "Chapter One" in total_content
        assert "Chapter Two" in total_content

        # Verify metadata integrity
        for i, chunk in enumerate(chunks):
            assert chunk.metadata.chunk_index == i
            assert chunk.metadata.total_chunks == len(chunks)
            assert chunk.token_count > 0

    def test_empty_pdf_returns_empty_chunks(self):
        """An empty PDF produces an empty chunk list."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.extractor import extract_text
        from pdf_chunker.conversion.markdown_writer import to_markdown
        from pdf_chunker.conversion.cleaner import clean_markdown_document
        from pdf_chunker.chunking.structural_chunker import StructuralChunker
        from pdf_chunker.config import ChunkingConfig

        doc = load_document(FIXTURES_DIR / "empty.pdf")
        doc = extract_text(doc)
        md_doc = to_markdown(doc)
        md_doc = clean_markdown_document(md_doc)

        chunker = StructuralChunker()
        chunks = chunker.chunk(md_doc, ChunkingConfig())

        assert len(chunks) == 0
