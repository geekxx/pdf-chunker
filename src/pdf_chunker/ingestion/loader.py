from pathlib import Path

import pymupdf

from pdf_chunker.models import Document


def load_document(path: str | Path) -> Document:
    """Load a PDF document and return a Document with metadata."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"No such file: {path}")

    try:
        doc = pymupdf.open(str(path))
    except Exception as e:
        raise ValueError(f"{path} is not a valid PDF") from e

    if doc.is_pdf is False:
        doc.close()
        raise ValueError(f"{path} is not a valid PDF")

    # Verify it's actually a valid PDF by checking page count
    try:
        page_count = doc.page_count
    except Exception as e:
        doc.close()
        raise ValueError(f"{path} is not a valid PDF") from e

    raw_meta = doc.metadata or {}
    metadata = {
        "title": raw_meta.get("title", ""),
        "author": raw_meta.get("author", ""),
    }

    doc.close()

    return Document(
        path=path,
        page_count=page_count,
        metadata=metadata,
        pages=[],
    )
