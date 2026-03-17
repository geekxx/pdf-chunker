import hashlib
import re

from pdf_chunker.chunking.base import Chunker
from pdf_chunker.config import ChunkingConfig
from pdf_chunker.models import Chunk, ChunkMetadata, MarkdownDocument


def _get_heading_level(line: str) -> int | None:
    """Return heading level (1-6) if line is a markdown heading, else None."""
    match = re.match(r"^(#{1,6}) ", line)
    if match:
        return len(match.group(1))
    return None


def _count_tokens(text: str, encoding_name: str) -> int:
    try:
        import tiktoken
        encoding = tiktoken.get_encoding(encoding_name)
        return len(encoding.encode(text))
    except Exception:
        return len(text) // 4


def _derive_page_numbers(
    page_map: list[tuple[int, int, int]],
    chunk_start: int,
    chunk_end: int,
) -> list[int]:
    return sorted(set(
        pm[2] for pm in page_map
        if pm[0] < chunk_end and pm[1] > chunk_start
    ))


class StructuralChunker(Chunker):
    def chunk(self, document: MarkdownDocument, config: ChunkingConfig) -> list[Chunk]:
        content = document.content

        if not content or not content.strip():
            return []

        split_level = config.split_heading_level
        lines = content.splitlines(keepends=True)

        # Split content into sections at headings <= split_heading_level
        sections: list[tuple[list[str], list[str]]] = []  # (heading_hierarchy, lines)
        current_lines: list[str] = []
        current_hierarchy: list[str] = []
        # Track headings above split level to maintain hierarchy
        parent_headings: dict[int, str] = {}

        def flush_section():
            if current_lines:
                section_content = "".join(current_lines).strip()
                if section_content:
                    sections.append((list(current_hierarchy), list(current_lines)))

        for line in lines:
            stripped = line.rstrip("\n")
            level = _get_heading_level(stripped)

            if level is not None and level <= split_level:
                # This is a split point — flush current section
                flush_section()
                current_lines = [line]

                # Update parent heading tracking
                # Remove any tracked headings at this level or deeper
                for k in list(parent_headings.keys()):
                    if k >= level:
                        del parent_headings[k]
                heading_text = stripped.lstrip("#").strip()
                parent_headings[level] = heading_text

                # Build hierarchy: all headings from level 1 up to current level
                current_hierarchy = [
                    parent_headings[lvl]
                    for lvl in sorted(parent_headings.keys())
                ]
            else:
                current_lines.append(line)

        flush_section()

        # If no sections were created (no headings), treat entire content as one section
        if not sections:
            sections = [([], lines)]

        # Build raw chunks from sections, handling max/min token constraints
        source_file = str(document.source_path)

        raw_chunks: list[tuple[list[str], str]] = []  # (hierarchy, content)

        for hierarchy, sec_lines in sections:
            sec_content = "".join(sec_lines).strip()
            if not sec_content:
                continue

            token_count = _count_tokens(sec_content, config.token_encoding)

            if token_count <= config.max_tokens:
                raw_chunks.append((hierarchy, sec_content))
            else:
                # Split at paragraph boundaries
                paragraphs = re.split(r"\n\n+", sec_content)
                current_para_content = ""
                for para in paragraphs:
                    candidate = (current_para_content + "\n\n" + para).strip() if current_para_content else para
                    if _count_tokens(candidate, config.token_encoding) > config.max_tokens:
                        if current_para_content:
                            raw_chunks.append((hierarchy, current_para_content.strip()))
                        current_para_content = para
                    else:
                        current_para_content = candidate
                if current_para_content.strip():
                    raw_chunks.append((hierarchy, current_para_content.strip()))

        merged_chunks = raw_chunks

        if not merged_chunks:
            return []

        # Compute character offsets for page number derivation
        # We need to find where each chunk's content appears in the original document
        chunks: list[Chunk] = []
        search_start = 0

        for chunk_index, (hierarchy, chunk_content) in enumerate(merged_chunks):
            # Find position in original content
            pos = content.find(chunk_content, search_start)
            if pos == -1:
                # Fallback: search from beginning
                pos = content.find(chunk_content)
            chunk_start = pos if pos != -1 else 0
            chunk_end = chunk_start + len(chunk_content)
            if pos != -1:
                search_start = chunk_start + 1

            page_numbers = _derive_page_numbers(document.page_map, chunk_start, chunk_end)
            token_count = _count_tokens(chunk_content, config.token_encoding)
            chunk_id = hashlib.sha256(f"{source_file}:{chunk_index}".encode()).hexdigest()[:16]

            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                source_file=source_file,
                page_numbers=page_numbers,
                chunk_index=chunk_index,
                total_chunks=0,  # filled in second pass
                token_count=token_count,
                heading_hierarchy=hierarchy,
            )

            chunks.append(Chunk(
                content=chunk_content,
                metadata=metadata,
                token_count=token_count,
                heading_hierarchy=hierarchy,
            ))

        # Second pass: set total_chunks
        total = len(chunks)
        for chunk in chunks:
            chunk.metadata.total_chunks = total

        return chunks
