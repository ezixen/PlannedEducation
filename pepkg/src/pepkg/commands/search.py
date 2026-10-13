"""Search commands for pepkg CLI."""

import click
from rich.console import Console
from rich.table import Table

from ..config import Config

console = Console()


@click.group()
def search() -> None:
    """Search packages in the registry."""
    pass


@search.command()
@click.argument("query")
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
    "--author",
    "-a",
    help="Filter by author name",
)
@click.option(
    "--public-only/--include-private",
    default=True,
    help="Only search public packages",
)
@click.option(
    "--limit",
    "-l",
    default=20,
    help="Maximum results to return",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format",
)
@click.pass_context
def packages(
    ctx: click.Context,
    query: str,
    subject: Optional[str],
    grade_level: Optional[str],
    tags: Optional[str],
    author: Optional[str],
    public_only: bool,
    limit: int,
    format: str,
) -> None:
    """Search packages by query."""
    config: Config = ctx.obj["config"]

    import httpx

    try:
        with httpx.Client(base_url=config.api_url, timeout=30.0) as client:
            params = {
                "q": query,
                "limit": limit,
                "public_only": public_only,
            }
            if subject:
                params["subject"] = subject
            if grade_level:
                params["grade_level"] = grade_level
            if tags:
                params["tags"] = tags
            if author:
                params["author"] = author

            response = client.get(
                "/packages/search",
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

                table = Table(title=f"Search Results for '{query}'")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="bold")
                table.add_column("Version", style="dim")
                table.add_column("Author", style="green")
                table.add_column("Subject", style="blue")
                table.add_column("Grade", style="magenta")
                table.add_column("Public", style="green")
                table.add_column("Created", style="dim")

                for pkg in packages:
                    table.add_row(
                        pkg.get("id", "")[:8] + "...",
                        pkg.get("name", ""),
                        pkg.get("version", ""),
                        pkg.get("author", ""),
                        pkg.get("subject", "") or "-",
                        pkg.get("grade_level", "") or "-",
                        "✓" if pkg.get("is_public") else "✗",
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


@search.command()
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
    "--limit",
    "-l",
    default=20,
    help="Maximum results to return",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format",
)
@click.pass_context
def public(
    ctx: click.Context,
    subject: Optional[str],
    grade_level: Optional[str],
    tags: Optional[str],
    limit: int,
    format: str,
) -> None:
    """Browse public packages."""
    config: Config = ctx.obj["config"]

    import httpx

    try:
        with httpx.Client(base_url=config.api_url, timeout=30.0) as client:
            params = {
                "limit": limit,
                "public_only": True,
            }
            if subject:
                params["subject"] = subject
            if grade_level:
                params["grade_level"] = grade_level
            if tags:
                params["tags"] = tags

            response = client.get(
                "/packages/public",
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
                    console.print("[yellow]No public packages found[/yellow]")
                    return

                table = Table(title="Public Packages")
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