# pdf-chunker

Convert PDFs to AI-optimized Markdown chunks with rich metadata. Designed for preparing documents for ingestion into RAG pipelines, knowledge bases, and LLM context windows.

## Features

- **PDF text extraction** with layout preservation and font metadata (PyMuPDF)
- **Table extraction** with GFM Markdown table output (pdfplumber)
- **Image detection** with placeholder insertion or extraction to disk
- **Structural chunking** — split at heading boundaries with heading hierarchy context
- **Sliding-window chunking** — configurable token size with overlap for unstructured documents
- **Content cleaning** — smart quote normalization, ligature expansion, hyphenated line rejoining
- **Rich metadata** — source file, page numbers, token counts, deterministic chunk IDs
- **Multiple output formats** — JSON (default) or individual Markdown files with YAML frontmatter
- **TOML config files** — codify your settings for repeatable processing

## Installation

Requires Python 3.12+.

```bash
pip install pdf-chunker
```

Or for development:

```bash
git clone <repo-url>
cd pdf-chunker
uv sync
```

## Quick Start

```bash
# Process a single PDF
pdf-chunker input.pdf

# Process a directory of PDFs
pdf-chunker ./documents/ --recursive

# Output as Markdown files instead of JSON
pdf-chunker input.pdf --format markdown

# Use sliding-window chunking with custom token limit
pdf-chunker input.pdf --strategy sliding --max-tokens 1000

# Verbose logging
pdf-chunker input.pdf --verbose
```

## CLI Reference

```text
pdf-chunker [OPTIONS] INPUT_PATH
```

| Option | Description | Default |
| ------ | ----------- | ------- |
| `--output`, `-o` | Output directory | `./output` |
| `--format` | Output format: `json` or `markdown` | `json` |
| `--strategy` | Chunking strategy: `structural` or `sliding` | `structural` |
| `--max-tokens` | Maximum tokens per chunk | `1500` |
| `--recursive`, `-r` | Recurse into subdirectories | off |
| `--compact` | Minified JSON output | off |
| `--verbose`, `-v` | Enable debug logging | off |
| `--config` | Path to TOML config file | none |

### Generate a config file

```bash
pdf-chunker init-config --output pdf-chunker.toml
```

## Output Formats

### JSON (default)

One file per input PDF: `{stem}_chunks.json`

```json
{
  "source": "report.pdf",
  "total_chunks": 12,
  "chunks": [
    {
      "chunk_id": "a1b2c3d4e5f67890",
      "content": "## Introduction\n\nThis report covers...",
      "metadata": {
        "source_file": "report.pdf",
        "page_numbers": [1, 2],
        "chunk_index": 0,
        "total_chunks": 12,
        "token_count": 342,
        "heading_hierarchy": ["Introduction"]
      }
    }
  ]
}
```

### Markdown

One directory per input PDF containing:

- `chunk_0000.md`, `chunk_0001.md`, ... — individual chunks with YAML frontmatter
- `full.md` — the complete pre-chunking Markdown
- `manifest.json` — index of all chunk files with metadata

## Python API

```python
from pdf_chunker.ingestion.loader import load_document
from pdf_chunker.ingestion.extractor import extract_text
from pdf_chunker.conversion.markdown_writer import to_markdown
from pdf_chunker.conversion.cleaner import clean_markdown_document
from pdf_chunker.chunking.structural_chunker import StructuralChunker
from pdf_chunker.config import ChunkingConfig

# Full pipeline
doc = load_document("input.pdf")
doc = extract_text(doc)
md_doc = to_markdown(doc)
md_doc = clean_markdown_document(md_doc)

chunker = StructuralChunker()
chunks = chunker.chunk(md_doc, ChunkingConfig(max_tokens=1000))

for chunk in chunks:
    print(f"[{chunk.metadata.chunk_id}] {chunk.token_count} tokens")
    print(chunk.content[:100])
```

## Chunking Strategies

### Structural (default)

Splits at heading boundaries (`##` by default). Each chunk includes its heading hierarchy for context. Chunks exceeding `max_tokens` are further split at paragraph boundaries. Chunks below `min_tokens` are merged with adjacent chunks.

### Sliding Window

Fixed-size token windows with configurable overlap. Prefers paragraph boundaries over mid-sentence splits. Best for documents without clear heading structure.

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=pdf_chunker
```

## License

MIT
