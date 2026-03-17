import hashlib
import logging
from pdf_chunker.chunking.base import Chunker
from pdf_chunker.models import MarkdownDocument, Chunk, ChunkMetadata
from pdf_chunker.config import ChunkingConfig

logger = logging.getLogger(__name__)


class SlidingWindowChunker(Chunker):
    def chunk(self, document: MarkdownDocument, config: ChunkingConfig) -> list[Chunk]:
        content = document.content.strip()
        if not content:
            return []

        try:
            import tiktoken
            encoding = tiktoken.get_encoding(config.token_encoding)
            tokens = encoding.encode(content)
            use_tiktoken = True
        except Exception:
            use_tiktoken = False
            # Approximate: 1 token ≈ 4 chars
            tokens = [content[i:i+4] for i in range(0, len(content), 4)]

        chunk_size = config.max_tokens
        overlap = config.overlap
        step = max(1, chunk_size - overlap)

        raw_chunks = []
        i = 0
        while i < len(tokens):
            end = min(i + chunk_size, len(tokens))
            chunk_tokens = tokens[i:end]

            if use_tiktoken:
                chunk_text = encoding.decode(chunk_tokens)
            else:
                chunk_text = "".join(chunk_tokens)

            # Prefer paragraph boundaries: if not at the end, try to break at \n\n
            actual_step = step
            if end < len(tokens):
                last_para = chunk_text.rfind("\n\n")
                if last_para > len(chunk_text) * 0.5:
                    chunk_text = chunk_text[:last_para]
                    if use_tiktoken:
                        actual_tokens = len(encoding.encode(chunk_text))
                    else:
                        actual_tokens = len(chunk_text) // 4
                    actual_step = max(1, actual_tokens - overlap)

            raw_chunks.append((i, chunk_text.strip()))
            i += actual_step

        # Build Chunk objects with metadata
        source_file = str(document.source_path)
        chunks = []
        for idx, (start_token_idx, text) in enumerate(raw_chunks):
            if not text:
                continue

            if use_tiktoken:
                token_count = len(encoding.encode(text))
            else:
                token_count = max(1, len(text) // 4)

            chunk_id = hashlib.sha256(f"{source_file}:{idx}".encode()).hexdigest()[:16]

            # Derive page numbers from page_map
            chunk_start = document.content.find(text[:50])
            chunk_end = chunk_start + len(text) if chunk_start >= 0 else len(document.content)
            page_numbers = sorted(set(
                pm[2] for pm in document.page_map
                if pm[0] < chunk_end and pm[1] > max(0, chunk_start)
            )) if document.page_map else []

            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                source_file=source_file,
                page_numbers=page_numbers,
                chunk_index=idx,
                total_chunks=len(raw_chunks),
                token_count=token_count,
            )
            chunks.append(Chunk(
                content=text,
                metadata=metadata,
                token_count=token_count,
                heading_hierarchy=[],
            ))

        # Update total_chunks in case we filtered empties
        for c in chunks:
            c.metadata.total_chunks = len(chunks)

        return chunks
