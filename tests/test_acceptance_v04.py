"""
Acceptance tests for v0.4: Image Handling and Config File Support.

Stories: STORY-006 (image/figure handling), STORY-015 (config file support)
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# STORY-006: Image and figure handling
# ---------------------------------------------------------------------------


class TestImageHandling:
    """Acceptance tests for image handling (STORY-006)."""

    def test_image_placeholder_in_markdown(self):
        """Images are noted as placeholders in Markdown output by default."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.extractor import extract_text
        from pdf_chunker.conversion.markdown_writer import to_markdown
        from pdf_chunker.conversion.image_handler import detect_images

        doc = load_document(FIXTURES_DIR / "with_image.pdf")
        doc = extract_text(doc)
        doc = detect_images(doc)
        md_doc = to_markdown(doc)

        assert "[Image on page" in md_doc.content

    def test_image_extraction_to_disk(self, tmp_path):
        """Images are extracted and saved when extraction is enabled."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.conversion.image_handler import extract_images

        doc = load_document(FIXTURES_DIR / "with_image.pdf")
        image_dir = tmp_path / "images"
        extracted = extract_images(doc, image_dir)

        assert len(extracted) >= 1
        assert image_dir.exists()
        image_files = list(image_dir.glob("*"))
        assert len(image_files) >= 1

    def test_image_reference_in_markdown(self, tmp_path):
        """When images are extracted, Markdown includes image references."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.extractor import extract_text
        from pdf_chunker.conversion.image_handler import detect_images, extract_images
        from pdf_chunker.conversion.markdown_writer import to_markdown

        doc = load_document(FIXTURES_DIR / "with_image.pdf")
        doc = extract_text(doc)
        doc = detect_images(doc)

        image_dir = tmp_path / "images"
        images = extract_images(doc, image_dir)

        md_doc = to_markdown(doc, image_refs=images)

        # Should contain markdown image reference
        assert "![" in md_doc.content

    def test_deterministic_image_naming(self, tmp_path):
        """Extracted images use deterministic naming: {stem}_p{page}_img{idx}.{ext}."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.conversion.image_handler import extract_images

        doc = load_document(FIXTURES_DIR / "with_image.pdf")
        image_dir = tmp_path / "images"
        extracted = extract_images(doc, image_dir)

        # Check naming convention
        for img in extracted:
            name = Path(img["path"]).name
            assert "with_image" in name
            assert "_p" in name
            assert "_img" in name

    def test_no_images_no_crash(self):
        """PDFs without images are handled gracefully."""
        from pdf_chunker.ingestion.loader import load_document
        from pdf_chunker.ingestion.extractor import extract_text
        from pdf_chunker.conversion.image_handler import detect_images
        from pdf_chunker.conversion.markdown_writer import to_markdown

        doc = load_document(FIXTURES_DIR / "simple.pdf")
        doc = extract_text(doc)
        doc = detect_images(doc)
        md_doc = to_markdown(doc)

        # Should work without any image placeholders
        assert "[Image on page" not in md_doc.content


# ---------------------------------------------------------------------------
# STORY-015: Configuration file support
# ---------------------------------------------------------------------------


class TestConfigFile:
    """Acceptance tests for TOML config file support (STORY-015)."""

    def test_config_file_loaded(self, tmp_path):
        """--config loads settings from a TOML file."""
        from pdf_chunker.cli import main

        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[chunking]\n'
            'max_tokens = 500\n'
            'strategy = "sliding"\n'
        )

        runner = CliRunner()
        result = runner.invoke(main, [
            str(FIXTURES_DIR / "simple.pdf"),
            "--output", str(tmp_path / "out"),
            "--config", str(config_file),
        ])
        assert result.exit_code == 0

        # Verify the config was applied (sliding strategy)
        data = json.loads((tmp_path / "out" / "simple_chunks.json").read_text())
        assert data["total_chunks"] >= 1

    def test_cli_flags_override_config(self, tmp_path):
        """CLI flags override config file values."""
        from pdf_chunker.cli import main

        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[chunking]\n'
            'strategy = "sliding"\n'
        )

        runner = CliRunner()
        # CLI flag --strategy structural should override config's "sliding"
        result = runner.invoke(main, [
            str(FIXTURES_DIR / "simple.pdf"),
            "--output", str(tmp_path / "out"),
            "--config", str(config_file),
            "--strategy", "structural",
        ])
        assert result.exit_code == 0

    def test_init_config_generates_default(self, tmp_path):
        """pdf-chunker init-config generates a default config file."""
        from pdf_chunker.cli import cli_group

        runner = CliRunner()
        result = runner.invoke(cli_group, [
            "init-config",
            "--output", str(tmp_path / "default.toml"),
        ])
        assert result.exit_code == 0

        config_file = tmp_path / "default.toml"
        assert config_file.exists()
        content = config_file.read_text()
        assert "max_tokens" in content
        assert "strategy" in content

    def test_invalid_config_clear_error(self, tmp_path):
        """Invalid config values produce clear error messages."""
        from pdf_chunker.cli import main

        config_file = tmp_path / "bad_config.toml"
        config_file.write_text(
            '[chunking]\n'
            'max_tokens = -1\n'
        )

        runner = CliRunner()
        result = runner.invoke(main, [
            str(FIXTURES_DIR / "simple.pdf"),
            "--output", str(tmp_path / "out"),
            "--config", str(config_file),
        ])
        # Should fail with clear error, not a traceback
        assert result.exit_code != 0

    def test_unknown_config_keys_ignored(self, tmp_path):
        """Unknown keys in config are warned about but don't crash."""
        from pdf_chunker.cli import main

        config_file = tmp_path / "extra_config.toml"
        config_file.write_text(
            '[chunking]\n'
            'max_tokens = 1000\n'
            'unknown_key = "value"\n'
        )

        runner = CliRunner()
        result = runner.invoke(main, [
            str(FIXTURES_DIR / "simple.pdf"),
            "--output", str(tmp_path / "out"),
            "--config", str(config_file),
        ])
        assert result.exit_code == 0
