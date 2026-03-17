from collections import Counter
from pathlib import Path

from pdf_chunker.models import Document, MarkdownDocument, Table


def table_to_markdown(table: Table) -> str:
    """Convert a Table to GFM pipe table syntax."""
    if not table.rows:
        return ""

    def escape_cell(cell: str) -> str:
        return cell.replace("|", r"\|")

    lines = []
    for i, row in enumerate(table.rows):
        escaped = [escape_cell(cell) for cell in row]
        line = "| " + " | ".join(escaped) + " |"
        lines.append(line)

        if i == 0 and table.has_header_row:
            separator = "| " + " | ".join("---" for _ in row) + " |"
            lines.append(separator)

    return "\n".join(lines)


def to_markdown(document: Document, image_refs: list[dict] | None = None) -> MarkdownDocument:
    """Convert a Document to a MarkdownDocument.

    Args:
        document: The parsed document.
        image_refs: Optional list of dicts from extract_images. When provided,
            inserts ``![Figure](images/filename)`` references. When absent but
            document metadata contains ``_images``, inserts ``[Image on page N]``
            placeholders.
    """
    # Collect all text blocks from all pages
    all_blocks = []
    for page in document.pages:
        all_blocks.extend(page.text_blocks)

    # Check if there's any content (text or tables)
    has_tables = any(page.tables for page in document.pages)

    # Build image lookup structures
    detected_images: list[dict] = document.metadata.get("_images", [])

    # Group detected images by page for placeholder insertion
    images_by_page: dict[int, list[dict]] = {}
    for img in detected_images:
        images_by_page.setdefault(img["page"], []).append(img)

    # Group image_refs by page for reference insertion
    refs_by_page: dict[int, list[dict]] = {}
    if image_refs:
        for ref in image_refs:
            refs_by_page.setdefault(ref["page"], []).append(ref)

    has_images = bool(detected_images)

    if not all_blocks and not has_tables and not has_images:
        return MarkdownDocument(
            content="",
            source_path=document.path,
            page_map=[],
        )

    # Determine body font size (most common font size)
    font_size_counts = Counter(
        round(block.font_size, 1) for block in all_blocks if block.font_size > 0
    )
    body_size = font_size_counts.most_common(1)[0][0] if font_size_counts else 12.0

    parts = []
    page_map = []

    # Track which pages we've already emitted image entries for
    pages_with_image_entries: set[int] = set()

    def _add_image_parts_for_page(page_num: int) -> None:
        """Insert image placeholders or references for a given page."""
        if page_num in pages_with_image_entries:
            return
        pages_with_image_entries.add(page_num)

        if image_refs is not None:
            # Emit actual image references
            for ref in refs_by_page.get(page_num, []):
                filename = ref.get("filename", Path(ref["path"]).name)
                img_md = f"![Figure](images/{filename})"
                current_offset = sum(len(p) + 2 for p in parts)
                page_map.append((current_offset, current_offset + len(img_md), page_num))
                parts.append(img_md)
        else:
            # Emit placeholders for detected images
            for img in images_by_page.get(page_num, []):
                placeholder = f"[Image on page {page_num}]"
                current_offset = sum(len(p) + 2 for p in parts)
                page_map.append((current_offset, current_offset + len(placeholder), page_num))
                parts.append(placeholder)

    for block in all_blocks:
        text = block.text.strip()
        if not text:
            continue

        font_size = block.font_size
        font_flags = block.font_flags
        is_bold = bool(font_flags & (1 << 4))  # bit 4
        is_italic = bool(font_flags & (1 << 1))  # bit 1 (value 2)

        # Determine heading level
        if body_size > 0 and font_size >= body_size * 1.8:
            formatted = f"# {text}"
        elif body_size > 0 and font_size >= body_size * 1.4:
            formatted = f"## {text}"
        elif body_size > 0 and font_size >= body_size * 1.2:
            formatted = f"### {text}"
        else:
            # Paragraph: apply bold/italic if applicable
            if is_bold:
                text = f"**{text}**"
            if is_italic:
                text = f"*{text}*"
            formatted = text

        # Track page_map
        current_offset = sum(len(p) + 2 for p in parts)  # +2 for "\n\n" separator
        start_offset = current_offset
        end_offset = start_offset + len(formatted)
        page_map.append((start_offset, end_offset, block.page_number))

        parts.append(formatted)

        # After each text block, emit images for this page if not yet done
        _add_image_parts_for_page(block.page_number)

    # Emit images for any pages that had no text blocks
    for page_num in list(images_by_page.keys()) + list(refs_by_page.keys()):
        _add_image_parts_for_page(page_num)

    # Append tables from each page
    for page in document.pages:
        for table in page.tables:
            md = table_to_markdown(table)
            if md:
                current_offset = sum(len(p) + 2 for p in parts)
                start_offset = current_offset
                end_offset = start_offset + len(md)
                page_map.append((start_offset, end_offset, table.page_number))
                parts.append(md)

    content = "\n\n".join(parts)

    return MarkdownDocument(
        content=content,
        source_path=document.path,
        page_map=page_map,
    )
