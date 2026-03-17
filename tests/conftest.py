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
    _create_table_pdf()
    _create_unstructured_pdf()


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


def _create_table_pdf():
    """A PDF with a table embedded between text."""
    pdf = FPDF()
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 10, "Report with Table", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Intro text
    pdf.set_font("Helvetica", "", 12)
    pdf.multi_cell(0, 6, "The following table shows quarterly results:")
    pdf.ln(4)

    # Table header
    pdf.set_font("Helvetica", "B", 11)
    col_w = 45
    pdf.cell(col_w, 8, "Quarter", border=1)
    pdf.cell(col_w, 8, "Revenue", border=1)
    pdf.cell(col_w, 8, "Profit", border=1)
    pdf.cell(col_w, 8, "Growth", border=1)
    pdf.ln()

    # Table rows
    pdf.set_font("Helvetica", "", 11)
    rows = [
        ("Q1 2025", "$1.2M", "$300K", "12%"),
        ("Q2 2025", "$1.5M", "$400K", "25%"),
        ("Q3 2025", "$1.8M", "$500K", "20%"),
        ("Q4 2025", "$2.1M", "$650K", "17%"),
    ]
    for row in rows:
        for val in row:
            pdf.cell(col_w, 8, val, border=1)
        pdf.ln()

    pdf.ln(4)

    # Closing text
    pdf.set_font("Helvetica", "", 12)
    pdf.multi_cell(0, 6, "The results demonstrate consistent growth across all quarters.")

    pdf.output(str(FIXTURES_DIR / "table.pdf"))


def _create_unstructured_pdf():
    """A PDF with no headings — just body text paragraphs. For sliding-window chunker testing."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "", 12)

    # Generate enough text for multiple chunks
    paragraphs = [
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor "
        "incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud "
        "exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
        "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu "
        "fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa "
        "qui officia deserunt mollit anim id est laborum.",
        "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque "
        "laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi "
        "architecto beatae vitae dicta sunt explicabo.",
        "Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia "
        "consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt. Neque porro "
        "quisquam est, qui dolorem ipsum quia dolor sit amet.",
        "At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis praesentium "
        "voluptatum deleniti atque corrupti quos dolores et quas molestias excepturi sint "
        "occaecati cupiditate non provident.",
    ]
    for p in paragraphs:
        pdf.multi_cell(0, 6, p)
        pdf.ln(4)

    pdf.output(str(FIXTURES_DIR / "unstructured.pdf"))
