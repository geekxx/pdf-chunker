"""
Acceptance tests for v0.3: Tables, Sliding Window Chunker, Markdown Output.

Stories: STORY-003 (table extraction), STORY-005 (table-to-markdown),
         STORY-008 (sliding-window chunker), STORY-013 (markdown output format)
"""

import json
import yaml
from pathlib import Path

import pytest
from click.testing import CliRunner

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# STORY-003: Table extraction from PDFs
# ---------------------------------------------------------------------------


class TestTableExtraction:
    """Acceptance tests for table extraction (STORY-003)."""

    def test_tables_detected_on_page(self):
        """Tables are detected on pages that contain them."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.table_extractor import extract_tables
        from pdf_chunker.models import Table

        doc = load_document(FIXTURES_DIR / "table.pdf")
        doc = extract_tables(doc)

        assert len(doc.pages) == 1
        page = doc.pages[0]
        assert len(page.tables) >= 1
        assert isinstance(page.tables[0], Table)

    def test_table_rows_and_columns(self):
        """Cell contents extracted with correct row/column associations."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.table_extractor import extract_tables

        doc = load_document(FIXTURES_DIR / "table.pdf")
        doc = extract_tables(doc)

        table = doc.pages[0].tables[0]
        # Should have header + 4 data rows = 5 rows
        assert len(table.rows) >= 4
        # Should have 4 columns
        assert all(len(row) == 4 for row in table.rows)

    def test_table_contains_expected_data(self):
        """Table cell contents match expected values."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.table_extractor import extract_tables

        doc = load_document(FIXTURES_DIR / "table.pdf")
        doc = extract_tables(doc)

        table = doc.pages[0].tables[0]
        all_text = " ".join(" ".join(row) for row in table.rows)
        assert "Q1 2025" in all_text or "Q1" in all_text
        assert "Revenue" in all_text or "1.2" in all_text

    def test_page_without_tables_returns_empty(self):
        """Pages with no tables return an empty table list."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.table_extractor import extract_tables

        doc = load_document(FIXTURES_DIR / "simple.pdf")
        doc = extract_tables(doc)

        for page in doc.pages:
            assert len(page.tables) == 0

    def test_table_has_page_number(self):
        """Each table includes its page number."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.table_extractor import extract_tables

        doc = load_document(FIXTURES_DIR / "table.pdf")
        doc = extract_tables(doc)

        for page in doc.pages:
            for table in page.tables:
                assert table.page_number == page.page_number


# ---------------------------------------------------------------------------
# STORY-005: Table-to-Markdown conversion
# ---------------------------------------------------------------------------


class TestTableToMarkdown:
    """Acceptance tests for table-to-Markdown conversion (STORY-005)."""

    def test_table_rendered_as_gfm_pipe_table(self):
        """Tables are rendered using GFM pipe table syntax."""
        from pdf_chunker.conversion.markdown_writer import table_to_markdown
        from pdf_chunker.models import Table

        table = Table(
            rows=[
                ["Name", "Age", "City"],
                ["Alice", "30", "NYC"],
                ["Bob", "25", "LA"],
            ],
            page_number=0,
            bbox=(0, 0, 100, 100),
            has_header_row=True,
        )
        md = table_to_markdown(table)

        assert "|" in md
        assert "---" in md  # separator row
        assert "Name" in md
        assert "Alice" in md

    def test_header_row_separated(self):
        """First row treated as header when has_header_row is true."""
        from pdf_chunker.conversion.markdown_writer import table_to_markdown
        from pdf_chunker.models import Table

        table = Table(
            rows=[["H1", "H2"], ["A", "B"]],
            page_number=0,
            bbox=(0, 0, 100, 100),
            has_header_row=True,
        )
        md = table_to_markdown(table)
        lines = [l for l in md.strip().split("\n") if l.strip()]

        # Line 0: header, Line 1: separator, Line 2+: data
        assert "H1" in lines[0]
        assert "---" in lines[1]
        assert "A" in lines[2]

    def test_pipe_chars_escaped(self):
        """Cell contents containing pipe characters are escaped."""
        from pdf_chunker.conversion.markdown_writer import table_to_markdown
        from pdf_chunker.models import Table

        table = Table(
            rows=[["Col1", "Col2"], ["val|ue", "normal"]],
            page_number=0,
            bbox=(0, 0, 100, 100),
            has_header_row=True,
        )
        md = table_to_markdown(table)
        assert r"val\|ue" in md

    def test_empty_cells_render(self):
        """Empty cells render correctly."""
        from pdf_chunker.conversion.markdown_writer import table_to_markdown
        from pdf_chunker.models import Table

        table = Table(
            rows=[["A", "B"], ["", "data"]],
            page_number=0,
            bbox=(0, 0, 100, 100),
            has_header_row=True,
        )
        md = table_to_markdown(table)
        assert "data" in md
        # Should still have proper pipe structure
        for line in md.strip().split("\n"):
            if line.strip():
                assert line.strip().startswith("|")
                assert line.strip().endswith("|")

    def test_table_in_full_conversion(self):
        """Tables appear in the full document markdown conversion."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.extractor import extract_text
        from pdf_chunker.ingestion.table_extractor import extract_tables
        from pdf_chunker.conversion.markdown_writer import to_markdown

        doc = load_document(FIXTURES_DIR / "table.pdf")
        doc = extract_text(doc)
        doc = extract_tables(doc)
        md_doc = to_markdown(doc)

        # The markdown should contain pipe table syntax
        assert "|" in md_doc.content
        assert "---" in md_doc.content


