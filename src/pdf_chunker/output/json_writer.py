import json
from pathlib import Path
from pdf_chunker.models import Chunk


def write_json(chunks: list[Chunk], source: str, output_path: Path, compact: bool = False) -> None:
    """Write chunks to a JSON file."""
    data = {
        "source": source,
        "total_chunks": len(chunks),
        "chunks": []
    }
    for chunk in chunks:
        chunk_data = {
            "chunk_id": chunk.metadata.chunk_id,
            "content": chunk.content,
            "metadata": chunk.metadata.model_dump(mode="json")
        }
        data["chunks"].append(chunk_data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        if compact:
            json.dump(data, f)
        else:
            json.dump(data, f, indent=2)
