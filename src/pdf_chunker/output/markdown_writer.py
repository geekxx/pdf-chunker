import json
import yaml
from pathlib import Path
from pdf_chunker.models import Chunk


def write_markdown(chunks: list[Chunk], source: str, full_markdown: str, output_dir: Path) -> None:
    """Write chunks as individual Markdown files with YAML frontmatter."""
    # Create document directory named after the source PDF stem
    stem = Path(source).stem
    doc_dir = output_dir / stem
    doc_dir.mkdir(parents=True, exist_ok=True)

    # Write full pre-chunking markdown
    (doc_dir / "full.md").write_text(full_markdown)

    # Write individual chunk files
    manifest_entries = []
    for i, chunk in enumerate(chunks):
        filename = f"chunk_{i:04d}.md"
        filepath = doc_dir / filename

        # Build YAML frontmatter
        meta = chunk.metadata.model_dump(mode="json")
        frontmatter = yaml.dump(meta, default_flow_style=False, sort_keys=False)

        content = f"---\n{frontmatter}---\n{chunk.content}"
        filepath.write_text(content)

        manifest_entries.append({
            "file": filename,
            "chunk_id": chunk.metadata.chunk_id,
            "chunk_index": chunk.metadata.chunk_index,
            "token_count": chunk.metadata.token_count,
            "page_numbers": chunk.metadata.page_numbers,
        })

    # Write manifest
    manifest_path = doc_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_entries, indent=2))
