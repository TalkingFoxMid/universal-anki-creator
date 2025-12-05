"""Main CLI interface for Anki deck generator."""

import os
import sys
import time
import click
from pathlib import Path
from dotenv import load_dotenv

from .parser import InputParser
from .prompt import PromptBuilder
from .api import ClaudeAPIClient
from .validator import ResponseValidator
from .formatter import AnkiFormatter


# Load environment variables
load_dotenv()


def get_template_path() -> Path:
    """Get path to INSTRUCTION.md template."""
    # Try to find template relative to this file
    src_dir = Path(__file__).parent
    project_root = src_dir.parent
    template_path = project_root / "templates" / "INSTRUCTION.md"

    if not template_path.exists():
        raise FileNotFoundError(
            f"INSTRUCTION.md template not found at: {template_path}"
        )

    return template_path


@click.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option(
    '--prompt', '-p',
    default='./PROMPT.md',
    help='Path to PROMPT.md',
    type=click.Path(exists=True)
)
@click.option(
    '--output', '-o',
    default='./OUTPUT.txt',
    help='Path to OUTPUT.txt'
)
@click.option(
    '--deck', '-d',
    default='Default',
    help='Deck name'
)
@click.option(
    '--reverse', '-r',
    is_flag=True,
    help='Swap front/back'
)
@click.option(
    '--cards', '-c',
    default=1,
    type=int,
    help='Cards per input element'
)
@click.option(
    '--batch-size', '-b',
    default=1,
    type=int,
    help='Elements per API request'
)
@click.option(
    '--model', '-m',
    default='claude-sonnet-4-20250514',
    help='Claude model'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Show requests without executing'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Verbose output'
)
def cli(
    input_file: str,
    prompt: str,
    output: str,
    deck: str,
    reverse: bool,
    cards: int,
    batch_size: int,
    model: str,
    dry_run: bool,
    verbose: bool
):
    """
    Universal Anki deck generator using Claude API.

    Generates flashcards from INPUT_FILE according to PROMPT.md specification.
    """
    try:
        # Initialize components
        start_time = time.time()
        click.echo("⚙️  Initializing...")

        if verbose:
            click.echo(f"  Input file: {input_file}")
            click.echo(f"  Prompt file: {prompt}")
            click.echo(f"  Output file: {output}")
            click.echo(f"  Deck: {deck}")
            click.echo(f"  Cards per item: {cards}")
            click.echo(f"  Batch size: {batch_size}")
            click.echo(f"  Model: {model}")
            click.echo(f"  Reverse: {reverse}")

        # Get template path
        template_path = get_template_path()
        click.echo("✓ Template loaded")

        # Initialize components
        parser = InputParser(input_file, batch_size)
        click.echo("✓ Input parsed")

        prompt_builder = PromptBuilder(
            str(template_path),
            prompt,
            cards
        )
        click.echo("✓ Prompt configured")

        formatter = AnkiFormatter(output, deck, reverse)
        click.echo("✓ Formatter ready")

        # Create system message (cached)
        system_message = prompt_builder.create_system_message()

        # Initialize API client (skip if dry run)
        api_client = None
        if not dry_run:
            api_client = ClaudeAPIClient(
                model=model,
                verbose=verbose
            )
            click.echo("✓ API client initialized")

        # Get all lines and calculate total batches
        all_lines = parser.read_lines()
        total_batches = (len(all_lines) + batch_size - 1) // batch_size
        click.echo(f"\n📋 Found {len(all_lines)} items in {total_batches} batch(es)")

        # Process batches
        total_items = 0
        total_cards = 0
        is_first_batch = True
        batch_number = 0

        click.echo("\n🔄 Processing...\n")

        for batch_lines in parser.create_batches(all_lines):
            batch_number += 1
            batch_size_actual = len(batch_lines)
            total_items += batch_size_actual

            # Show batch progress
            click.echo(f"[Batch {batch_number}/{total_batches}] Processing {batch_size_actual} item(s)...")

            # Create user message
            if batch_size_actual == 1:
                user_message = prompt_builder.create_user_message_single(
                    batch_lines[0]
                )
            else:
                user_message = prompt_builder.create_user_message_batch(
                    batch_lines
                )

            # Dry run mode
            if dry_run:
                api_client_dry = ClaudeAPIClient(model=model, verbose=True)
                api_client_dry.dry_run(system_message, user_message)
                continue

            # Generate cards
            try:
                click.echo(f"  → Sending API request...")
                response_text = api_client.generate_cards(
                    system_message,
                    user_message
                )

                click.echo(f"  → Validating response...")

                # Parse and validate response
                data = ResponseValidator.parse_json(response_text)

                if batch_size_actual == 1:
                    # Single item response
                    validated_cards = ResponseValidator.validate_single_response(
                        data,
                        cards
                    )

                    # Write cards
                    click.echo(f"  → Writing {len(validated_cards)} card(s)...")
                    formatter.write_cards(
                        validated_cards,
                        append=not is_first_batch
                    )
                    total_cards += len(validated_cards)
                    click.echo(f"  ✓ Batch {batch_number} complete ({len(validated_cards)} cards generated)\n")

                else:
                    # Batch response
                    validated_items = ResponseValidator.validate_batch_response(
                        data,
                        cards,
                        batch_size_actual
                    )

                    # Write all cards from batch
                    batch_cards = 0
                    for item in validated_items:
                        formatter.write_cards(
                            item.cards,
                            append=not is_first_batch
                        )
                        batch_cards += len(item.cards)
                        total_cards += len(item.cards)
                        is_first_batch = False

                    click.echo(f"  → Writing {batch_cards} card(s)...")
                    click.echo(f"  ✓ Batch {batch_number} complete ({batch_cards} cards generated)\n")

                is_first_batch = False

            except ValueError as e:
                click.echo(f"  ✗ Error: {e}", err=True)
                click.echo(f"  ⟳ Retrying batch {batch_number}...", err=True)

                # Retry once
                try:
                    response_text = api_client.generate_cards(
                        system_message,
                        user_message
                    )
                    data = ResponseValidator.parse_json(response_text)

                    if batch_size_actual == 1:
                        validated_cards = ResponseValidator.validate_single_response(
                            data,
                            cards
                        )
                        formatter.write_cards(
                            validated_cards,
                            append=not is_first_batch
                        )
                        total_cards += len(validated_cards)
                    else:
                        validated_items = ResponseValidator.validate_batch_response(
                            data,
                            cards,
                            batch_size_actual
                        )
                        for item in validated_items:
                            formatter.write_cards(
                                item.cards,
                                append=not is_first_batch
                            )
                            total_cards += len(item.cards)
                            is_first_batch = False

                    is_first_batch = False
                    click.echo(f"  ✓ Retry successful for batch {batch_number}")

                except Exception as retry_error:
                    click.echo(
                        f"Retry failed: {retry_error}",
                        err=True
                    )
                    formatter.save_progress(total_items)
                    formatter.create_partial_backup()
                    raise

            except Exception as e:
                click.echo(f"  ✗ Unexpected error in batch {batch_number}: {e}", err=True)
                formatter.save_progress(total_items)
                formatter.create_partial_backup()
                raise

        # Summary
        elapsed_time = time.time() - start_time

        if dry_run:
            click.echo("\n✓ Dry run completed. No cards generated.")
        else:
            click.echo(f"\n{'='*50}")
            click.echo(f"✓ Success!")
            click.echo(f"{'='*50}")
            click.echo(f"  Processed: {total_items} items")
            click.echo(f"  Generated: {total_cards} cards")
            click.echo(f"  Time: {elapsed_time:.1f}s")
            click.echo(f"  Output: {output}")
            click.echo(f"{'='*50}")
            formatter.clear_progress()

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
