from collections import Counter

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


def to_markdown(document: Document) -> MarkdownDocument:
    """Convert a Document to a MarkdownDocument."""
    # Collect all text blocks from all pages
    all_blocks = []
    for page in document.pages:
        all_blocks.extend(page.text_blocks)

    # Check if there's any content (text or tables)
    has_tables = any(page.tables for page in document.pages)

    if not all_blocks and not has_tables:
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
