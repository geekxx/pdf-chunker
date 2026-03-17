import re
import unicodedata

from pdf_chunker.models import MarkdownDocument


def clean(text: str) -> str:
    """Clean and normalize a text string."""
    if not text:
        return text

    # 1. Expand ligatures
    text = text.replace("\ufb03", "ffi")
    text = text.replace("\ufb04", "ffl")
    text = text.replace("\ufb01", "fi")
    text = text.replace("\ufb02", "fl")
    text = text.replace("\ufb00", "ff")

    # 2. Normalize Unicode
    text = unicodedata.normalize("NFKC", text)

    # 3. Smart quotes → straight
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")

    # 4. Normalize dashes
    text = text.replace("\u2014", "--")
    text = text.replace("\u2013", "--")

    # 5. Rejoin hyphenated line breaks
    text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)

    # 6. Collapse excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text


def clean_markdown_document(md_doc: MarkdownDocument) -> MarkdownDocument:
    """Clean the content of a MarkdownDocument."""
    cleaned_content = clean(md_doc.content)
    return MarkdownDocument(
        content=cleaned_content,
        source_path=md_doc.source_path,
        page_map=md_doc.page_map,
    )