# ---------------------------------------------------------------------------
# STORY-008: Sliding-window chunking with overlap
# ---------------------------------------------------------------------------


class TestSlidingWindowChunker:
    """Acceptance tests for sliding-window chunker (STORY-008)."""

    def test_chunks_created_with_configurable_size(self):
        """Document is split into chunks of configurable token size."""
        from pdf_chunker.chunking.window_chunker import SlidingWindowChunker
        from pdf_chunker.config import ChunkingConfig
        from pdf_chunker.models import MarkdownDocument

        content = "Word " * 500  # ~500 tokens
        md_doc = MarkdownDocument(
            content=content,
            source_path=Path("test.pdf"),
            page_map=[(0, len(content), 0)],
        )

        config = ChunkingConfig(strategy="sliding", max_tokens=100, overlap=20)
        chunker = SlidingWindowChunker()
        chunks = chunker.chunk(md_doc, config)

        assert len(chunks) >= 3  # 500 tokens / 100 per chunk ≈ 5-6 chunks

    def test_consecutive_chunks_overlap(self):
        """Consecutive chunks share overlapping content."""
        from pdf_chunker.chunking.window_chunker import SlidingWindowChunker
        from pdf_chunker.config import ChunkingConfig
        from pdf_chunker.models import MarkdownDocument

        # Create content with distinct words to verify overlap
        words = [f"word{i}" for i in range(200)]
        content = " ".join(words)
        md_doc = MarkdownDocument(
            content=content,
            source_path=Path("test.pdf"),
            page_map=[(0, len(content), 0)],
        )

        config = ChunkingConfig(strategy="sliding", max_tokens=50, overlap=10)
        chunker = SlidingWindowChunker()
        chunks = chunker.chunk(md_doc, config)

        # Check that consecutive chunks share some content
        if len(chunks) >= 2:
            words_chunk0 = set(chunks[0].content.split())
            words_chunk1 = set(chunks[1].content.split())
            overlap = words_chunk0 & words_chunk1
            assert len(overlap) > 0

    def test_chunks_have_metadata(self):
        """Each chunk from sliding window has proper metadata."""
        from pdf_chunker.chunking.window_chunker import SlidingWindowChunker
        from pdf_chunker.config import ChunkingConfig
        from pdf_chunker.models import MarkdownDocument

        content = "Text content here. " * 100
        md_doc = MarkdownDocument(
            content=content,
            source_path=Path("test.pdf"),
            page_map=[(0, len(content), 0)],
        )

        config = ChunkingConfig(strategy="sliding", max_tokens=50, overlap=10)
        chunker = SlidingWindowChunker()
        chunks = chunker.chunk(md_doc, config)

        for i, chunk in enumerate(chunks):
            assert chunk.metadata.chunk_index == i
            assert chunk.metadata.total_chunks == len(chunks)
            assert chunk.metadata.chunk_id != ""
            assert chunk.token_count > 0

    def test_empty_document_returns_empty(self):
        """Empty document returns empty chunk list."""
        from pdf_chunker.chunking.window_chunker import SlidingWindowChunker
        from pdf_chunker.config import ChunkingConfig
        from pdf_chunker.models import MarkdownDocument

        md_doc = MarkdownDocument(
            content="",
            source_path=Path("test.pdf"),
            page_map=[],
        )

        config = ChunkingConfig(strategy="sliding", max_tokens=100, overlap=20)
        chunker = SlidingWindowChunker()
        chunks = chunker.chunk(md_doc, config)

        assert len(chunks) == 0

    def test_cli_sliding_strategy(self, tmp_path):
        """CLI --strategy sliding uses the sliding window chunker."""
        from pdf_chunker.cli import main

        runner = CliRunner()
        result = runner.invoke(main, [
            str(FIXTURES_DIR / "simple.pdf"),
            "--output", str(tmp_path),
            "--strategy", "sliding",
        ])
        assert result.exit_code == 0
        output_file = tmp_path / "simple_chunks.json"
        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert data["total_chunks"] >= 1


