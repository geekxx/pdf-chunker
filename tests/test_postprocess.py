"""Tests for post-processing: watermark stripping, chunk filtering, quality report."""

import pytest
from pdf_chunker.chunking.postprocess import (
    strip_watermarks,
    filter_chunks,
    print_quality_report,
    PostProcessingReport,
)
from pdf_chunker.config import ChunkingConfig
from pdf_chunker.models import Chunk, ChunkMetadata


def _make_chunk(content: str, index: int = 0, hierarchy: list[str] | None = None, token_count: int | None = None) -> Chunk:
    hierarchy = hierarchy or []
    if token_count is None:
        token_count = len(content.split())
    return Chunk(
        content=content,
        metadata=ChunkMetadata(
            chunk_id=f"test{index}",
            source_file="test.pdf",
            page_numbers=[1],
            chunk_index=index,
            total_chunks=0,
            token_count=token_count,
            heading_hierarchy=hierarchy,
        ),
        token_count=token_count,
        heading_hierarchy=hierarchy,
    )


class TestStripWatermarks:
    def test_removes_watermark_line(self):
        content = "Some text\nJeff Heinen (Order #48779060)\nMore text"
        report = PostProcessingReport()
        result = strip_watermarks(content, report)
        assert "(Order #" not in result
        assert "Some text" in result
        assert "More text" in result
        assert report.watermark_lines_stripped == 1

    def test_removes_orphaned_author_after_watermark(self):
        content = "Some text\nJeff Heinen (Order #48779060)\nMatt Davids\nMore text"
        report = PostProcessingReport()
        result = strip_watermarks(content, report)
        assert "(Order #" not in result
        assert "Matt Davids" not in result
        assert "More text" in result
        assert report.watermark_lines_stripped == 1
        assert report.orphan_lines_stripped == 1

    def test_does_not_remove_lowercase_continuation(self):
        content = "Some text\nJeff Heinen (Order #48779060)\nand then some more text follows here"
        report = PostProcessingReport()
        result = strip_watermarks(content, report)
        assert "and then some more text" in result

    def test_handles_multiple_watermarks(self):
        content = "A\nJohn Doe (Order #12345678)\nB\nJane Smith (Order #99999999)\nC"
        report = PostProcessingReport()
        result = strip_watermarks(content, report)
        assert "(Order #" not in result
        assert report.watermark_lines_stripped == 2

    def test_no_watermarks_unchanged(self):
        content = "Just normal content\nwith no watermarks"
        report = PostProcessingReport()
        result = strip_watermarks(content, report)
        assert result == content
        assert report.watermark_lines_stripped == 0

    def test_collapses_extra_newlines(self):
        content = "Before\n\nJeff Heinen (Order #48779060)\n\nAfter"
        result = strip_watermarks(content)
        assert "\n\n\n" not in result


class TestFilterChunks:
    def test_filters_table_of_contents(self):
        chunks = [
            _make_chunk("## TOC\nPage 1...3", hierarchy=["Table of Contents"], token_count=50),
            _make_chunk("## Chapter 1\nReal content here.", hierarchy=["Chapter 1"], token_count=200),
        ]
        config = ChunkingConfig()
        report = PostProcessingReport()
        result = filter_chunks(chunks, config, report)
        assert len(result) == 1
        assert result[0].heading_hierarchy == ["Chapter 1"]
        assert len(report.chunks_filtered) == 1

    def test_filters_other_books(self):
        chunks = [
            _make_chunk("Content", hierarchy=["Chapter 1"], token_count=200),
            _make_chunk("Book list", hierarchy=["Other Books by Author"], token_count=100),
        ]
        config = ChunkingConfig()
        result = filter_chunks(chunks, config)
        assert len(result) == 1

    def test_filters_marketing(self):
        chunks = [
            _make_chunk("Content", hierarchy=["Chapter 1"], token_count=200),
            _make_chunk("Sign up now!", hierarchy=["Get Free Updates", "Subscribe"], token_count=50),
        ]
        config = ChunkingConfig()
        result = filter_chunks(chunks, config)
        assert len(result) == 1

    def test_filters_tiny_heading_only_chunks(self):
        chunks = [
            _make_chunk("# Title", hierarchy=["Title"], token_count=5),
            _make_chunk("## Chapter 1\nReal content.", hierarchy=["Chapter 1"], token_count=200),
        ]
        config = ChunkingConfig()
        result = filter_chunks(chunks, config)
        assert len(result) == 1

    def test_reindexes_after_filtering(self):
        chunks = [
            _make_chunk("A", index=0, hierarchy=["Table of Contents"], token_count=50),
            _make_chunk("B", index=1, hierarchy=["Chapter 1"], token_count=200),
            _make_chunk("C", index=2, hierarchy=["Chapter 2"], token_count=200),
        ]
        config = ChunkingConfig()
        result = filter_chunks(chunks, config)
        assert len(result) == 2
        assert result[0].metadata.chunk_index == 0
        assert result[1].metadata.chunk_index == 1
        assert result[0].metadata.total_chunks == 2

    def test_no_filtering_with_empty_patterns(self):
        chunks = [
            _make_chunk("TOC stuff", hierarchy=["Table of Contents"], token_count=50),
        ]
        config = ChunkingConfig(skip_patterns=[])
        result = filter_chunks(chunks, config)
        assert len(result) == 1


class TestQualityReport:
    def test_report_includes_totals(self):
        chunks = [
            _make_chunk("A" * 100, token_count=150),
            _make_chunk("B" * 200, token_count=500),
        ]
        report = PostProcessingReport()
        text = print_quality_report(chunks, report, "test.pdf")
        assert "Total chunks: 2" in text
        assert "Total tokens: 650" in text

    def test_report_shows_buckets(self):
        chunks = [
            _make_chunk("x", token_count=5),
            _make_chunk("x", token_count=500),
        ]
        report = PostProcessingReport()
        text = print_quality_report(chunks, report)
        assert "junk (<10)" in text
        assert "good (300-1000)" in text

    def test_report_shows_watermark_stats(self):
        report = PostProcessingReport(watermark_lines_stripped=10, orphan_lines_stripped=5)
        text = print_quality_report([], report)
        assert "Watermark lines stripped: 10" in text
        assert "Orphaned author lines stripped: 5" in text

    def test_report_shows_filtered_chunks(self):
        report = PostProcessingReport(chunks_filtered=[(0, "Table of Contents", "pattern match")])
        text = print_quality_report([], report)
        assert "Chunks filtered out: 1" in text
        assert "Table of Contents" in text
