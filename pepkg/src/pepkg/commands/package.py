"""Package management commands for pepkg CLI."""

import json
from pathlib import Path
from typing import Optional

import click
import yaml
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..config import Config

console = Console()


@click.group()
def package() -> None:
    """Package management commands."""
    pass


@package.command()
@click.option(
    "--exam-id",
    "-e",
    required=True,
    help="Exam ID to export",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "yaml"]),
    default="json",
    help="Export format",
)
@click.option(
    "--include-answers/--no-answers",
    default=True,
    help="Include correct answers in export",
)
@click.option(
    "--include-rubrics/--no-rubrics",
    default=True,
    help="Include rubrics in export",
)
@click.option(
    "--include-variables/--no-variables",
    default=True,
    help="Include variables in export",
)
@click.option(
    "--compress/--no-compress",
    default=False,
    help="Compress output with gzip",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output file path (default: stdout)",
)
@click.pass_context
def export(
    ctx: click.Context,
    exam_id: str,
    format: str,
    include_answers: bool,
    include_rubrics: bool,
    include_variables: bool,
    compress: bool,
    output: Optional[Path],
) -> None:
    """Export an exam as a test package."""
    config: Config = ctx.obj["config"]

    import httpx

    try:
        with httpx.Client(base_url=config.api_url, timeout=60.0) as client:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Exporting package...", total=None)

                response = client.post(
                    "/packages/export",
                    json={
                        "exam_id": exam_id,
                        "format": format,
                        "include_answers": include_answers,
                        "include_rubrics": include_rubrics,
                        "include_variables": include_variables,
                        "compress": compress,
                    },
                    headers=config.get_headers(),
                    timeout=60.0,
                )
                response.raise_for_status()

                progress.update(task, completed=True)

            # Determine filename
            content_disposition = response.headers.get("content-disposition", "")
            filename = f"package.{format}"
            if "filename=" in content_disposition:
                import re
                match = re.search(r'filename="(.+)"', content_disposition)
                if match:
                    filename = match.group(1)

            if compress and not filename.endswith(".gz"):
                filename += ".gz"

            # Write output
            if output:
                output.write_bytes(response.content)
                console.print(f"[green]✓[/green] Package exported to [bold]{output}[/bold]")
            else:
                # Print to stdout
                if format == "json":
                    console.print_json(response.text)
                else:
                    console.print(response.text)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            console.print("[red]Error: Not authenticated. Run 'pepkg auth login'[/red]")
        elif e.response.status_code == 404:
            console.print("[red]Error: Exam not found or access denied[/red]")
        else:
            console.print(f"[red]Error: {e.response.status_code} - {e.response.text}[/red]")
    except httpx.RequestError as e:
        console.print(f"[red]Error: Could not connect to API at {config.api_url}[/red]")
        console.print(f"[dim]Details: {e}[/dim]")


@package.command()
@click.argument(
    "file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Import even if validation fails",
)
@click.pass_context
def import_cmd(
    ctx: click.Context,
    file: Path,
    force: bool,
) -> None:
    """Import a test package from file."""
    config: Config = ctx.obj["config"]

    import httpx

    try:
        with httpx.Client(base_url=config.api_url, timeout=60.0) as client:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Importing package...", total=None)

                with open(file, "rb") as f:
                    files = {"file": (file.name, f, "application/octet-stream")}
                    response = client.post(
                        "/packages/import",
                        files=files,
                        headers={"Authorization": f"Bearer {config.token}"} if config.token else {},
                        timeout=60.0,
                    )
                    response.raise_for_status()

                progress.update(task, completed=True)

            result = response.json()

            if result.get("success"):
                console.print(f"[green]✓[/green] Package imported successfully!")
                console.print(f"  Package ID: {result.get('package_id')}")
                console.print(f"  Exam ID: {result.get('exam_id')}")
                console.print(f"  Questions imported: {result.get('questions_imported', 0)}")
                console.print(f"  Rubrics imported: {result.get('rubrics_imported', 0)}")
                if result.get("warnings"):
                    for warning in result["warnings"]:
                        console.print(f"  [yellow]Warning:[/yellow] {warning}")
            else:
                console.print("[red]✗[/red] Import failed")
                for error in result.get("errors", []):
                    console.print(f"  [red]Error:[/red] {error}")
                if not force:
                    console.print("[yellow]Use --force to import anyway[/yellow]")

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            console.print("[red]Error: Not authenticated. Run 'pepkg auth login'[/red]")
        else:
            console.print(f"[red]Error: {e.response.status_code} - {e.response.text}[/red]")
    except httpx.RequestError as e:
        console.print(f"[red]Error: Could not connect to API at {config.api_url}[/red]")
        console.print(f"[dim]Details: {e}[/dim]")


