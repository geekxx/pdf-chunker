"""Shared test fixtures for pdf-chunker tests."""

import os
from pathlib import Path

import pytest
from fpdf import FPDF

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session", autouse=True)
def create_fixture_pdfs():
    """Generate test PDF fixtures once per test session."""
    FIXTURES_DIR.mkdir(exist_ok=True)
    _create_simple_pdf()
    _create_multiheading_pdf()
    _create_corrupted_pdf()
    _create_empty_pdf()


def _create_simple_pdf():
    """A simple single-page PDF with a title, subtitle, and body text."""
    pdf = FPDF()
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(0, 12, "Document Title", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Subtitle
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Section One", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Body paragraph
    pdf.set_font("Helvetica", "", 12)
    pdf.multi_cell(0, 6, (
        "This is the first paragraph of section one. "
        "It contains some sample text that should be extracted "
        "as a coherent block during processing."
    ))
    pdf.ln(4)

    # Another subtitle
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Section Two", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Body paragraph
    pdf.set_font("Helvetica", "", 12)
    pdf.multi_cell(0, 6, (
        "This is the first paragraph of section two. "
        "It also contains sample text for testing purposes."
    ))

    pdf.output(str(FIXTURES_DIR / "simple.pdf"))


def _create_multiheading_pdf():
    """A multi-page PDF with multiple heading levels and sections."""
    pdf = FPDF()

    # Page 1
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 28)
    pdf.cell(0, 14, "Main Document Title", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 10, "Chapter One", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 12)
    pdf.multi_cell(0, 6, (
        "This is the introduction to chapter one. "
        "It provides context for the sections that follow. "
        "The content here is meant to be long enough to test chunking behavior "
        "when combined with other sections."
    ))
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Section 1.1", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 12)
    pdf.multi_cell(0, 6, (
        "Content for section 1.1. This discusses the first subtopic "
        "within chapter one. It should be chunked separately from the chapter intro."
    ))
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Section 1.2", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 12)
    pdf.multi_cell(0, 6, (
        "Content for section 1.2. This discusses the second subtopic. "
        "It covers additional material that warrants its own chunk."
    ))

    # Page 2
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 10, "Chapter Two", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 12)
    pdf.multi_cell(0, 6, (
        "Chapter two explores a completely different topic. "
        "This should definitely be in a separate chunk from chapter one content."
    ))
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Section 2.1", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 12)
    pdf.multi_cell(0, 6, (
        "Final section content. This wraps up the document with "
        "concluding material for testing purposes."
    ))

    pdf.output(str(FIXTURES_DIR / "multiheading.pdf"))


def _create_corrupted_pdf():
    """A file that looks like a PDF but is corrupted."""
    path = FIXTURES_DIR / "corrupted.pdf"
    path.write_bytes(b"%PDF-1.4 this is not a valid pdf content\x00\x00")


def _create_empty_pdf():
    """A valid PDF with no text content (just a blank page)."""
    pdf = FPDF()
    pdf.add_page()
    pdf.output(str(FIXTURES_DIR / "empty.pdf"))
