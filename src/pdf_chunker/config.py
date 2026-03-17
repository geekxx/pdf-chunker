import logging
import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator


class ChunkingConfig(BaseModel):
    """Configuration for the chunking process."""
    strategy: str = "structural"  # "structural" or "sliding"
    max_tokens: int = 1500
    min_tokens: int = 100
    overlap: int = 200
    split_heading_level: int = 2
    token_encoding: str = "cl100k_base"

    @field_validator("max_tokens")
    @classmethod
    def max_tokens_positive(cls, v):
        if v <= 0:
            raise ValueError("max_tokens must be positive")
        return v


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    chunking: ChunkingConfig = ChunkingConfig()
    output_format: str = "json"
    compact: bool = False
    verbose: bool = False


def load_config(path: Path) -> AppConfig:
    """Load config from a TOML file. Unknown keys are ignored."""
    with open(path, "rb") as f:
        data = tomllib.load(f)

    # Handle nested chunking config
    chunking_data = data.get("chunking", {})
    known_chunking_fields = set(ChunkingConfig.model_fields.keys())
    filtered_chunking = {k: v for k, v in chunking_data.items() if k in known_chunking_fields}
    unknown_keys = set(chunking_data.keys()) - known_chunking_fields
    if unknown_keys:
        logging.getLogger(__name__).warning(f"Unknown config keys ignored: {unknown_keys}")

    return AppConfig(
        chunking=ChunkingConfig(**filtered_chunking),
        output_format=data.get("output", {}).get("format", "json"),
        compact=data.get("output", {}).get("compact", False),
        verbose=data.get("verbose", False),
    )


def generate_default_config() -> str:
    """Generate a default TOML config file content with comments."""
    return '''# pdf-chunker configuration

[chunking]
# Chunking strategy: "structural" (split at headings) or "sliding" (fixed window)
strategy = "structural"

# Maximum tokens per chunk
max_tokens = 1500

# Minimum tokens per chunk (smaller chunks get merged)
min_tokens = 100

# Token overlap between consecutive chunks (sliding strategy)
overlap = 200

# Heading level to split at (1=h1, 2=h2, etc.)
split_heading_level = 2

# Tokenizer encoding
token_encoding = "cl100k_base"

[output]
# Output format: "json" or "markdown"
format = "json"

# Produce minified JSON (no pretty-printing)
compact = false
'''
