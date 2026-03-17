"""Post-processing steps for chunks: watermark removal, filtering, quality reporting."""

import re
import logging
from dataclasses import dataclass, field

from pdf_chunker.models import Chunk
from pdf_chunker.config import ChunkingConfig

logger = logging.getLogger(__name__)

# DriveThruRPG-style watermark: "Name Name (Order #12345678)"
_WATERMARK_RE = re.compile(r"^\s*.+?\(Order\s*#\d+\)\s*$", re.MULTILINE)


@dataclass
class PostProcessingReport:
    """Tracks what happened during post-processing for quality reporting."""
    watermark_lines_stripped: int = 0
    orphan_lines_stripped: int = 0
    chunks_filtered: list[tuple[int, str, str]] = field(default_factory=list)  # (index, heading, reason)


def strip_watermarks(content: str, report: PostProcessingReport | None = None) -> str:
    """Remove DRM watermark lines and orphaned author name lines that follow them."""
    lines = content.split("\n")
    cleaned: list[str] = []
    i = 0
    while i < len(lines):
        if _WATERMARK_RE.match(lines[i]):
            if report is not None:
                report.watermark_lines_stripped += 1
            # Check if next line is an orphaned author name:
            # Looks like a person's name: 2-4 capitalized words, no punctuation
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if (
                    next_line
                    and re.match(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}$", next_line)
                ):
                    # Likely an orphaned author name (e.g., "Matt Davids")
                    if report is not None:
                        report.orphan_lines_stripped += 1
                    i += 2
                    continue
            i += 1
            continue
        cleaned.append(lines[i])
        i += 1

    result = "\n".join(cleaned)
    # Collapse any triple+ newlines left behind
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result


def filter_chunks(
    chunks: list[Chunk],
    config: ChunkingConfig,
    report: PostProcessingReport | None = None,
) -> list[Chunk]:
    """Filter out low-value chunks based on skip_patterns and heuristics."""
    if not config.skip_patterns:
        return chunks

    compiled_patterns = [re.compile(p) for p in config.skip_patterns]
    kept: list[Chunk] = []

    for chunk in chunks:
        heading_text = " > ".join(chunk.heading_hierarchy) if chunk.heading_hierarchy else ""
        reason = _should_skip(chunk, heading_text, compiled_patterns)
        if reason:
            if report is not None:
                report.chunks_filtered.append((chunk.metadata.chunk_index, heading_text or "(no heading)", reason))
            logger.debug(f"Filtered chunk {chunk.metadata.chunk_index}: {reason}")
        else:
            kept.append(chunk)

    # Re-index kept chunks
    total = len(kept)
    for i, chunk in enumerate(kept):
        chunk.metadata.chunk_index = i
        chunk.metadata.total_chunks = total

    return kept


def _should_skip(chunk: Chunk, heading_text: str, patterns: list[re.Pattern]) -> str | None:
    """Return a reason string if the chunk should be skipped, else None."""
    # Check heading hierarchy against skip patterns
    for pattern in patterns:
        for heading in chunk.heading_hierarchy:
            if pattern.search(heading):
                return f"heading matches pattern: {pattern.pattern}"
        # Also check combined heading text
        if heading_text and pattern.search(heading_text):
            return f"heading hierarchy matches pattern: {pattern.pattern}"

    # Title/cover page heuristic: very low token count with only heading content
    if chunk.token_count < 20:
        content_lines = [l.strip() for l in chunk.content.split("\n") if l.strip()]
        non_heading_lines = [l for l in content_lines if not l.startswith("#")]
        if len(non_heading_lines) <= 1:
            return "likely title/cover page (very low tokens, heading-only)"

    return None


@dataclass
class QualityBucket:
    label: str
    min_tokens: int
    max_tokens: int  # exclusive
    count: int = 0


def print_quality_report(
    chunks: list[Chunk],
    report: PostProcessingReport,
    source_name: str = "",
) -> str:
    """Generate a quality report string and return it."""
    buckets = [
        QualityBucket("junk (<10)", 0, 10),
        QualityBucket("tiny (10-50)", 10, 50),
        QualityBucket("small (50-100)", 50, 100),
        QualityBucket("medium (100-300)", 100, 300),
        QualityBucket("good (300-1000)", 300, 1000),
        QualityBucket("large (1000+)", 1000, 999999),
    ]

    total_tokens = 0
    for chunk in chunks:
        total_tokens += chunk.token_count
        for bucket in buckets:
            if bucket.min_tokens <= chunk.token_count < bucket.max_tokens:
                bucket.count += 1
                break

    lines: list[str] = []
    if source_name:
        lines.append(f"--- Quality Report: {source_name} ---")
    else:
        lines.append("--- Quality Report ---")

    lines.append(f"Total chunks: {len(chunks)}")
    lines.append(f"Total tokens: {total_tokens}")
    if chunks:
        token_counts = [c.token_count for c in chunks]
        lines.append(f"Token range: {min(token_counts)}-{max(token_counts)} (avg {total_tokens // len(chunks)})")
    lines.append("")
    lines.append("Token distribution:")
    for bucket in buckets:
        bar = "#" * bucket.count
        lines.append(f"  {bucket.label:20s} {bucket.count:3d}  {bar}")

    if report.watermark_lines_stripped > 0 or report.orphan_lines_stripped > 0:
        lines.append("")
        lines.append(f"Watermark lines stripped: {report.watermark_lines_stripped}")
        if report.orphan_lines_stripped > 0:
            lines.append(f"Orphaned author lines stripped: {report.orphan_lines_stripped}")

    if report.chunks_filtered:
        lines.append("")
        lines.append(f"Chunks filtered out: {len(report.chunks_filtered)}")
        for idx, heading, reason in report.chunks_filtered:
            lines.append(f"  [{idx}] \"{heading}\" - {reason}")

    lines.append("")
    return "\n".join(lines)