@package.command()
@click.argument(
    "file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.pass_context
def validate(ctx: click.Context, file: Path) -> None:
    """Validate a test package without importing."""
    config: Config = ctx.obj["config"]

    import httpx

    try:
        with httpx.Client(base_url=config.api_url, timeout=30.0) as client:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Validating package...", total=None)

                with open(file, "rb") as f:
                    files = {"file": (file.name, f, "application/octet-stream")}
                    response = client.post(
                        "/packages/validate",
                        files=files,
                        headers={"Authorization": f"Bearer {config.token}"} if config.token else {},
                        timeout=30.0,
                    )
                    response.raise_for_status()

                progress.update(task, completed=True)

            result = response.json()

            if result.get("valid"):
                console.print("[green]✓[/green] Package is valid!")
                if result.get("warnings"):
                    for warning in result["warnings"]:
                        console.print(f"  [yellow]Warning:[/yellow] {warning}")
            else:
                console.print("[red]✗[/red] Package validation failed")
                for error in result.get("errors", []):
                    console.print(f"  [red]Error:[/red] {error}")

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            console.print("[red]Error: Not authenticated. Run 'pepkg auth login'[/red]")
        else:
            console.print(f"[red]Error: {e.response.status_code} - {e.response.text}[/red]")
    except httpx.RequestError as e:
        console.print(f"[red]Error: Could not connect to API at {config.api_url}[/red]")
        console.print(f"[dim]Details: {e}[/dim]")


@package.command()
@click.option(
    "--subject",
    "-s",
    help="Filter by subject",
)
@click.option(
    "--grade-level",
    "-g",
    help="Filter by grade level",
)
@click.option(
    "--tags",
    "-t",
    help="Filter by tags (comma-separated)",
)
@click.option(
    "--author-id",
    "-a",
    help="Filter by author ID",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format",
)
@click.pass_context
def list(
    ctx: click.Context,
    subject: Optional[str],
    grade_level: Optional[str],
    tags: Optional[str],
    author_id: Optional[str],
    format: str,
) -> None:
    """List available packages."""
    config: Config = ctx.obj["config"]

    import httpx

    try:
        with httpx.Client(base_url=config.api_url, timeout=30.0) as client:
            params = {}
            if subject:
                params["subject"] = subject
            if grade_level:
                params["grade_level"] = grade_level
            if tags:
                params["tags"] = tags
            if author_id:
                params["author_id"] = author_id

            response = client.get(
                "/packages",
                params=params,
                headers=config.get_headers(),
                timeout=30.0,
            )
            response.raise_for_status()

            data = response.json()
            packages = data.get("packages", [])

            if format == "json":
                console.print_json(json.dumps(packages))
            elif format == "yaml":
                console.print(yaml.dump(packages, default_flow_style=False))
            else:
                if not packages:
                    console.print("[yellow]No packages found[/yellow]")
                    return

                table = Table(title="Available Packages")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="bold")
                table.add_column("Version", style="dim")
                table.add_column("Author", style="green")
                table.add_column("Subject", style="blue")
                table.add_column("Grade", style="magenta")
                table.add_column("Created", style="dim")

                for pkg in packages:
                    table.add_row(
                        pkg.get("id", "")[:8] + "...",
                        pkg.get("name", ""),
                        pkg.get("version", ""),
                        pkg.get("author", ""),
                        pkg.get("subject", "") or "-",
                        pkg.get("grade_level", "") or "-",
                        pkg.get("created_at", "")[:10] if pkg.get("created_at") else "-",
                    )

                console.print(table)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            console.print("[red]Error: Not authenticated. Run 'pepkg auth login'[/red]")
        else:
            console.print(f"[red]Error: {e.response.status_code} - {e.response.text}[/red]")
    except httpx.RequestError as e:
        console.print(f"[red]Error: Could not connect to API at {config.api_url}[/red]")
        console.print(f"[dim]Details: {e}[/dim]")


@package.command()
@click.argument(
    "package_id",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "yaml"]),
    default="json",
    help="Download format",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output file path",
)
@click.pass_context
def download(
    ctx: click.Context,
    package_id: str,
    format: str,
    output: Optional[Path],
) -> None:
    """Download a package by ID."""
    config: Config = ctx.obj["config"]

    import httpx

    try:
        with httpx.Client(base_url=config.api_url, timeout=60.0) as client:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Downloading package...", total=None)

                response = client.get(
                    f"/packages/{package_id}/download",
                    params={"format": format},
                    headers=config.get_headers(),
                    timeout=60.0,
                )
                response.raise_for_status()

                progress.update(task, completed=True)

            # Determine filename
            content_disposition = response.headers.get("content-disposition", "")
            filename = f"package.{format}"
            if "filename=" in content_disposition:
                import re
                match = re.search(r'filename="(.+)"', content_disposition)
                if match:
                    filename = match.group(1)

            if output:
                output.write_bytes(response.content)
                console.print(f"[green]✓[/green] Package downloaded to [bold]{output}[/bold]")
            else:
                # Print to stdout
                if format == "json":
                    console.print_json(response.text)
                else:
                    console.print(response.text)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            console.print("[red]Error: Not authenticated. Run 'pepkg auth login'[/red]")
        elif e.response.status_code == 404:
            console.print("[red]Error: Package not found[/red]")
        else:
            console.print(f"[red]Error: {e.response.status_code} - {e.response.text}[/red]")
    except httpx.RequestError as e:
        console.print(f"[red]Error: Could not connect to API at {config.api_url}[/red]")
        console.print(f"[dim]Details: {e}[/dim]")