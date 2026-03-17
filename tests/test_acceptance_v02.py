"""
Acceptance tests for v0.2: CLI, JSON Output, and Error Handling.

Stories: STORY-011 (CLI), STORY-012 (JSON output), STORY-014 (error handling/logging)
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# STORY-011: CLI with file and directory input
# ---------------------------------------------------------------------------


class TestCLISingleFile:
    """CLI processes a single PDF file."""

    def test_process_single_pdf(self, tmp_path):
        """pdf-chunker <file> processes a PDF and creates output."""
        from pdf_chunker.cli import main

        runner = CliRunner()
        result = runner.invoke(main, [
            str(FIXTURES_DIR / "simple.pdf"),
            "--output", str(tmp_path),
        ])
        assert result.exit_code == 0
        # Output file should exist
        output_files = list(tmp_path.glob("*.json"))
        assert len(output_files) == 1

    def test_output_file_named_after_input(self, tmp_path):
        """Output file is named {stem}_chunks.json."""
        from pdf_chunker.cli import main

        runner = CliRunner()
        runner.invoke(main, [
            str(FIXTURES_DIR / "simple.pdf"),
            "--output", str(tmp_path),
        ])
        expected = tmp_path / "simple_chunks.json"
        assert expected.exists()


class TestCLIDirectory:
    """CLI processes a directory of PDFs."""

    def test_process_directory(self, tmp_path):
        """pdf-chunker <directory> processes all PDFs in it."""
        from pdf_chunker.cli import main

        runner = CliRunner()
        result = runner.invoke(main, [
            str(FIXTURES_DIR),
            "--output", str(tmp_path),
        ])
        # Should process simple.pdf, multiheading.pdf, empty.pdf
        # corrupted.pdf should fail but not crash
        assert result.exit_code in (0, 1)  # 0=all success, 1=partial failure
        output_files = list(tmp_path.glob("*.json"))
        assert len(output_files) >= 2  # At least simple + multiheading

    def test_recursive_flag(self, tmp_path):
        """--recursive enables recursive directory traversal."""
        from pdf_chunker.cli import main

        # Create a nested directory with a PDF
        nested = tmp_path / "input" / "subdir"
        nested.mkdir(parents=True)
        import shutil
        shutil.copy(FIXTURES_DIR / "simple.pdf", nested / "nested.pdf")

        out = tmp_path / "output"
        runner = CliRunner()
        result = runner.invoke(main, [
            str(tmp_path / "input"),
            "--output", str(out),
            "--recursive",
        ])
        assert result.exit_code == 0
        assert (out / "nested_chunks.json").exists()


class TestCLIOptions:
    """CLI options work correctly."""

    def test_default_output_directory(self, tmp_path, monkeypatch):
        """Default output goes to ./output/."""
        from pdf_chunker.cli import main

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, [str(FIXTURES_DIR / "simple.pdf")])
        assert result.exit_code == 0
        assert (tmp_path / "output" / "simple_chunks.json").exists()

    def test_exit_code_0_on_success(self, tmp_path):
        """Exit code 0 on full success."""
        from pdf_chunker.cli import main

        runner = CliRunner()
        result = runner.invoke(main, [
            str(FIXTURES_DIR / "simple.pdf"),
            "--output", str(tmp_path),
        ])
        assert result.exit_code == 0

    def test_exit_code_2_on_invalid_input(self):
        """Exit code 2 for invalid input path."""
        from pdf_chunker.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["/nonexistent/path"])
        assert result.exit_code == 2


# ---------------------------------------------------------------------------
# STORY-012: JSON output format
# ---------------------------------------------------------------------------


class TestJSONOutput:
    """JSON output format is correct and parseable."""

    def test_json_output_valid_and_parseable(self, tmp_path):
        """Output JSON is valid and parseable."""
        from pdf_chunker.cli import main

        runner = CliRunner()
        runner.invoke(main, [
            str(FIXTURES_DIR / "simple.pdf"),
            "--output", str(tmp_path),
        ])

        output_file = tmp_path / "simple_chunks.json"
        data = json.loads(output_file.read_text())
        assert isinstance(data, dict)

    def test_json_output_schema(self, tmp_path):
        """JSON output has correct schema structure."""
        from pdf_chunker.cli import main

        runner = CliRunner()
        runner.invoke(main, [
            str(FIXTURES_DIR / "simple.pdf"),
            "--output", str(tmp_path),
        ])

        data = json.loads((tmp_path / "simple_chunks.json").read_text())
        assert "source" in data
        assert "total_chunks" in data
        assert "chunks" in data
        assert isinstance(data["chunks"], list)
        assert data["total_chunks"] == len(data["chunks"])

    def test_json_chunk_structure(self, tmp_path):
        """Each chunk in JSON has the expected fields."""
        from pdf_chunker.cli import main

        runner = CliRunner()
        runner.invoke(main, [
            str(FIXTURES_DIR / "simple.pdf"),
            "--output", str(tmp_path),
        ])

        data = json.loads((tmp_path / "simple_chunks.json").read_text())
        for chunk in data["chunks"]:
            assert "chunk_id" in chunk
            assert "content" in chunk
            assert "metadata" in chunk
            meta = chunk["metadata"]
            assert "source_file" in meta
            assert "page_numbers" in meta
            assert "chunk_index" in meta
            assert "token_count" in meta

    def test_json_pretty_printed_by_default(self, tmp_path):
        """JSON output is pretty-printed by default."""
        from pdf_chunker.cli import main

        runner = CliRunner()
        runner.invoke(main, [
            str(FIXTURES_DIR / "simple.pdf"),
            "--output", str(tmp_path),
        ])

        content = (tmp_path / "simple_chunks.json").read_text()
        # Pretty-printed JSON has newlines and indentation
        assert "\n" in content
        assert "  " in content

    def test_compact_json_flag(self, tmp_path):
        """--compact produces minified JSON."""
        from pdf_chunker.cli import main

        runner = CliRunner()
        runner.invoke(main, [
            str(FIXTURES_DIR / "simple.pdf"),
            "--output", str(tmp_path),
            "--compact",
        ])

        content = (tmp_path / "simple_chunks.json").read_text()
        # Compact JSON should be a single line (or very few lines)
        lines = [l for l in content.strip().split("\n") if l.strip()]
        assert len(lines) == 1


# ---------------------------------------------------------------------------
# STORY-014: Error handling and logging
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Error handling and logging work correctly."""

    def test_corrupted_pdf_skipped_not_crash(self, tmp_path):
        """Corrupted PDF is skipped, doesn't crash the process."""
        from pdf_chunker.cli import main

        runner = CliRunner()
        result = runner.invoke(main, [
            str(FIXTURES_DIR / "corrupted.pdf"),
            "--output", str(tmp_path),
        ])
        # Should not crash — exit code 1 or 2 is acceptable (not an unhandled exception)
        assert result.exit_code in (1, 2)
        # Verify no unhandled exception (SystemExit is expected from Click)
        if result.exception is not None:
            assert isinstance(result.exception, SystemExit)

    def test_summary_printed_at_end(self, tmp_path):
        """A processing summary is printed at the end."""
        from pdf_chunker.cli import main

        runner = CliRunner()
        result = runner.invoke(main, [
            str(FIXTURES_DIR / "simple.pdf"),
            "--output", str(tmp_path),
        ])
        # Should contain summary info
        assert "processed" in result.output.lower() or "chunk" in result.output.lower()

    def test_verbose_flag_increases_output(self, tmp_path):
        """--verbose produces more detailed output."""
        from pdf_chunker.cli import main

        runner = CliRunner()
        result_normal = runner.invoke(main, [
            str(FIXTURES_DIR / "simple.pdf"),
            "--output", str(tmp_path / "normal"),
        ])
        result_verbose = runner.invoke(main, [
            str(FIXTURES_DIR / "simple.pdf"),
            "--output", str(tmp_path / "verbose"),
            "--verbose",
        ])
        # Verbose output should be at least as long as normal
        assert len(result_verbose.output) >= len(result_normal.output)

    def test_partial_failure_exit_code_1(self, tmp_path):
        """Mixed success/failure in a directory gives exit code 1."""
        from pdf_chunker.cli import main

        # Process fixtures dir which has both valid and corrupted PDFs
        runner = CliRunner()
        result = runner.invoke(main, [
            str(FIXTURES_DIR),
            "--output", str(tmp_path),
        ])
        assert result.exit_code == 1  # Partial failure

    def test_no_pdfs_in_directory(self, tmp_path):
        """Empty directory gives exit code 0 with a message."""
        from pdf_chunker.cli import main

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(main, [
            str(empty_dir),
            "--output", str(tmp_path / "output"),
        ])
        assert result.exit_code == 0
        assert "no pdf" in result.output.lower()
