"""Authentication commands for pepkg CLI."""

import click
from rich.console import Console
from rich.prompt import Prompt

from ..config import Config

console = Console()


@click.group()
def auth() -> None:
    """Authentication commands."""
    pass


@auth.command()
@click.option(
    "--email",
    "-e",
    prompt=True,
    help="Email address",
)
@click.option(
    "--password",
    "-p",
    prompt=True,
    hide_input=True,
    help="Password",
)
@click.pass_context
def login(ctx: click.Context, email: str, password: str) -> None:
    """Login to PlannedEducation and store token."""
    config: Config = ctx.obj["config"]

    import httpx

    try:
        with httpx.Client(base_url=config.api_url, timeout=30.0) as client:
            response = client.post(
                "/auth/token",
                data={"username": email, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            data = response.json()
            token = data.get("access_token")
            if not token:
                console.print("[red]Error: No access token in response[/red]")
                return

            config.save_token(token)
            console.print(f"[green]✓[/green] Logged in as [bold]{email}[/bold]")
            console.print(f"Token saved to config")

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            console.print("[red]Error: Invalid credentials[/red]")
        else:
            console.print(f"[red]Error: {e.response.status_code} - {e.response.text}[/red]")
    except httpx.RequestError as e:
        console.print(f"[red]Error: Could not connect to API at {config.api_url}[/red]")
        console.print(f"[dim]Details: {e}[/dim]")


@auth.command()
@click.pass_context
def logout(ctx: click.Context) -> None:
    """Logout and clear stored token."""
    config: Config = ctx.obj["config"]
    config.clear_token()
    console.print("[green]✓[/green] Logged out successfully")


@auth.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show authentication status."""
    config: Config = ctx.obj["config"]

    if config.token:
        console.print("[green]✓[/green] Authenticated")
        console.print(f"API URL: {config.api_url}")
        # Try to get user info
        import httpx

        try:
            with httpx.Client(base_url=config.api_url, timeout=10.0) as client:
                response = client.get(
                    "/auth/me",
                    headers=config.get_headers(),
                )
                if response.status_code == 200:
                    user = response.json()
                    console.print(f"User: {user.get('email', 'Unknown')} ({user.get('role', 'Unknown')})")
                else:
                    console.print("[yellow]Token may be expired[/yellow]")
        except Exception:
            console.print("[yellow]Could not verify token[/yellow]")
    else:
        console.print("[red]✗[/red] Not authenticated")
        console.print("Run 'pepkg auth login' to authenticate")


@auth.command()
@click.option(
    "--email",
    "-e",
    prompt=True,
    help="Email address",
)
@click.option(
    "--username",
    "-u",
    prompt=True,
    help="Username",
)
@click.option(
    "--password",
    "-p",
    prompt=True,
    hide_input=True,
    help="Password",
)
@click.option(
    "--full-name",
    "-n",
    prompt=True,
    help="Full name",
)
@click.pass_context
def register(ctx: click.Context, email: str, username: str, password: str, full_name: str) -> None:
    """Register a new user account."""
    config: Config = ctx.obj["config"]

    import httpx

    try:
        with httpx.Client(base_url=config.api_url, timeout=30.0) as client:
            response = client.post(
                "/auth/register",
                json={
                    "email": email,
                    "username": username,
                    "password": password,
                    "full_name": full_name,
                },
            )
            response.raise_for_status()
            data = response.json()
            console.print(f"[green]✓[/green] Registered successfully as [bold]{email}[/bold]")
            console.print(f"User ID: {data.get('id', 'Unknown')}")

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            detail = e.response.json().get("detail", "Registration failed")
            console.print(f"[red]Error: {detail}[/red]")
        else:
            console.print(f"[red]Error: {e.response.status_code} - {e.response.text}[/red]")
    except httpx.RequestError as e:
        console.print(f"[red]Error: Could not connect to API at {config.api_url}[/red]")
        console.print(f"[dim]Details: {e}[/dim]")