# ---------------------------------------------------------------------------
# STORY-013: Markdown output format
# ---------------------------------------------------------------------------


class TestMarkdownOutputFormat:
    """Acceptance tests for Markdown output format (STORY-013)."""

    def test_markdown_format_creates_chunk_files(self, tmp_path):
        """--format markdown creates individual .md files per chunk."""
        from pdf_chunker.cli import main

        runner = CliRunner()
        result = runner.invoke(main, [
            str(FIXTURES_DIR / "multiheading.pdf"),
            "--output", str(tmp_path),
            "--format", "markdown",
        ])
        assert result.exit_code == 0

        doc_dir = tmp_path / "multiheading"
        assert doc_dir.exists()
        chunk_files = sorted(doc_dir.glob("chunk_*.md"))
        assert len(chunk_files) >= 1

    def test_chunk_files_have_yaml_frontmatter(self, tmp_path):
        """Each chunk .md file includes YAML frontmatter with metadata."""
        from pdf_chunker.cli import main

        runner = CliRunner()
        runner.invoke(main, [
            str(FIXTURES_DIR / "multiheading.pdf"),
            "--output", str(tmp_path),
            "--format", "markdown",
        ])

        doc_dir = tmp_path / "multiheading"
        chunk_files = sorted(doc_dir.glob("chunk_*.md"))
        assert len(chunk_files) >= 1

        content = chunk_files[0].read_text()
        assert content.startswith("---\n")
        # Parse YAML frontmatter
        parts = content.split("---\n", 2)
        assert len(parts) >= 3
        meta = yaml.safe_load(parts[1])
        assert "chunk_id" in meta
        assert "source_file" in meta

    def test_manifest_json_created(self, tmp_path):
        """A manifest.json file is created listing all chunks."""
        from pdf_chunker.cli import main

        runner = CliRunner()
        runner.invoke(main, [
            str(FIXTURES_DIR / "multiheading.pdf"),
            "--output", str(tmp_path),
            "--format", "markdown",
        ])

        manifest = tmp_path / "multiheading" / "manifest.json"
        assert manifest.exists()
        data = json.loads(manifest.read_text())
        assert isinstance(data, list) or "chunks" in data

    def test_full_markdown_saved(self, tmp_path):
        """Full pre-chunking markdown is saved as full.md."""
        from pdf_chunker.cli import main

        runner = CliRunner()
        runner.invoke(main, [
            str(FIXTURES_DIR / "multiheading.pdf"),
            "--output", str(tmp_path),
            "--format", "markdown",
        ])

        full_md = tmp_path / "multiheading" / "full.md"
        assert full_md.exists()
        content = full_md.read_text()
        assert "Chapter One" in content
        assert "Chapter Two" in content

    def test_chunk_file_naming_convention(self, tmp_path):
        """Chunk files follow naming: chunk_NNNN.md."""
        from pdf_chunker.cli import main

        runner = CliRunner()
        runner.invoke(main, [
            str(FIXTURES_DIR / "multiheading.pdf"),
            "--output", str(tmp_path),
            "--format", "markdown",
        ])

        doc_dir = tmp_path / "multiheading"
        chunk_files = sorted(doc_dir.glob("chunk_*.md"))
        for i, f in enumerate(chunk_files):
            expected_name = f"chunk_{i:04d}.md"
            assert f.name == expected_name
