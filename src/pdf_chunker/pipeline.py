from pathlib import Path
from dataclasses import dataclass, field
import logging

from pdf_chunker.ingestion.loader import load_document
from pdf_chunker.ingestion.extractor import extract_text
from pdf_chunker.conversion.markdown_writer import to_markdown
from pdf_chunker.conversion.cleaner import clean_markdown_document
from pdf_chunker.config import ChunkingConfig
from pdf_chunker.models import Chunk

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    output_path: Path | None = None
    total_chunks: int = 0
    success: bool = True
    error: str | None = None


@dataclass
class BatchResult:
    results: list[ProcessingResult] = field(default_factory=list)
    total_files: int = 0
    successful: int = 0
    failed: int = 0
    total_chunks: int = 0


def process_pdf(input_path: Path, output_dir: Path, config: ChunkingConfig | None = None, compact: bool = False) -> ProcessingResult:
    """Process a single PDF file through the full pipeline. Returns ProcessingResult."""
    config = config or ChunkingConfig()
    try:
        doc = load_document(input_path)
        doc = extract_text(doc)
        md_doc = to_markdown(doc)
        md_doc = clean_markdown_document(md_doc)

        if config.strategy == "sliding":
            from pdf_chunker.chunking.window_chunker import SlidingWindowChunker
            chunker = SlidingWindowChunker()
        else:
            from pdf_chunker.chunking.structural_chunker import StructuralChunker
            chunker = StructuralChunker()
        chunks = chunker.chunk(md_doc, config)

        from pdf_chunker.output.json_writer import write_json
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{input_path.stem}_chunks.json"
        write_json(chunks, str(input_path), output_path, compact=compact)

        logger.info(f"Processed {input_path}: {len(chunks)} chunks")
        return ProcessingResult(output_path=output_path, total_chunks=len(chunks), success=True)
    except Exception as e:
        logger.error(f"Failed to process {input_path}: {e}")
        return ProcessingResult(success=False, error=str(e))


def process_batch(paths: list[Path], output_dir: Path, config: ChunkingConfig | None = None, compact: bool = False) -> BatchResult:
    """Process multiple PDF files. Returns BatchResult with per-file results."""
    batch = BatchResult(total_files=len(paths))
    for path in paths:
        result = process_pdf(path, output_dir, config, compact)
        batch.results.append(result)
        if result.success:
            batch.successful += 1
            batch.total_chunks += result.total_chunks
        else:
            batch.failed += 1
    return batch
