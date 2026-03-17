import logging
import sys
from pathlib import Path

import click

from pdf_chunker.config import ChunkingConfig, load_config, generate_default_config
from pdf_chunker.pipeline import process_pdf, process_batch, BatchResult


@click.command()
@click.argument("input_path", type=click.Path(exists=False))
@click.option("--output", "-o", type=click.Path(), default="./output", help="Output directory")
@click.option("--recursive", "-r", is_flag=True, help="Recurse into subdirectories")
@click.option("--compact", is_flag=True, help="Produce minified JSON output")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--max-tokens", type=int, default=1500, help="Maximum tokens per chunk")
@click.option("--strategy", type=click.Choice(["structural", "sliding"]), default="structural")
@click.option("--format", "output_format", type=click.Choice(["json", "markdown"]), default="json", help="Output format")
@click.option("--config", "config_path", type=click.Path(exists=True), default=None, help="Path to TOML config file")
@click.option("--in-place", is_flag=True, help="Output alongside the source PDF(s)")
@click.pass_context
def main(ctx, input_path, output, recursive, compact, verbose, max_tokens, strategy, output_format, config_path, in_place):
    """Process PDF files into AI-optimized Markdown chunks."""
    # If config_path provided, load it and use as base (CLI args override)
    if config_path:
        try:
            app_config = load_config(Path(config_path))
            # CLI args override config only if they differ from Click defaults
            if max_tokens == 1500:
                max_tokens = app_config.chunking.max_tokens
            if strategy == "structural":
                strategy = app_config.chunking.strategy
            if output_format == "json":
                output_format = app_config.output_format
            if not compact:
                compact = app_config.compact
            if not verbose:
                verbose = app_config.verbose
        except Exception as e:
            click.echo(f"Error loading config: {e}", err=True)
            ctx.exit(2)
            return

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
        file_output_dir = input_path.parent if in_place else output_dir
        result = process_pdf(input_path, file_output_dir, config, compact=compact, output_format=output_format)
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

        if in_place:
            # Process each file with output alongside its source
            batch = BatchResult(total_files=len(pdf_files))
            for pdf_file in pdf_files:
                result = process_pdf(pdf_file, pdf_file.parent, config, compact=compact, output_format=output_format)
                batch.results.append(result)
                if result.success:
                    batch.successful += 1
                    batch.total_chunks += result.total_chunks
                else:
                    batch.failed += 1
        else:
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


@click.group(invoke_without_command=True)
@click.pass_context
def cli_group(ctx):
    """pdf-chunker: Process PDF files into AI-optimized chunks."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli_group.command("init-config")
@click.option("--output", "-o", type=click.Path(), default="./pdf-chunker.toml", help="Output path for config file")
def init_config(output):
    """Generate a default configuration file."""
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_default_config())
    click.echo(f"Default config written to {path}")
