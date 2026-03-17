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
    strip_watermarks: bool = True
    skip_patterns: list[str] = [
        r"(?i)^table of contents$",
        r"(?i)^contents$",
        r"(?i)get free",
        r"(?i)subscribe",
        r"(?i)newsletter",
        r"(?i)insider",
        r"(?i)recommended (reading|watching|viewing)",
        r"(?i)other books by",
        r"(?i)also by",
        r"(?i)^title page$",
        r"(?i)^cover$",
    ]
    quality_report: bool = True

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

    # Handle top-level filtering config that maps to chunking fields
    filtering_data = data.get("filtering", {})
    for key in ("strip_watermarks", "skip_patterns", "quality_report"):
        if key in filtering_data and key not in filtered_chunking:
            filtered_chunking[key] = filtering_data[key]

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

[filtering]
# Remove DRM watermarks matching "Name (Order #NNNNNNN)" pattern
strip_watermarks = true

# Print a quality report after chunking
quality_report = true

# Skip chunks whose headings match these patterns (regex, case-insensitive)
# skip_patterns = [
#     "(?i)^table of contents$",
#     "(?i)^contents$",
#     "(?i)get free",
#     "(?i)subscribe",
#     "(?i)newsletter",
#     "(?i)insider",
#     "(?i)recommended (reading|watching|viewing)",
#     "(?i)other books by",
#     "(?i)also by",
#     "(?i)^title page$",
#     "(?i)^cover$",
# ]

[output]
# Output format: "json" or "markdown"
format = "json"

# Produce minified JSON (no pretty-printing)
compact = false
'''
