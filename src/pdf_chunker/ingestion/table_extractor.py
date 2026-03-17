import pdfplumber
from pathlib import Path
from pdf_chunker.models import Document, Page, Table


def extract_tables(document: Document) -> Document:
    """Extract tables from PDF pages using pdfplumber."""
    with pdfplumber.open(str(document.path)) as pdf:
        pages = []
        for page_idx, pdf_page in enumerate(pdf.pages):
            # Get existing page data or create new
            if page_idx < len(document.pages):
                page = document.pages[page_idx]
            else:
                page = Page(page_number=page_idx)

            tables = []
            extracted = pdf_page.extract_tables()
            if extracted:
                for table_data in extracted:
                    if not table_data or not table_data[0]:
                        continue
                    # Clean None values to empty strings
                    rows = [
                        [cell if cell is not None else "" for cell in row]
                        for row in table_data
                        if row is not None
                    ]
                    if rows:
                        # Detect header: first row is header if it has content
                        has_header = bool(rows[0] and any(cell.strip() for cell in rows[0]))
                        bbox_data = pdf_page.bbox  # (x0, y0, x1, y1)
                        tables.append(Table(
                            rows=rows,
                            page_number=page_idx,
                            bbox=tuple(bbox_data),
                            has_header_row=has_header,
                        ))

            page = page.model_copy(update={"tables": tables})
            pages.append(page)

    return document.model_copy(update={"pages": pages})
