import logging
from pathlib import Path

import pymupdf

from pdf_chunker.models import Document, Page

logger = logging.getLogger(__name__)


def detect_images(document: Document) -> Document:
    """Detect images on each page and add image metadata to pages.

    Adds a '_images' key to document metadata tracking image xref, page, and index.
    This is used by to_markdown() to insert placeholders.
    """
    all_images = []
    doc = pymupdf.open(str(document.path))
    for page_idx in range(doc.page_count):
        page = doc[page_idx]
        for img_idx, img in enumerate(page.get_images()):
            all_images.append({
                "xref": img[0],
                "page": page_idx,
                "index": img_idx,
            })
    doc.close()

    new_metadata = dict(document.metadata)
    new_metadata["_images"] = all_images

    return document.model_copy(update={"metadata": new_metadata})


def extract_images(document: Document, output_dir: Path) -> list[dict]:
    """Extract images from a PDF and save them to disk.

    Returns a list of dicts with: path, page, index, xref, filename.
    Naming convention: {stem}_p{page}_img{index}.{ext}
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = document.path.stem

    doc = pymupdf.open(str(document.path))
    extracted = []

    for page_idx in range(doc.page_count):
        page = doc[page_idx]
        for img_idx, img in enumerate(page.get_images()):
            xref = img[0]
            try:
                pix = pymupdf.Pixmap(doc, xref)
                # Convert CMYK or other colorspaces to RGB if needed
                if pix.n > 4:
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)

                ext = "png"
                filename = f"{stem}_p{page_idx}_img{img_idx}.{ext}"
                filepath = output_dir / filename
                pix.save(str(filepath))

                extracted.append({
                    "path": str(filepath),
                    "page": page_idx,
                    "index": img_idx,
                    "xref": xref,
                    "filename": filename,
                })
            except Exception as e:
                logger.warning(f"Failed to extract image xref={xref} from page {page_idx}: {e}")

    doc.close()
    return extracted
