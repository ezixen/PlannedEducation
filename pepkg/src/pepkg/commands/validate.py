"""Validate commands for pepkg CLI."""

import click
from pathlib import Path
from rich.console import Console

from ..config import Config

console = Console()


@click.group()
def validate() -> None:
    """Validate package files locally (without API)."""
    pass


@validate.command()
@click.argument(
    "file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--strict",
    is_flag=True,
    help="Fail on warnings as well as errors",
)
@click.pass_context
def package(
    ctx: click.Context,
    file: Path,
    strict: bool,
) -> None:
    """Validate a package file locally."""
    import json
    import yaml
    import hashlib

    console = Console()

    try:
        # Read and parse file
        content = file.read_bytes()

        # Decompress if gzipped
        if file.suffix == ".gz":
            import gzip
            try:
                content = gzip.decompress(content)
            except Exception:
                console.print("[red]Error: Invalid gzip file[/red]")
                return

        # Parse content
        try:
            if file.suffix in (".yaml", ".yml"):
                pkg = yaml.safe_load(content.decode())
            else:
                pkg = json.loads(content.decode())
        except Exception as e:
            console.print(f"[red]Error: Invalid package format: {e}[/red]")
            return

        # Validate structure
        errors = []
        warnings = []

        # Required fields
        required_fields = ["metadata", "exam", "questions"]
        for field in required_fields:
            if field not in pkg:
                errors.append(f"Missing required field: {field}")

        if errors:
            console.print("[red]✗[/red] Package validation failed")
            for error in errors:
                console.print(f"  [red]Error:[/red] {error}")
            return

        # Validate metadata
        metadata = pkg.get("metadata", {})
        required_metadata = ["id", "name", "version", "author", "author_id", "checksum"]
        for field in required_metadata:
            if field not in metadata:
                errors.append(f"Missing metadata field: {field}")

        # Validate exam
        exam = pkg.get("exam", {})
        if not exam.get("title"):
            errors.append("Exam title is required")

        # Validate questions
        questions = pkg.get("questions", [])
        if not isinstance(questions, list):
            errors.append("Questions must be a list")
        else:
            for i, q in enumerate(questions):
                if not q.get("id"):
                    errors.append(f"Question {i}: missing id")
                if not q.get("question_type"):
                    errors.append(f"Question {i}: missing question_type")
                if not q.get("text"):
                    errors.append(f"Question {i}: missing text")
                if q.get("question_type") == "multiple_choice" and not q.get("options"):
                    warnings.append(f"Question {i}: multiple_choice should have options")

        # Verify checksum
        pkg_copy = pkg.copy()
        pkg_copy["metadata"] = pkg_copy["metadata"].copy()
        pkg_copy["metadata"]["checksum"] = ""
        import json as json_lib
        content_str = json_lib.dumps(pkg_copy, sort_keys=True, separators=(",", ":"))
        calculated = hashlib.sha256(content_str.encode()).hexdigest()
        if metadata.get("checksum") != calculated:
            errors.append("Checksum mismatch - package may be corrupted or modified")

        # Output results
        if errors:
            console.print("[red]✗[/red] Package validation failed")
            for error in errors:
                console.print(f"  [red]Error:[/red] {error}")
        else:
            console.print("[green]✓[/green] Package is valid!")

        if warnings:
            for warning in warnings:
                console.print(f"  [yellow]Warning:[/yellow] {warning}")

        if strict and warnings:
            console.print("[red]Strict mode: warnings treated as errors[/red]")
            return

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")