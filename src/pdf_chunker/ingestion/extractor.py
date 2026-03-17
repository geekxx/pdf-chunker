from collections import Counter

import pymupdf

from pdf_chunker.models import Document, Page, TextBlock


def extract_text(document: Document) -> Document:
    """Extract text blocks from a PDF and populate the document's pages."""
    doc = pymupdf.open(str(document.path))

    pages = []
    for page_index in range(doc.page_count):
        page = doc[page_index]
        raw = page.get_text("dict", flags=11)
        blocks_data = raw.get("blocks", [])

        text_blocks = []
        for block in blocks_data:
            if "lines" not in block:
                continue

            # Collect spans line-by-line: concatenate spans within a line
            # directly (they are contiguous text runs), then join lines
            # with spaces. This avoids inserting spurious spaces within
            # words when the PDF uses per-character or per-glyph spans
            # (common in decorative/display fonts).
            all_spans = []
            line_texts = []
            for line in block["lines"]:
                line_text = "".join(s["text"] for s in line["spans"])
                line_text = line_text.strip()
                if line_text:
                    line_texts.append(line_text)
                all_spans.extend(line["spans"])

            if not all_spans:
                continue

            text = " ".join(line_texts).strip()
            if not text:
                continue

            # Compute dominant font size and flags
            font_size = sum(s["size"] for s in all_spans) / len(all_spans)
            # Pick most common flags value
            flags_counter = Counter(s["flags"] for s in all_spans)
            font_flags = flags_counter.most_common(1)[0][0]

            text_blocks.append(TextBlock(
                text=text,
                bbox=block["bbox"],
                block_type="paragraph",
                page_number=page_index,
                font_size=font_size,
                font_flags=font_flags,
            ))

        pages.append(Page(
            page_number=page_index,
            text_blocks=text_blocks,
        ))

    doc.close()

    return document.model_copy(update={"pages": pages})
