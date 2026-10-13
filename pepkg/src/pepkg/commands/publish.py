"""Publish commands for pepkg CLI."""

import click
from rich.console import Console
from rich.table import Table

from ..config import Config

console = Console()


@click.group()
def publish() -> None:
    """Publish/unpublish packages to the registry."""
    pass


@publish.command()
@click.argument("package_id")
@click.option(
    "--public/--private",
    default=True,
    help="Publish as public or private",
)
@click.pass_context
def set_visibility(
    ctx: click.Context,
    package_id: str,
    public: bool,
) -> None:
    """Set package visibility (public/private)."""
    config: Config = ctx.obj["config"]

    import httpx

    try:
        with httpx.Client(base_url=config.api_url, timeout=30.0) as client:
            response = client.post(
                f"/packages/{package_id}/publish",
                json={"is_public": public},
                headers=config.get_headers(),
                timeout=30.0,
            )
            response.raise_for_status()

            result = response.json()
            console.print(f"[green]✓[/green] Package visibility updated")
            console.print(f"  Package ID: {result.get('package_id')}")
            console.print(f"  Public: {result.get('is_public')}")
            console.print(f"  Message: {result.get('message')}")

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


@publish.command()
@click.argument("package_id")
@click.pass_context
def unpublish(ctx: click.Context, package_id: str) -> None:
    """Unpublish a package (make private)."""
    config: Config = ctx.obj["config"]

    import httpx

    try:
        with httpx.Client(base_url=config.api_url, timeout=30.0) as client:
            response = client.post(
                f"/packages/{package_id}/publish",
                json={"is_public": False},
                headers=config.get_headers(),
                timeout=30.0,
            )
            response.raise_for_status()

            result = response.json()
            console.print(f"[green]✓[/green] Package unpublished")
            console.print(f"  Package ID: {result.get('package_id')}")
            console.print(f"  Public: {result.get('is_public')}")

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