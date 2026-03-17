import logging
import sys
from pathlib import Path

import click

from pdf_chunker.config import ChunkingConfig
from pdf_chunker.pipeline import process_pdf, process_batch


@click.command()
@click.argument("input_path", type=click.Path(exists=False))
@click.option("--output", "-o", type=click.Path(), default="./output", help="Output directory")
@click.option("--recursive", "-r", is_flag=True, help="Recurse into subdirectories")
@click.option("--compact", is_flag=True, help="Produce minified JSON output")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--max-tokens", type=int, default=1500, help="Maximum tokens per chunk")
@click.option("--strategy", type=click.Choice(["structural", "sliding"]), default="structural")
@click.option("--format", "output_format", type=click.Choice(["json", "markdown"]), default="json", help="Output format")
@click.pass_context
def main(ctx, input_path, output, recursive, compact, verbose, max_tokens, strategy, output_format):
    """Process PDF files into AI-optimized Markdown chunks."""
    # Configure logging
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s", stream=sys.stderr)

    input_path = Path(input_path)
    output_dir = Path(output)

    # Validate input exists
    if not input_path.exists():
        click.echo(f"Error: Path '{input_path}' does not exist.", err=True)
        ctx.exit(2)
        return

    config = ChunkingConfig(max_tokens=max_tokens, strategy=strategy)

    if input_path.is_file():
        # Single file mode
        result = process_pdf(input_path, output_dir, config, compact=compact, output_format=output_format)
        if result.success:
            click.echo(f"Processed 1 file, {result.total_chunks} chunks generated, 0 errors")
        else:
            click.echo(f"Error processing {input_path}: {result.error}", err=True)
            raise click.exceptions.Exit(1)

    elif input_path.is_dir():
        # Directory mode
        if recursive:
            pdf_files = sorted(input_path.rglob("*.pdf"))
        else:
            pdf_files = sorted(input_path.glob("*.pdf"))

        if not pdf_files:
            click.echo(f"No PDF files found in {input_path}")
            ctx.exit(0)
            return

        batch = process_batch(pdf_files, output_dir, config, compact=compact, output_format=output_format)

        click.echo(f"Processed {batch.total_files} files, {batch.total_chunks} chunks generated, {batch.failed} errors")

        if batch.failed > 0 and batch.successful > 0:
            ctx.exit(1)  # Partial failure
        elif batch.failed > 0 and batch.successful == 0:
            ctx.exit(2)  # Total failure
        else:
            ctx.exit(0)
    else:
        click.echo(f"Error: '{input_path}' is not a file or directory.", err=True)
        ctx.exit(2)
