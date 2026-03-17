import re
import unicodedata

from pdf_chunker.models import MarkdownDocument


def _fix_spaced_characters(text: str) -> str:
    """Fix text where PDF extraction inserted spaces within words.

    Detects patterns like "T he  B arbarian" and collapses to "The Barbarian".
    Only applies to lines with 2+ occurrences of the pattern to avoid
    false positives on legitimate text like "I am".
    """
    def fix_line(line: str) -> str:
        # Count single-uppercase-letter + space + lowercase pattern
        matches = re.findall(r"(?<![A-Za-z])([A-Z]) ([a-z])", line)
        if len(matches) >= 2:
            # Collapse "X yz" → "Xyz" at word starts
            line = re.sub(r"(?<![A-Za-z])([A-Z]) ([a-z])", r"\1\2", line)
            # Collapse runs of 2+ spaces to single space
            line = re.sub(r" {2,}", " ", line)
        return line

    return "\n".join(fix_line(l) for l in text.split("\n"))


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

    # 5. Fix spaced-out characters from PDF extraction artifacts.
    # Decorative/display fonts often produce per-glyph spans that result
    # in text like "T he  B arbarian" instead of "The Barbarian".
    # Only apply when a line has 2+ occurrences (high confidence).
    text = _fix_spaced_characters(text)

    # 6. Rejoin hyphenated line breaks
    text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)

    # 7. Remove bare page number lines (lines that are just a number, possibly with whitespace)
    text = re.sub(r"^\s*\d{1,4}\s*$", "", text, flags=re.MULTILINE)

    # 8. Remove markdown headings that are just page numbers (e.g., "### 227")
    text = re.sub(r"^#{1,6}\s+\d{1,4}\s*$", "", text, flags=re.MULTILINE)

    # 9. Collapse excessive whitespace
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
