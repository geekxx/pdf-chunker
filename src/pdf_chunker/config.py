from pydantic import BaseModel


class ChunkingConfig(BaseModel):
    """Configuration for the chunking process."""
    strategy: str = "structural"  # "structural" or "sliding"
    max_tokens: int = 1500
    min_tokens: int = 100
    overlap: int = 200
    split_heading_level: int = 2
    token_encoding: str = "cl100k_base"
